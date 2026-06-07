from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.concursos.models import Concurso


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")


class Command(BaseCommand):
    help = 'Importa concursos desde el dump SQL de SilverStripe.'

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

        result = self._run(sql_path=sql_path, truncate=truncate, dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS('Importacion de concursos finalizada'))
        self.stdout.write(
            f"Concursos: creados={result['created']} actualizados={result['updated']} omitidos={result['skipped']}"
        )

    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
        }

        old_file_map: Dict[int, str] = {}

        if truncate and not dry_run:
            Concurso.objects.all().delete()

        def process_statement(table: str, columns: List[str], rows: Iterable[List[object]]):
            nonlocal summary, old_file_map

            if table == 'File':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    filename = (data.get('Filename') or '').strip()
                    if old_id and filename:
                        old_file_map[old_id] = filename

            elif table == 'Concurso':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    titulo = (data.get('Titulo') or '').strip()
                    if not legacy_id or not titulo:
                        summary['skipped'] += 1
                        continue

                    slug = f"{slugify(titulo) or 'concurso'}-{legacy_id}"
                    pagina_legacy_id = _to_int(data.get('PaginaID'))
                    imagen_corta = _legacy_file_to_media_path(old_file_map.get(_to_int(data.get('ImagenCortaID'))))
                    imagen_completa = _legacy_file_to_media_path(old_file_map.get(_to_int(data.get('ImagenCompletaID'))))

                    defaults = {
                        'titulo': titulo,
                        'pagina_legacy_id': pagina_legacy_id,
                        'fecha': _parse_date(data.get('Fecha')),
                        'enlace': (data.get('Enlace') or '')[:1000],
                        'legacy_created': _parse_datetime(data.get('Created')),
                        'legacy_last_edited': _parse_datetime(data.get('LastEdited')),
                    }
                    if imagen_corta:
                        defaults['imagen_corta'] = imagen_corta
                    if imagen_completa:
                        defaults['imagen_completa'] = imagen_completa

                    if dry_run:
                        continue

                    _, created = Concurso.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults={
                            'slug': slug,
                            **defaults,
                        },
                    )
                    if created:
                        summary['created'] += 1
                    else:
                        summary['updated'] += 1

        context = transaction.atomic if not dry_run else _null_context
        with context():
            self._scan_dump(sql_path, process_statement)

        return summary

    def _scan_dump(self, sql_path: Path, handler):
        target_tables = {'Concurso', 'File'}

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
                    if table_name not in target_tables:
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


def _parse_datetime(value: object):
    if not value:
        return None

    raw = str(value)
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            dt = datetime.strptime(raw, fmt)
            if timezone.is_naive(dt):
                return timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        except ValueError:
            continue
    return None
