"""
Importa relaciones ManyToMany de la Biblioteca desde el dump SQL de SilverStripe.
NO modifica los 279 registros Biblioteca ya importados.

Tablas objetivo:
  - BibliotecaVideo   → VideoBiblioteca + Biblioteca.videos
  - BibliotecaImagen  → ImagenBiblioteca + Biblioteca.imagenes
  - BibliotecaDocumento → DocumentoBiblioteca + Biblioteca.documentos
  - BibliotecaEtiqueta / Etiqueta → EtiquetaBiblioteca + Biblioteca.etiquetas
  - File              → mapa de ID→Filename para resolver paths

Uso:
  python manage.py import_biblioteca_relaciones
  python manage.py import_biblioteca_relaciones --dry-run
  python manage.py import_biblioteca_relaciones --sql-path ruta/dinapi.sql
  python manage.py import_biblioteca_relaciones --truncate-relaciones
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.biblioteca.models import (
    Biblioteca,
    VideoBiblioteca,
    ImagenBiblioteca,
    DocumentoBiblioteca,
    EtiquetaBiblioteca,
)


INSERT_RE = re.compile(
    r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$"
)

_TARGET_TABLES = {
    'BibliotecaVideo',
    'BibliotecaImagen',
    'BibliotecaDocumento',
    'BibliotecaEtiqueta',
    'Etiqueta',
    'File',
}


class Command(BaseCommand):
    help = 'Importa relaciones M2M de biblioteca desde dump SQL de SilverStripe.'

    def add_arguments(self, parser):
        parser.add_argument('--sql-path', default='dinapi_web_old/dinapi.sql')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--truncate-relaciones',
            action='store_true',
            help='Elimina los recursos multimedia y etiquetas antes de reimportar '
                 '(NO toca los registros Biblioteca).',
        )

    def handle(self, *args, **options):
        sql_path = Path(options['sql_path']).resolve()
        dry_run = options['dry_run']
        truncate = options['truncate_relaciones']

        if not sql_path.exists():
            raise CommandError(f'No existe el archivo SQL: {sql_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run: no se guardarán cambios.'))

        stats = self._run(sql_path=sql_path, dry_run=dry_run, truncate=truncate)
        self.stdout.write(self.style.SUCCESS('Importacion de relaciones finalizada.'))
        for k, v in stats.items():
            self.stdout.write(f'  {k}: {v}')

    # ------------------------------------------------------------------

    def _run(self, sql_path, dry_run, truncate):
        # 1. Leer todas las tablas necesarias del dump
        data: Dict[str, list] = {t: [] for t in _TARGET_TABLES}

        def collect(table, columns, rows):
            if table in _TARGET_TABLES:
                for row in rows:
                    data[table].append(dict(zip(columns, row)))

        self._scan_dump(sql_path, collect)

        # Informe de lo encontrado
        for table, rows in data.items():
            if rows:
                self.stdout.write(f'  {table}: {len(rows)} filas')
            else:
                self.stdout.write(self.style.WARNING(f'  {table}: no encontrada'))

        if dry_run:
            return {'dry_run': True}

        # 2. Construir mapa legacy_id → Biblioteca (slug = f"{slugify(titulo)}-{old_id}")
        biblioteca_map: Dict[int, Biblioteca] = {}
        for bib in Biblioteca.objects.all():
            slug_parts = bib.slug.rsplit('-', 1)
            if len(slug_parts) == 2:
                try:
                    old_id = int(slug_parts[1])
                    biblioteca_map[old_id] = bib
                except ValueError:
                    pass

        self.stdout.write(f'Bibliotecas mapeadas: {len(biblioteca_map)}')

        # 3. Mapa File: ID → path
        file_map: Dict[int, str] = {}
        for row in data.get('File', []):
            fid = _to_int(row.get('ID'))
            path = (row.get('Filename') or '').strip()
            if fid and path:
                file_map[fid] = path

        stats = {
            'videos_creados': 0, 'videos_relaciones': 0,
            'imagenes_creadas': 0, 'imagenes_relaciones': 0,
            'documentos_creados': 0, 'documentos_relaciones': 0,
            'etiquetas_creadas': 0, 'etiquetas_relaciones': 0,
            'omitidos': 0,
        }

        with transaction.atomic():
            if truncate:
                VideoBiblioteca.objects.all().delete()
                ImagenBiblioteca.objects.all().delete()
                DocumentoBiblioteca.objects.all().delete()
                EtiquetaBiblioteca.objects.all().delete()
                self.stdout.write(self.style.WARNING('Multimedia y etiquetas eliminados.'))

            # --- Videos ---
            for row in data.get('BibliotecaVideo', []):
                old_id = _to_int(row.get('ID'))
                bib_id = _to_int(row.get('BibliotecaID'))
                titulo = (row.get('Titulo') or row.get('Title') or '').strip()
                url = (row.get('URL') or row.get('Url') or row.get('VideoURL') or '').strip()
                if not titulo or not url:
                    stats['omitidos'] += 1
                    continue
                obj, created = VideoBiblioteca.objects.get_or_create(
                    legacy_id=old_id,
                    defaults={
                        'titulo': titulo,
                        'url': url,
                        'descripcion': (row.get('Descripcion') or '').strip(),
                        'orden': _to_int(row.get('Orden') or row.get('Sort')) or 0,
                    },
                )
                if created:
                    stats['videos_creados'] += 1
                bib = biblioteca_map.get(bib_id)
                if bib:
                    bib.videos.add(obj)
                    stats['videos_relaciones'] += 1

            # --- Imagenes ---
            for row in data.get('BibliotecaImagen', []):
                old_id = _to_int(row.get('ID'))
                bib_id = _to_int(row.get('BibliotecaID'))
                titulo = (row.get('Titulo') or row.get('Title') or '').strip()
                file_id = _to_int(row.get('ImagenID') or row.get('FileID') or row.get('ImageID'))
                url_ext = (row.get('URL') or row.get('Url') or '').strip()

                # Resolver path del archivo
                imagen_path = None
                if file_id and file_id in file_map:
                    raw = file_map[file_id]
                    imagen_path = raw[len('assets/'):] if raw.startswith('assets/') else raw

                obj, created = ImagenBiblioteca.objects.get_or_create(
                    legacy_id=old_id,
                    defaults={
                        'titulo': titulo,
                        'imagen': imagen_path or '',
                        'url': url_ext,
                        'descripcion': (row.get('Descripcion') or '').strip(),
                        'orden': _to_int(row.get('Orden') or row.get('Sort')) or 0,
                    },
                )
                if created:
                    stats['imagenes_creadas'] += 1
                bib = biblioteca_map.get(bib_id)
                if bib:
                    bib.imagenes.add(obj)
                    stats['imagenes_relaciones'] += 1

            # --- Documentos ---
            for row in data.get('BibliotecaDocumento', []):
                old_id = _to_int(row.get('ID'))
                bib_id = _to_int(row.get('BibliotecaID'))
                titulo = (row.get('Titulo') or row.get('Title') or '').strip()
                file_id = _to_int(row.get('DocumentoID') or row.get('FileID') or row.get('ArchivoID'))
                url_ext = (row.get('URL') or row.get('Url') or '').strip()

                archivo_path = None
                if file_id and file_id in file_map:
                    raw = file_map[file_id]
                    archivo_path = raw[len('assets/'):] if raw.startswith('assets/') else raw

                if not titulo:
                    # Intentar inferir título del path
                    titulo = Path(archivo_path).stem if archivo_path else 'Documento'

                obj, created = DocumentoBiblioteca.objects.get_or_create(
                    legacy_id=old_id,
                    defaults={
                        'titulo': titulo,
                        'archivo': archivo_path or '',
                        'url': url_ext,
                        'descripcion': (row.get('Descripcion') or '').strip(),
                        'orden': _to_int(row.get('Orden') or row.get('Sort')) or 0,
                    },
                )
                if created:
                    stats['documentos_creados'] += 1
                bib = biblioteca_map.get(bib_id)
                if bib:
                    bib.documentos.add(obj)
                    stats['documentos_relaciones'] += 1

            # --- Etiquetas ---
            # Primero construir mapa de etiquetas (tabla Etiqueta o BibliotecaEtiqueta)
            etiqueta_obj_map: Dict[int, EtiquetaBiblioteca] = {}

            for row in data.get('Etiqueta', []):
                old_id = _to_int(row.get('ID'))
                nombre = (row.get('Nombre') or row.get('Name') or row.get('Titulo') or '').strip()
                if not nombre:
                    continue
                slug = slugify(nombre)[:100] or f'etiqueta-{old_id}'
                obj, created = EtiquetaBiblioteca.objects.get_or_create(
                    slug=slug,
                    defaults={'nombre': nombre},
                )
                if created:
                    stats['etiquetas_creadas'] += 1
                if old_id:
                    etiqueta_obj_map[old_id] = obj

            # Relaciones Biblioteca-Etiqueta
            for row in data.get('BibliotecaEtiqueta', []):
                bib_id = _to_int(row.get('BibliotecaID'))
                etq_id = _to_int(row.get('EtiquetaID'))
                if not bib_id or not etq_id:
                    continue
                bib = biblioteca_map.get(bib_id)
                etq = etiqueta_obj_map.get(etq_id)
                if bib and etq:
                    bib.etiquetas.add(etq)
                    stats['etiquetas_relaciones'] += 1

        return stats

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
                    if table_name not in _TARGET_TABLES:
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
# Utilidades SQL (mismo patrón que todos los otros import commands)
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
