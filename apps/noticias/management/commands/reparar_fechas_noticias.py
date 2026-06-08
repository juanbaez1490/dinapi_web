"""
Repara el campo `fecha` (y `fecha_creacion`) de Noticia desde el SQL legacy.

Problema observado: durante el import original, muchas noticias quedaron con
`fecha=hoy` porque el parser del comando original fallaba en algunos casos.
Resultado: la lista de noticias se ordena por id y no por la fecha real de
publicacion, por lo que aparecen noticias antiguas como "mas nuevas".

Este comando lee Noticia.{ID, Created, Fecha} del SQL legacy y actualiza
en BD usando el legacy_id que esta embebido al final del slug
(`titulo-noticia-<legacy_id>`).

Uso:
    python manage.py reparar_fechas_noticias              # dry-run
    python manage.py reparar_fechas_noticias --apply
"""
import re
from datetime import datetime, date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples
from apps.noticias.models import Noticia


def _parse_dt(value):
    if value is None or value == '':
        return None
    s = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = 'Repara fecha y fecha_creacion de Noticia desde el SQL legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al SQL legacy. Default: <BASE_DIR>/bd_legacy_bk_dinapi_2026-06-05.sql')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')

    def handle(self, *args, **options):
        apply = options['apply']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # Parsea legacy: legacy_id -> (created_dt, fecha)
        legacy_data = {}
        for tup in iter_insert_tuples(sql_text, 'Noticia'):
            if len(tup) < 7:
                continue
            legacy_id = tup[0]
            created_dt = _parse_dt(tup[2])
            fecha_publi = _parse_dt(tup[6])
            if fecha_publi:
                fecha_publi = fecha_publi.date() if hasattr(fecha_publi, 'date') else fecha_publi
            legacy_data[legacy_id] = {
                'created': created_dt,
                'fecha': fecha_publi,
            }
        self.stdout.write(f'Noticias legacy parseadas: {len(legacy_data)}')

        # Match por legacy_id extraido del slug
        slug_re = re.compile(r'-(\d+)$')
        actualizadas = 0
        sin_legacy_id = 0
        sin_match = 0
        sin_cambio = 0

        with transaction.atomic():
            for n in Noticia.objects.all():
                m = slug_re.search(n.slug)
                if not m:
                    sin_legacy_id += 1
                    continue
                legacy_id = int(m.group(1))
                data = legacy_data.get(legacy_id)
                if not data:
                    sin_match += 1
                    continue

                nueva_fecha = data['fecha']
                if not nueva_fecha and data['created']:
                    nueva_fecha = data['created'].date()
                if not nueva_fecha:
                    continue

                if n.fecha == nueva_fecha:
                    sin_cambio += 1
                    continue

                if apply:
                    n.fecha = nueva_fecha
                    # Tambien sincronizamos fecha_creacion para que sirva de tiebreaker
                    if data['created']:
                        Noticia.objects.filter(pk=n.pk).update(
                            fecha=nueva_fecha,
                            fecha_creacion=data['created'],
                        )
                    else:
                        Noticia.objects.filter(pk=n.pk).update(fecha=nueva_fecha)
                actualizadas += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen:\n'
            f'  Actualizadas:                {actualizadas}\n'
            f'  Sin cambio (ya correctas):   {sin_cambio}\n'
            f'  Sin legacy_id en slug:       {sin_legacy_id}\n'
            f'  Sin match en legacy:         {sin_match}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))
