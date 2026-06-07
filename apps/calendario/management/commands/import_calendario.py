"""
Importa Actividad desde el dump SQL de SilverStripe.

Tablas objetivo:
  - CalendarioActividad  (o Actividad, dependiendo del modelo legacy)
  - SiteTree / CalendarioPage  (sólo para contexto; no se importa como modelo separado)

Uso:
  python manage.py import_calendario
  python manage.py import_calendario --sql-path ruta/dinapi.sql
  python manage.py import_calendario --dry-run
  python manage.py import_calendario --truncate
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.calendario.models import Actividad


INSERT_RE = re.compile(
    r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$"
)

# Tablas legacy que pueden contener actividades
_ACTIVIDAD_TABLES = {
    'CalendarioActividad',
    'Actividad',
    'ActividadCalendario',
}


class Command(BaseCommand):
    help = 'Importa Actividad desde dump SQL de SilverStripe.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql-path',
            default='dinapi_web_old/dinapi.sql',
            help='Ruta al dump SQL (default: dinapi_web_old/dinapi.sql)',
        )
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--truncate', action='store_true')
        parser.add_argument(
            '--batch-size',
            type=int,
            default=200,
            help='Tamaño de lote para bulk_create (default: 200)',
        )

    def handle(self, *args, **options):
        sql_path = Path(options['sql_path']).resolve()
        dry_run = options['dry_run']
        truncate = options['truncate']
        batch_size = options['batch_size']

        if not sql_path.exists():
            raise CommandError(f'No existe el archivo SQL: {sql_path}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run: no se guardarán cambios.'))

        created, updated, skipped = self._run(
            sql_path=sql_path,
            dry_run=dry_run,
            truncate=truncate,
            batch_size=batch_size,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Importación finalizada — creadas={created} actualizadas={updated} omitidas={skipped}'
        ))

    def _run(self, sql_path, dry_run, truncate, batch_size):
        rows_by_table: Dict[str, list] = {}

        def collect(table, columns, rows):
            if table in _ACTIVIDAD_TABLES:
                rows_by_table.setdefault(table, [])
                for row in rows:
                    rows_by_table[table].append(dict(zip(columns, row)))

        self._scan_dump(sql_path, collect)

        if not rows_by_table:
            self.stdout.write(self.style.WARNING(
                'No se encontraron tablas de actividades en el dump. '
                f'Tablas buscadas: {sorted(_ACTIVIDAD_TABLES)}'
            ))
            return 0, 0, 0

        # Usar la primera tabla encontrada
        table_name = next(iter(rows_by_table))
        raw_rows = rows_by_table[table_name]
        self.stdout.write(f'Tabla encontrada: {table_name} ({len(raw_rows)} filas)')

        if dry_run:
            return 0, 0, 0

        created = updated = skipped = 0

        with transaction.atomic():
            if truncate:
                Actividad.objects.all().delete()
                self.stdout.write(self.style.WARNING('Tabla Actividad vaciada (--truncate).'))

            batch: List[Actividad] = []

            for data in raw_rows:
                obj = self._build_actividad(data)
                if obj is None:
                    skipped += 1
                    continue

                if obj.legacy_id is not None and Actividad.objects.filter(legacy_id=obj.legacy_id).exists():
                    # Actualizar en lugar de crear
                    Actividad.objects.filter(legacy_id=obj.legacy_id).update(
                        titulo=obj.titulo,
                        descripcion=obj.descripcion,
                        fecha_inicio=obj.fecha_inicio,
                        fecha_fin=obj.fecha_fin,
                        lugar=obj.lugar,
                        activo=obj.activo,
                    )
                    updated += 1
                    continue

                batch.append(obj)

                if len(batch) >= batch_size:
                    Actividad.objects.bulk_create(batch, ignore_conflicts=True)
                    created += len(batch)
                    batch = []

            if batch:
                Actividad.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)

        return created, updated, skipped

    def _build_actividad(self, data: dict) -> Optional[Actividad]:
        titulo = (data.get('Titulo') or data.get('Title') or '').strip()
        if not titulo:
            return None

        fecha_inicio = _parse_datetime(
            data.get('FechaInicio') or data.get('StartDate') or data.get('Fecha')
        )
        if fecha_inicio is None:
            return None

        fecha_fin = _parse_datetime(data.get('FechaFin') or data.get('EndDate'))
        lugar = (data.get('Lugar') or data.get('Location') or '').strip()
        descripcion = (data.get('Descripcion') or data.get('Description') or data.get('Contenido') or '').strip()
        legacy_id = _to_int(data.get('ID'))
        activo = not bool(_to_int(data.get('Ocultar') or data.get('Hidden') or 0))

        return Actividad(
            titulo=titulo,
            descripcion=descripcion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            lugar=lugar,
            activo=activo,
            legacy_id=legacy_id,
        )

    def _scan_dump(self, sql_path: Path, handler):
        all_targets = _ACTIVIDAD_TABLES

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
                    if table_name not in all_targets:
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


# ---------------------------------------------------------------------------
# Utilidades de parseo SQL (mismo patrón que los demás import commands)
# ---------------------------------------------------------------------------

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
        s = (s.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')
              .replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t'))
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


def _parse_datetime(value: object):
    if not value:
        return None
    s = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
