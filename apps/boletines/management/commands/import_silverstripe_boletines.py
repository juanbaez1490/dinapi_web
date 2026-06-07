from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.boletines.models import PeriodoBoletin, Boletin


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")

# Mapa tabla SQL → tipo discriminador Django
TABLA_TIPO: Dict[str, str] = {
    # BoletinGeneral con PaginaBoletinesID → periodo general
    'BoletinGeneral_general': Boletin.TIPO_GENERAL,
    # BoletinGeneral con PaginaID → acto juridico en periodo marca
    'BoletinGeneral_acto': Boletin.TIPO_ACTO,
    'BoletinLogotiposMarcas': Boletin.TIPO_LOGOTIPO,
    'BoletinMarcasDocumentos': Boletin.TIPO_MARCA_DOC,
    'BoletinMovimientosAdministrativos': Boletin.TIPO_MOVIMIENTO,
}

TARGET_TABLES = {
    'SiteTree',
    'File',
    'BoletinGeneral',
    'BoletinLogotiposMarcas',
    'BoletinMarcasDocumentos',
    'BoletinMovimientosAdministrativos',
}

PERIODO_GENERAL_CLASS = 'PeriodoBoletinPage'
PERIODO_MARCA_CLASS = 'PeriodoBoletinMarcaPage'
BOLETIN_PAGE_CLASSES = {'BoletinPage', 'BoletinMarcaPage'}


class Command(BaseCommand):
    help = 'Importa PeriodoBoletin y Boletin desde el dump SQL de SilverStripe.'

    def add_arguments(self, parser):
        parser.add_argument('--sql-path', default='dinapi_web_old/dinapi.sql')
        parser.add_argument('--truncate', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        sql_path = Path(options['sql_path']).resolve()
        truncate = options['truncate']
        dry_run = options['dry_run']

        if not sql_path.exists():
            raise CommandError(f'No existe el archivo SQL: {sql_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run activo: no se guardaran cambios.'))

        result = self._run(sql_path, truncate, dry_run)

        self.stdout.write(self.style.SUCCESS('Importacion de boletines finalizada'))
        self.stdout.write(
            f"Periodos: creados={result['per_created']} actualizados={result['per_updated']}"
        )
        self.stdout.write(
            f"Boletines: creados={result['bol_created']} actualizados={result['bol_updated']} omitidos={result['bol_skipped']}"
        )

    # ------------------------------------------------------------------ core
    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            'per_created': 0, 'per_updated': 0,
            'bol_created': 0, 'bol_updated': 0, 'bol_skipped': 0,
        }

        # lookup maps built during scan
        file_map: Dict[int, str] = {}
        # SiteTree rows we care about (periods + BoletinPage parents)
        site_tree: Dict[int, dict] = {}

        periodo_map: Dict[int, PeriodoBoletin] = {}   # legacy_id → PeriodoBoletin

        if truncate and not dry_run:
            Boletin.objects.all().delete()
            PeriodoBoletin.objects.all().delete()

        # We need File and SiteTree tables processed BEFORE the Boletin tables.
        # A single-pass over the dump handles them in order because the dump
        # writes CREATE TABLE + INSERT for each table sequentially.

        def process(table: str, columns: List[str], rows: Iterable):
            nonlocal summary

            if table == 'File':
                for row in rows:
                    d = _row(columns, row)
                    fid = _int(d.get('ID'))
                    fname = (d.get('Filename') or '').strip()
                    if fid and fname:
                        file_map[fid] = fname

            elif table == 'SiteTree':
                for row in rows:
                    d = _row(columns, row)
                    sid = _int(d.get('ID'))
                    cls = (d.get('ClassName') or '').strip()
                    if cls in {PERIODO_GENERAL_CLASS, PERIODO_MARCA_CLASS} | BOLETIN_PAGE_CLASSES:
                        site_tree[sid] = {
                            'class': cls,
                            'title': (d.get('Title') or '').strip(),
                            'parent_id': _int(d.get('ParentID')),
                            'sort': _int(d.get('Sort')) or 0,
                            'created': _dt(d.get('Created')),
                        }
                        # Create PeriodoBoletin rows for PERIODO_* classes
                        if cls in {PERIODO_GENERAL_CLASS, PERIODO_MARCA_CLASS} and not dry_run:
                            tipo = (
                                PeriodoBoletin.Tipo.GENERAL
                                if cls == PERIODO_GENERAL_CLASS
                                else PeriodoBoletin.Tipo.MARCA
                            )
                            titulo = (d.get('MenuTitle') or '').strip() or (d.get('Title') or '').strip() or 'Periodo'
                            slug = f"{slugify(titulo) or 'periodo'}-{sid}"
                            _, created = PeriodoBoletin.objects.update_or_create(
                                legacy_id=sid,
                                defaults={
                                    'titulo': titulo,
                                    'slug': slug,
                                    'tipo': tipo,
                                    'padre_legacy_id': _int(d.get('ParentID')),
                                    'orden': _int(d.get('Sort')) or 0,
                                    'legacy_created': _dt(d.get('Created')),
                                },
                            )
                            if created:
                                summary['per_created'] += 1
                            else:
                                summary['per_updated'] += 1

            elif table == 'BoletinGeneral':
                for row in rows:
                    d = _row(columns, row)
                    legacy_id = _int(d.get('ID'))
                    titulo = (d.get('Titulo') or '').strip()
                    if not legacy_id or not titulo:
                        summary['bol_skipped'] += 1
                        continue

                    pagina_boletines_id = _int(d.get('PaginaBoletinesID')) or 0
                    pagina_id = _int(d.get('PaginaID')) or 0

                    if pagina_boletines_id:
                        tipo = Boletin.TIPO_GENERAL
                        periodo_legacy = pagina_boletines_id
                    elif pagina_id:
                        tipo = Boletin.TIPO_ACTO
                        periodo_legacy = pagina_id
                    else:
                        summary['bol_skipped'] += 1
                        continue

                    _create_boletin(
                        d, legacy_id, tipo, periodo_legacy,
                        file_map, periodo_map, summary, dry_run,
                    )

            elif table in {'BoletinLogotiposMarcas', 'BoletinMarcasDocumentos', 'BoletinMovimientosAdministrativos'}:
                tipo_map = {
                    'BoletinLogotiposMarcas': Boletin.TIPO_LOGOTIPO,
                    'BoletinMarcasDocumentos': Boletin.TIPO_MARCA_DOC,
                    'BoletinMovimientosAdministrativos': Boletin.TIPO_MOVIMIENTO,
                }
                tipo = tipo_map[table]
                for row in rows:
                    d = _row(columns, row)
                    legacy_id = _int(d.get('ID'))
                    titulo = (d.get('Titulo') or '').strip()
                    if not legacy_id or not titulo:
                        summary['bol_skipped'] += 1
                        continue
                    periodo_legacy = _int(d.get('PaginaID')) or 0
                    if not periodo_legacy:
                        summary['bol_skipped'] += 1
                        continue
                    _create_boletin(
                        d, legacy_id, tipo, periodo_legacy,
                        file_map, periodo_map, summary, dry_run,
                    )

        context = transaction.atomic if not dry_run else _null_context
        with context():
            self._scan(sql_path, process)
            # After scanning, build periodo_map
            if not dry_run:
                for p in PeriodoBoletin.objects.all():
                    periodo_map[p.legacy_id] = p

        return summary

    def _scan(self, sql_path: Path, handler):
        with sql_path.open('r', encoding='utf-8', errors='ignore') as f:
            in_insert = False
            table = ''
            columns: List[str] = []
            buf: List[str] = []

            for line in f:
                stripped = line.rstrip('\n')
                if not in_insert:
                    m = INSERT_RE.match(stripped.strip())
                    if not m or m.group('table') not in TARGET_TABLES:
                        continue
                    table = m.group('table')
                    columns = [c.strip().strip('`') for c in m.group('columns').split(',')]
                    in_insert = True
                    buf = []
                    continue

                buf.append(stripped)
                if stripped.strip().endswith(';'):
                    rows = [_parse_tuple(t) for t in _extract_tuples('\n'.join(buf))]
                    handler(table, columns, rows)
                    in_insert = False
                    table = ''
                    columns = []
                    buf = []


# ------------------------------------------------------------------ helpers
def _create_boletin(
    d, legacy_id, tipo, periodo_legacy,
    file_map, periodo_map, summary, dry_run,
):
    periodo = periodo_map.get(periodo_legacy) if not dry_run else None
    pdf_path = _file_path(file_map.get(_int(d.get('PdfID'))))
    imagen_path = _file_path(file_map.get(_int(d.get('ImagenID'))))

    defaults = {
        'titulo': (d.get('Titulo') or '').strip(),
        'periodo': periodo,
        'fecha': _date(d.get('Fecha')),
        'legacy_created': _dt(d.get('Created')),
    }
    if pdf_path:
        defaults['pdf'] = pdf_path
    if imagen_path:
        defaults['imagen'] = imagen_path

    if dry_run:
        return

    _, created = Boletin.objects.update_or_create(
        legacy_id=legacy_id,
        tipo=tipo,
        defaults=defaults,
    )
    if created:
        summary['bol_created'] += 1
    else:
        summary['bol_updated'] += 1


def _file_path(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    filename = filename.strip()
    if filename.startswith('assets/'):
        return filename[len('assets/'):]
    return filename or None


class _null_context:
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _row(columns, row):
    return dict(zip(columns, row))


def _int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v), '%Y-%m-%d').date()
    except ValueError:
        return None


def _dt(v):
    if not v:
        return None
    raw = str(v)
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            dt = datetime.strptime(raw, fmt)
            return timezone.make_aware(dt, timezone.get_current_timezone()) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    return None


def _extract_tuples(text: str) -> List[str]:
    tuples: List[str] = []
    in_str = escape = False
    depth = start = 0
    for i, ch in enumerate(text):
        if in_str:
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == "'": in_str = False
            continue
        if ch == "'": in_str = True; continue
        if ch == '(':
            if depth == 0: start = i
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and start >= 0:
                tuples.append(text[start:i + 1])
                start = -1
    return tuples


def _parse_tuple(t: str) -> List[object]:
    inner = t[1:-1]
    parts, buf = [], []
    in_str = escape = False
    for ch in inner:
        if in_str:
            buf.append(ch)
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == "'": in_str = False
            continue
        if ch == "'": in_str = True; buf.append(ch); continue
        if ch == ',': parts.append(''.join(buf).strip()); buf = []; continue
        buf.append(ch)
    parts.append(''.join(buf).strip())
    return [_decode(p) for p in parts]


def _decode(v: str) -> object:
    if v.upper() == 'NULL': return None
    if v.startswith("'") and v.endswith("'"):
        s = v[1:-1]
        return s.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"') \
                .replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
    if re.fullmatch(r'-?\d+', v):
        try: return int(v)
        except ValueError: pass
    return v
