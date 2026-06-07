from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.tarjetas.models import TarjetaPage, Tarjeta, AcordeonPage, AcordeonItem


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")
TARGET_TABLES = {'File', 'SiteTree', 'TarjetaPage', 'Tarjeta', 'AcordeonPage', 'Acordeon'}


class Command(BaseCommand):
    help = 'Importa TarjetaPage/Tarjeta y AcordeonPage/Acordeon desde SQL de SilverStripe.'

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

        self.stdout.write(self.style.SUCCESS('Importacion de tarjetas/acordeon finalizada'))
        self.stdout.write(
            f"TarjetaPage: creadas={result['tp_created']} actualizadas={result['tp_updated']}"
        )
        self.stdout.write(
            f"Tarjeta: creadas={result['t_created']} actualizadas={result['t_updated']} omitidas={result['t_skipped']}"
        )
        self.stdout.write(
            f"AcordeonPage: creadas={result['ap_created']} actualizadas={result['ap_updated']}"
        )
        self.stdout.write(
            f"AcordeonItem: creadas={result['ai_created']} actualizadas={result['ai_updated']} omitidas={result['ai_skipped']}"
        )

    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            'tp_created': 0,
            'tp_updated': 0,
            't_created': 0,
            't_updated': 0,
            't_skipped': 0,
            'ap_created': 0,
            'ap_updated': 0,
            'ai_created': 0,
            'ai_updated': 0,
            'ai_skipped': 0,
        }

        file_map: Dict[int, str] = {}
        site_tree_map: Dict[int, Dict[str, str]] = {}
        tarjeta_page_map: Dict[int, TarjetaPage] = {}
        acordeon_page_map: Dict[int, AcordeonPage] = {}

        if truncate and not dry_run:
            Tarjeta.objects.all().delete()
            TarjetaPage.objects.all().delete()
            AcordeonItem.objects.all().delete()
            AcordeonPage.objects.all().delete()

        def process_statement(table: str, columns: List[str], rows: Iterable[List[object]]):
            nonlocal summary

            if table == 'File':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    filename = (data.get('Filename') or '').strip()
                    if old_id and filename:
                        file_map[old_id] = filename

            elif table == 'SiteTree':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    if not old_id:
                        continue
                    site_tree_map[old_id] = {
                        'url_segment': (data.get('URLSegment') or '').strip(),
                        'title': (data.get('Title') or '').strip(),
                    }

            elif table == 'TarjetaPage':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    if not legacy_id:
                        continue

                    titulo = (data.get('Titulo') or '').strip()
                    imagen_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('ImagenID'))))

                    defaults = {'titulo': titulo}
                    if imagen_path:
                        defaults['imagen'] = imagen_path

                    if dry_run:
                        continue

                    obj, created = TarjetaPage.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    tarjeta_page_map[legacy_id] = obj
                    if created:
                        summary['tp_created'] += 1
                    else:
                        summary['tp_updated'] += 1

            elif table == 'AcordeonPage':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    if not legacy_id:
                        continue

                    imagen_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('ImagenID'))))
                    anexo_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('AnexoID'))))

                    defaults = {
                        'titulo_padre': (data.get('TituloPadre') or '').strip(),
                        'titulo_anexo': (data.get('TituloAnexo') or '').strip(),
                        'contenido_superior': data.get('ContenidoSuperior') or '',
                    }
                    if imagen_path:
                        defaults['imagen'] = imagen_path
                    if anexo_path:
                        defaults['anexo'] = anexo_path

                    if dry_run:
                        continue

                    obj, created = AcordeonPage.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    acordeon_page_map[legacy_id] = obj
                    if created:
                        summary['ap_created'] += 1
                    else:
                        summary['ap_updated'] += 1

            elif table == 'Tarjeta':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    titulo = (data.get('Titulo') or '').strip()
                    if not legacy_id or not titulo:
                        summary['t_skipped'] += 1
                        continue

                    pagina_id = _to_int(data.get('PaginaID'))
                    pagina = tarjeta_page_map.get(pagina_id)

                    link_interno = _to_int(data.get('LinkInterno'))
                    link_interno_url = _resolve_internal_url(link_interno, site_tree_map)

                    imagen_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('ImagenID'))))

                    defaults = {
                        'pagina': pagina,
                        'titulo': titulo,
                        'subtitulo': (data.get('Subtitulo') or '').strip(),
                        'link_interno': link_interno,
                        'link_interno_url': link_interno_url,
                        'link_externo': (data.get('LinkExterno') or '').strip(),
                        'fecha': _parse_date(data.get('Fecha')),
                    }
                    if imagen_path:
                        defaults['imagen'] = imagen_path

                    if dry_run:
                        continue

                    _, created = Tarjeta.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    if created:
                        summary['t_created'] += 1
                    else:
                        summary['t_updated'] += 1

            elif table == 'Acordeon':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    titulo = (data.get('Titulo') or '').strip()
                    if not legacy_id or not titulo:
                        summary['ai_skipped'] += 1
                        continue

                    pagina = acordeon_page_map.get(_to_int(data.get('PaginaID')))
                    adjunto_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('AdjuntoID'))))

                    defaults = {
                        'pagina': pagina,
                        'titulo': titulo,
                        'contenido': data.get('Content') or '',
                        'titulo_adjunto': (data.get('TituloAdjunto') or '').strip(),
                        'fecha_ordenamiento': _parse_date(data.get('FechaOrdenamiento')),
                    }
                    if adjunto_path:
                        defaults['adjunto'] = adjunto_path

                    if dry_run:
                        continue

                    _, created = AcordeonItem.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    if created:
                        summary['ai_created'] += 1
                    else:
                        summary['ai_updated'] += 1

        context = transaction.atomic if not dry_run else _null_context
        with context():
            self._scan_dump(sql_path, process_statement)

        return summary

    def _scan_dump(self, sql_path: Path, handler):
        with sql_path.open('r', encoding='utf-8', errors='ignore') as f:
            in_insert = False
            table = ''
            columns: List[str] = []
            values_buffer: List[str] = []

            for line in f:
                stripped = line.rstrip('\n')

                if not in_insert:
                    m = INSERT_RE.match(stripped.strip())
                    if not m:
                        continue
                    table_name = m.group('table')
                    if table_name not in TARGET_TABLES:
                        continue

                    table = table_name
                    columns = [c.strip().strip('`') for c in m.group('columns').split(',')]
                    in_insert = True
                    values_buffer = []
                    continue

                values_buffer.append(stripped)

                if stripped.strip().endswith(';'):
                    values_text = '\n'.join(values_buffer)
                    rows = [_parse_tuple(t) for t in _extract_tuples(values_text)]
                    handler(table, columns, rows)

                    in_insert = False
                    table = ''
                    columns = []
                    values_buffer = []


class _null_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _resolve_internal_url(link_interno: Optional[int], site_tree_map: Dict[int, Dict[str, str]]) -> str:
    if not link_interno:
        return ''
    data = site_tree_map.get(link_interno)
    if not data:
        return ''
    url_segment = data.get('url_segment') or ''
    title = data.get('title') or 'pagina'
    slug = f"{slugify(url_segment or title)}-{link_interno}"
    return f'/{slug}/'


def _legacy_file_to_media_path(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    filename = filename.strip()
    if filename.startswith('assets/'):
        return filename[len('assets/'):]
    return filename


def _extract_tuples(values_text: str) -> List[str]:
    tuples: List[str] = []
    in_string = False
    escape = False
    depth = 0
    start = -1

    for i, ch in enumerate(values_text):
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_string = False
            continue

        if ch == "'":
            in_string = True
            continue

        if ch == '(':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and start >= 0:
                tuples.append(values_text[start:i + 1])
                start = -1

    return tuples


def _parse_tuple(tuple_text: str) -> List[object]:
    inner = tuple_text[1:-1]
    parts: List[str] = []
    buf: List[str] = []
    in_string = False
    escape = False

    for ch in inner:
        if in_string:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_string = False
            continue

        if ch == "'":
            in_string = True
            buf.append(ch)
            continue

        if ch == ',':
            parts.append(''.join(buf).strip())
            buf = []
            continue

        buf.append(ch)

    parts.append(''.join(buf).strip())
    return [_decode_sql_value(p) for p in parts]


def _decode_sql_value(value: str) -> object:
    if value.upper() == 'NULL':
        return None

    if value.startswith("'") and value.endswith("'"):
        s = value[1:-1]
        s = (
            s.replace('\\\\', '\\')
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace('\\n', '\n')
            .replace('\\r', '\r')
            .replace('\\t', '\t')
            .replace('\\0', '\0')
        )
        return s

    if re.fullmatch(r'-?\d+', value):
        try:
            return int(value)
        except ValueError:
            return value

    return value


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: object):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None
