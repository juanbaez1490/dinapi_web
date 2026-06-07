from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
import io
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.menus.models import MenuDerecho, Popup


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")
TARGET_TABLES = {'File', 'SiteTree', 'MenuDerecho', 'Popup'}


class Command(BaseCommand):
    help = 'Importa MenuDerecho y Popup desde SQL de SilverStripe.'

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

        summary = self._run(sql_path, truncate, dry_run)

        self.stdout.write(self.style.SUCCESS('Importacion de menus/popups finalizada'))
        self.stdout.write(
            f"MenuDerecho: creados={summary['menu_created']} actualizados={summary['menu_updated']}"
        )
        self.stdout.write(
            f"Popup: creados={summary['popup_created']} actualizados={summary['popup_updated']}"
        )

    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            'menu_created': 0,
            'menu_updated': 0,
            'popup_created': 0,
            'popup_updated': 0,
        }

        file_map: Dict[int, str] = {}
        site_tree_map: Dict[int, Dict[str, str]] = {}

        if truncate and not dry_run:
            MenuDerecho.objects.all().delete()
            Popup.objects.all().delete()

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

            elif table == 'MenuDerecho':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    if not legacy_id:
                        continue

                    link_interno = _to_int(data.get('LinkInterno'))
                    defaults = {
                        'titulo': (data.get('Titulo') or '').strip(),
                        'link_interno': link_interno,
                        'link_interno_url': _resolve_internal_url(link_interno, site_tree_map),
                        'link_externo': (data.get('LinkExterno') or '').strip(),
                        'destacado': _to_bool(data.get('Destacado')),
                        'padre': _to_bool(data.get('Padre')),
                        'hijo': _to_bool(data.get('Hijo')),
                        'fecha_ordenamiento': _parse_date(data.get('FechaOrdenamiento')),
                    }

                    if dry_run:
                        continue

                    _, created = MenuDerecho.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    if created:
                        summary['menu_created'] += 1
                    else:
                        summary['menu_updated'] += 1

            elif table == 'Popup':
                for row in rows:
                    data = dict(zip(columns, row))
                    legacy_id = _to_int(data.get('ID'))
                    if not legacy_id:
                        continue

                    imagen_path = _legacy_file_to_media_path(file_map.get(_to_int(data.get('ImagenID'))))
                    defaults = {
                        'titulo': (data.get('Titulo') or '').strip(),
                        'descripcion': (data.get('Descripcion') or '').strip(),
                        'url_video': (data.get('URLVideo') or data.get('UrlVideo') or '').strip(),
                    }
                    if imagen_path:
                        defaults['imagen'] = imagen_path

                    if dry_run:
                        continue

                    _, created = Popup.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults=defaults,
                    )
                    if created:
                        summary['popup_created'] += 1
                    else:
                        summary['popup_updated'] += 1

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
            continue

        if ch == ')':
            depth -= 1
            if depth == 0 and start != -1:
                tuples.append(values_text[start:i + 1])
                start = -1

    return tuples


def _parse_tuple(tuple_text: str) -> List[object]:
    inner = tuple_text.strip()[1:-1]
    reader = csv.reader(
        io.StringIO(inner),
        delimiter=',',
        quotechar="'",
        escapechar='\\',
        doublequote=False,
        strict=False,
    )
    values = next(reader)
    return [_convert_sql_value(v) for v in values]


def _convert_sql_value(value: str):
    v = value.strip()
    if v.upper() == 'NULL':
        return None

    # In some rows CSV parsing can leave surrounding single quotes as literal chars.
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        v = v[1:-1]

    return v


def _to_int(value) -> int:
    if value in (None, ''):
        return 0
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _to_bool(value) -> bool:
    return _to_int(value) == 1


def _parse_date(value) -> Optional[datetime.date]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None
