from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.biblioteca.models import CategoriaBiblioteca, Biblioteca


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")


class Command(BaseCommand):
    help = "Importa CategoriaBiblioteca y Biblioteca desde dump SQL de SilverStripe."

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

        self.stdout.write(self.style.SUCCESS('Importacion de biblioteca finalizada'))
        self.stdout.write(
            f"Categorias: creadas={result['cats_created']} actualizadas={result['cats_updated']}"
        )
        self.stdout.write(
            f"Biblioteca: creada={result['lib_created']} actualizada={result['lib_updated']} omitida={result['lib_skipped']}"
        )

    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            'cats_created': 0,
            'cats_updated': 0,
            'lib_created': 0,
            'lib_updated': 0,
            'lib_skipped': 0,
        }

        old_cat_map: Dict[int, CategoriaBiblioteca] = {}
        old_file_map: Dict[int, str] = {}

        if truncate and not dry_run:
            Biblioteca.objects.all().delete()
            CategoriaBiblioteca.objects.all().delete()

        def process_statement(table: str, columns: List[str], rows: Iterable[List[object]]):
            nonlocal summary, old_cat_map, old_file_map

            if table == 'CategoriaBiblioteca':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    nombre = (data.get('Categoria') or 'Sin categoria').strip()
                    color = (data.get('ColorCategoria') or '').strip()
                    slug = f"{slugify(nombre) or 'categoria'}-{old_id or 'x'}"

                    if dry_run:
                        continue

                    categoria, created = CategoriaBiblioteca.objects.update_or_create(
                        slug=slug,
                        defaults={'nombre': nombre, 'color': color},
                    )
                    if old_id is not None:
                        old_cat_map[old_id] = categoria
                    if created:
                        summary['cats_created'] += 1
                    else:
                        summary['cats_updated'] += 1

            elif table == 'File':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    filename = (data.get('Filename') or '').strip()
                    if old_id and filename:
                        old_file_map[old_id] = filename

            elif table == 'Biblioteca':
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get('ID'))
                    titulo = (data.get('Titulo') or '').strip()
                    if not titulo:
                        summary['lib_skipped'] += 1
                        continue

                    categoria = old_cat_map.get(_to_int(data.get('CategoriaID')))
                    fecha_ordenamiento = _parse_date(data.get('FechaOrdenamiento'))
                    ocultar = bool(_to_int(data.get('Ocultar')) or 0)
                    slug = f"{slugify(titulo) or 'biblioteca'}-{old_id or 'x'}"

                    imagen_path = None
                    imagen_old_id = _to_int(data.get('ImagenPrincipalID'))
                    if imagen_old_id and imagen_old_id in old_file_map:
                        raw = old_file_map[imagen_old_id]
                        if raw.startswith('assets/'):
                            imagen_path = raw[len('assets/'):]
                        else:
                            imagen_path = raw

                    defaults = {
                        'titulo': titulo,
                        'categoria': categoria,
                        'descripcion': data.get('Descripcion') or '',
                        'descripcion_videos': (data.get('DescripcionVideos') or '')[:500],
                        'descripcion_imagenes': (data.get('DescripcionImagenes') or '')[:500],
                        'descripcion_documentos': (data.get('DescripcionDocumentos') or '')[:500],
                        'enlaces_referencias': data.get('EnlacesReferencias') or '',
                        'fecha_ordenamiento': fecha_ordenamiento,
                        'ocultar': ocultar,
                    }
                    if imagen_path:
                        defaults['imagen_principal'] = imagen_path

                    if dry_run:
                        continue

                    _, created = Biblioteca.objects.update_or_create(slug=slug, defaults=defaults)
                    if created:
                        summary['lib_created'] += 1
                    else:
                        summary['lib_updated'] += 1

        context = transaction.atomic if not dry_run else _null_context
        with context():
            self._scan_dump(sql_path, process_statement)

        return summary

    def _scan_dump(self, sql_path: Path, handler):
        target_tables = {'CategoriaBiblioteca', 'Biblioteca', 'File'}

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
