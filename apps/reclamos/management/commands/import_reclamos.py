"""
Management command: import_reclamos

Lee la tabla MensajeReclamos del dump SQL de SilverStripe y la importa a
apps.reclamos.Reclamo.

Uso:
    python manage.py import_reclamos
    python manage.py import_reclamos --sql-path dinapi_web_old/dinapi.sql
    python manage.py import_reclamos --dry-run
    python manage.py import_reclamos --truncate

Notas del analisis (analisis_migracion_modelos_faltantes.txt):
  - 624 filas, sin FK externas, solo texto.
  - Charset mixto: tabla latin1 con columnas internas utf8.
  - Columnas legacy: ID, ClassName, Created, LastEdited, Nombre, Email,
    Agente, Estudio, Tema, Expediente, Telefono, Mensaje.
  - Sin adjuntos (los adjuntos legacy viven fuera de esta DB).
  - Tema legacy es texto libre -> se mapea al choice mas cercano o 'otro'.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.reclamos.models import Reclamo


# Mapeo de valores legacy de Tema a los choices del modelo Django
_TEMA_MAP: Dict[str, str] = {
    'marca':          'marcas',
    'marcas':         'marcas',
    'patente':        'patentes',
    'patentes':       'patentes',
    'dibujo':         'dibujos_modelos',
    'modelo':         'dibujos_modelos',
    'derecho':        'derecho_autor',
    'autor':          'derecho_autor',
    'observancia':    'observancia',
    'igdo':           'igdo',
    'indicacion':     'igdo',
    'denominacion':   'igdo',
    'conocimiento':   'conocimientos_trad',
    'tradicional':    'conocimientos_trad',
    'gestion':        'gestiones_admin',
    'administrativo': 'gestiones_admin',
    'mediacion':      'mediacion',
    'conciliacion':   'mediacion',
}

INSERT_RE = re.compile(
    r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$"
)


class Command(BaseCommand):
    help = 'Importa MensajeReclamos desde el dump SQL de SilverStripe a Reclamo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql-path',
            default='dinapi_web_old/dinapi.sql',
            help='Ruta al dump SQL de SilverStripe (default: dinapi_web_old/dinapi.sql).',
        )
        parser.add_argument(
            '--truncate',
            action='store_true',
            help='Elimina todos los Reclamo existentes antes de importar.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo analiza y muestra estadisticas sin escribir en la DB.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Tamano del lote para bulk_create (default: 100).',
        )

    def handle(self, *args, **options):
        sql_path = Path(options['sql_path']).resolve()
        dry_run = options['dry_run']
        truncate = options['truncate']
        batch_size = options['batch_size']

        if not sql_path.exists():
            raise CommandError('No existe el archivo SQL: {}'.format(sql_path))

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run: no se escribiran cambios.'))

        if truncate and not dry_run:
            deleted, _ = Reclamo.objects.all().delete()
            self.stdout.write('Reclamos eliminados: {}'.format(deleted))

        summary = self._run(sql_path=sql_path, dry_run=dry_run, batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS('Importacion finalizada'))
        self.stdout.write(
            'creados={created}  omitidos={skipped}  errores={errors}'.format(**summary)
        )

    def _run(self, sql_path: Path, dry_run: bool, batch_size: int) -> Dict[str, int]:
        summary = {'created': 0, 'skipped': 0, 'errors': 0}
        pending: List[Reclamo] = []
        existing_legacy_ids = set(
            Reclamo.objects.exclude(legacy_id__isnull=True).values_list('legacy_id', flat=True)
        )

        with sql_path.open('r', encoding='utf-8', errors='replace') as f:
            in_insert = False
            columns: List[str] = []
            buffer: List[str] = []

            for line in f:
                stripped = line.rstrip('\n')

                if not in_insert:
                    m = INSERT_RE.match(stripped.strip())
                    if m and m.group('table') == 'MensajeReclamos':
                        columns = [c.strip().strip('`') for c in m.group('columns').split(',')]
                        in_insert = True
                        buffer = []
                    continue

                buffer.append(stripped)

                if stripped.strip().endswith(';'):
                    for tuple_str in _extract_tuples('\n'.join(buffer)):
                        values = _parse_tuple(tuple_str)
                        data = dict(zip(columns, values))
                        obj = self._build_reclamo(data, existing_legacy_ids, summary)
                        if obj is not None and not dry_run:
                            pending.append(obj)
                            if len(pending) >= batch_size:
                                self._flush(pending, summary)
                                pending = []
                    in_insert = False
                    columns = []
                    buffer = []

        if pending and not dry_run:
            self._flush(pending, summary)

        return summary

    def _build_reclamo(self, data: dict, existing_ids: set, summary: dict) -> Optional[Reclamo]:
        legacy_id = _to_int(data.get('ID'))
        if legacy_id is None:
            summary['skipped'] += 1
            return None
        if legacy_id in existing_ids:
            summary['skipped'] += 1
            return None

        nombre    = _clean(data.get('Nombre')) or 'Sin nombre'
        email_raw = _clean(data.get('Email')) or ''
        # Validacion basica de email
        if '@' not in email_raw:
            email_raw = 'sin-email-{}@legacy.dinapi.gov.py'.format(legacy_id)

        telefono   = _clean(data.get('Telefono')) or ''
        expediente = _clean(data.get('Expediente')) or ''
        descripcion = _clean(data.get('Mensaje')) or '(sin descripcion)'
        tema = _map_tema(_clean(data.get('Tema')) or '')

        fecha_envio = _parse_datetime(data.get('Created'))
        if fecha_envio is None:
            fecha_envio = timezone.now()

        # Agente y Estudio: se concatenan a descripcion si existen
        agente  = _clean(data.get('Agente'))  or ''
        estudio = _clean(data.get('Estudio')) or ''
        if agente or estudio:
            extra = []
            if agente:
                extra.append('Agente: {}'.format(agente))
            if estudio:
                extra.append('Estudio: {}'.format(estudio))
            descripcion = descripcion + '\n\n[Datos adicionales legacy]\n' + '\n'.join(extra)

        existing_ids.add(legacy_id)
        summary['created'] += 1

        return Reclamo(
            legacy_id=legacy_id,
            nombre=nombre[:255],
            email=email_raw[:254],
            telefono=telefono[:50],
            expediente=expediente[:255],
            tema=tema,
            descripcion=descripcion,
            estado=Reclamo.Estado.CERRADO,  # legacy: se marca cerrado por defecto
            fecha_envio=fecha_envio,
        )

    def _flush(self, objs: List[Reclamo], summary: dict):
        try:
            with transaction.atomic():
                Reclamo.objects.bulk_create(objs, ignore_conflicts=True)
        except Exception as e:
            # Si el lote falla, intentar fila a fila
            self.stderr.write('Error en lote, intentando fila a fila: {}'.format(e))
            for obj in objs:
                try:
                    with transaction.atomic():
                        obj.save()
                except Exception as e2:
                    summary['errors'] += 1
                    summary['created'] -= 1
                    self.stderr.write('  Error legacy_id={}: {}'.format(obj.legacy_id, e2))


# ---------------------------------------------------------------------------
# Helpers de parseo SQL (mismo patron que import_silverstripe_paginas)
# ---------------------------------------------------------------------------

def _extract_tuples(text: str) -> List[str]:
    tuples = []
    depth = 0
    start = -1
    in_str = False
    escape = False

    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
            continue
        if ch == '(':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and start >= 0:
                tuples.append(text[start:i + 1])
                start = -1
    return tuples


def _parse_tuple(tuple_text: str) -> List[object]:
    inner = tuple_text[1:-1]
    parts: List[str] = []
    buf: List[str] = []
    in_str = False
    escape = False

    for ch in inner:
        if in_str:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
            buf.append(ch)
            continue
        if ch == ',':
            parts.append(''.join(buf).strip())
            buf = []
            continue
        buf.append(ch)

    parts.append(''.join(buf).strip())
    return [_decode_value(p) for p in parts]


def _decode_value(value: str):
    if value.upper() == 'NULL':
        return None
    if value.startswith("'") and value.endswith("'"):
        s = value[1:-1]
        return (
            s.replace('\\\\', '\\')
             .replace("\\'", "'")
             .replace('\\"', '"')
             .replace('\\n', '\n')
             .replace('\\r', '\r')
             .replace('\\t', '\t')
             .replace('\\0', '\0')
        )
    if re.fullmatch(r'-?\d+', value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _clean(value) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _to_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
        return timezone.make_aware(dt, timezone.get_current_timezone())
    except ValueError:
        return None


def _map_tema(tema_legacy: str) -> str:
    """Mapea el texto libre del campo Tema legacy al choice mas cercano."""
    if not tema_legacy:
        return Reclamo.Tema.OTRO
    lower = tema_legacy.lower()
    for keyword, choice in _TEMA_MAP.items():
        if keyword in lower:
            return choice
    return Reclamo.Tema.OTRO
