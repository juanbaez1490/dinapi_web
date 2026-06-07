"""
Importa los bloques dinámicos del home desde el dump SQL de SilverStripe:
  - CarouselItem  (tablas: HomeSlide, Slide, CarouselItem, BannerItem)
  - Anuncio       (tablas: Anuncio, Banner, HomeAnuncio)
  - EnlaceInteres (tablas: EnlaceInteres, QuickLink, AccesoRapido)
  - File          (para resolver paths de imágenes)

Uso:
  python manage.py import_home_bloques
  python manage.py import_home_bloques --dry-run
  python manage.py import_home_bloques --sql-path ruta/dinapi.sql
  python manage.py import_home_bloques --truncate
  python manage.py import_home_bloques --solo carousel
  python manage.py import_home_bloques --solo anuncios
  python manage.py import_home_bloques --solo enlaces
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import CarouselItem, Anuncio, EnlaceInteres


INSERT_RE = re.compile(
    r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$"
)

_CAROUSEL_TABLES  = {'HomeSlide', 'Slide', 'CarouselItem', 'BannerItem', 'HomeCarousel'}
_ANUNCIO_TABLES   = {'Anuncio', 'Banner', 'HomeAnuncio', 'AnuncioBanner'}
_ENLACE_TABLES    = {'EnlaceInteres', 'QuickLink', 'AccesoRapido', 'EnlaceRapido'}
_FILE_TABLES      = {'File'}

_ALL_TARGETS = _CAROUSEL_TABLES | _ANUNCIO_TABLES | _ENLACE_TABLES | _FILE_TABLES


class Command(BaseCommand):
    help = 'Importa CarouselItem, Anuncio y EnlaceInteres desde dump SQL de SilverStripe.'

    def add_arguments(self, parser):
        parser.add_argument('--sql-path', default='dinapi_web_old/dinapi.sql')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--truncate', action='store_true', help='Vacía las tablas antes de importar.')
        parser.add_argument(
            '--solo',
            choices=['carousel', 'anuncios', 'enlaces'],
            default=None,
            help='Importar sólo uno de los tres bloques.',
        )

    def handle(self, *args, **options):
        sql_path = Path(options['sql_path']).resolve()
        dry_run  = options['dry_run']
        truncate = options['truncate']
        solo     = options['solo']

        if not sql_path.exists():
            raise CommandError(f'No existe el archivo SQL: {sql_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run: no se guardarán cambios.'))

        # 1. Escanear dump
        data: Dict[str, list] = {t: [] for t in _ALL_TARGETS}

        def collect(table, columns, rows):
            if table in _ALL_TARGETS:
                for row in rows:
                    data[table].append(dict(zip(columns, row)))

        self._scan_dump(sql_path, collect)

        # Informe
        for grp_name, tables in [
            ('Carousel', _CAROUSEL_TABLES),
            ('Anuncios', _ANUNCIO_TABLES),
            ('Enlaces',  _ENLACE_TABLES),
        ]:
            found = {t: len(data[t]) for t in tables if data[t]}
            if found:
                self.stdout.write(f'{grp_name}: {found}')
            else:
                self.stdout.write(self.style.WARNING(f'{grp_name}: ninguna tabla encontrada'))

        if dry_run:
            return

        # 2. Mapa File
        file_map: Dict[int, str] = {}
        for row in data.get('File', []):
            fid = _to_int(row.get('ID'))
            path = (row.get('Filename') or '').strip()
            if fid and path:
                file_map[fid] = path

        stats = {}

        with transaction.atomic():
            if truncate:
                if solo in (None, 'carousel'):
                    CarouselItem.objects.all().delete()
                if solo in (None, 'anuncios'):
                    Anuncio.objects.all().delete()
                if solo in (None, 'enlaces'):
                    EnlaceInteres.objects.all().delete()
                self.stdout.write(self.style.WARNING('Tablas vaciadas (--truncate).'))

            if solo in (None, 'carousel'):
                stats['carousel'] = self._import_carousel(data, file_map)
            if solo in (None, 'anuncios'):
                stats['anuncios'] = self._import_anuncios(data, file_map)
            if solo in (None, 'enlaces'):
                stats['enlaces'] = self._import_enlaces(data)

        self.stdout.write(self.style.SUCCESS('Importación finalizada.'))
        for bloque, s in stats.items():
            self.stdout.write(f'  {bloque}: creados={s[0]} actualizados={s[1]} omitidos={s[2]}')

    # ------------------------------------------------------------------
    # Importadores por bloque
    # ------------------------------------------------------------------

    def _import_carousel(self, data, file_map):
        created = updated = skipped = 0
        rows = self._first_table_rows(data, _CAROUSEL_TABLES)
        for row in rows:
            old_id = _to_int(row.get('ID'))
            titulo = (row.get('Titulo') or row.get('Title') or row.get('Nombre') or '').strip()
            if not titulo:
                skipped += 1
                continue

            imagen_path = _resolve_file(
                row, file_map,
                file_keys=('ImagenID', 'ImageID', 'BackgroundImageID', 'FileID'),
            )
            defaults = {
                'titulo':      titulo,
                'subtitulo':   (row.get('Subtitulo') or row.get('Subtitle') or row.get('Descripcion') or '')[:500],
                'url':         (row.get('URL') or row.get('Url') or row.get('LinkURL') or '')[:500],
                'texto_boton': (row.get('TextoBoton') or row.get('ButtonText') or 'Ver más')[:100],
                'activo':      not bool(_to_int(row.get('Ocultar') or row.get('Hidden') or 0)),
                'orden':       _to_int(row.get('Orden') or row.get('Sort') or row.get('SortOrder')) or 0,
            }
            if imagen_path:
                defaults['imagen'] = imagen_path

            obj, c = CarouselItem.objects.update_or_create(legacy_id=old_id, defaults=defaults)
            if c:
                created += 1
            else:
                updated += 1
        return created, updated, skipped

    def _import_anuncios(self, data, file_map):
        created = updated = skipped = 0
        rows = self._first_table_rows(data, _ANUNCIO_TABLES)
        for row in rows:
            old_id = _to_int(row.get('ID'))
            titulo = (row.get('Titulo') or row.get('Title') or '').strip()
            if not titulo:
                skipped += 1
                continue

            imagen_path = _resolve_file(row, file_map, file_keys=('ImagenID', 'ImageID', 'FileID'))
            defaults = {
                'titulo':      titulo,
                'descripcion': (row.get('Descripcion') or row.get('Contenido') or row.get('Description') or ''),
                'url':         (row.get('URL') or row.get('Url') or '')[:500],
                'fecha_inicio': _parse_date(row.get('FechaInicio') or row.get('StartDate')),
                'fecha_fin':    _parse_date(row.get('FechaFin') or row.get('EndDate')),
                'activo':      not bool(_to_int(row.get('Ocultar') or row.get('Hidden') or 0)),
                'orden':       _to_int(row.get('Orden') or row.get('Sort')) or 0,
            }
            if imagen_path:
                defaults['imagen'] = imagen_path

            obj, c = Anuncio.objects.update_or_create(legacy_id=old_id, defaults=defaults)
            if c:
                created += 1
            else:
                updated += 1
        return created, updated, skipped

    def _import_enlaces(self, data):
        created = updated = skipped = 0
        rows = self._first_table_rows(data, _ENLACE_TABLES)
        for row in rows:
            old_id = _to_int(row.get('ID'))
            titulo = (row.get('Titulo') or row.get('Title') or row.get('Nombre') or '').strip()
            url = (row.get('URL') or row.get('Url') or row.get('Link') or '').strip()
            if not titulo or not url:
                skipped += 1
                continue

            defaults = {
                'titulo':      titulo,
                'descripcion': (row.get('Descripcion') or row.get('Description') or '')[:500],
                'url':         url[:500],
                'icono':       (row.get('Icono') or row.get('Icon') or row.get('ClaseIcono') or '')[:100],
                'activo':      not bool(_to_int(row.get('Ocultar') or row.get('Hidden') or 0)),
                'orden':       _to_int(row.get('Orden') or row.get('Sort') or row.get('SortOrder')) or 0,
            }
            obj, c = EnlaceInteres.objects.update_or_create(legacy_id=old_id, defaults=defaults)
            if c:
                created += 1
            else:
                updated += 1
        return created, updated, skipped

    # ------------------------------------------------------------------

    def _first_table_rows(self, data, table_set):
        """Devuelve las filas de la primera tabla del grupo que tenga datos."""
        for table in table_set:
            if data.get(table):
                return data[table]
        return []

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
                    if table_name not in _ALL_TARGETS:
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
# Utilidades SQL
# ---------------------------------------------------------------------------

def _resolve_file(row, file_map, file_keys):
    for key in file_keys:
        fid = _to_int(row.get(key))
        if fid and fid in file_map:
            raw = file_map[fid]
            return raw[len('assets/'):] if raw.startswith('assets/') else raw
    return None


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


def _parse_date(value: object):
    if not value:
        return None
    s = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
