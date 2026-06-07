"""
Repara datos faltantes en TarjetaPage y Tarjeta desde el legacy SQL.

Mismo patron que reparar_acordeones:
1. Los `Tarjeta` quedaron con pagina_id NULL (FK huerfana).
2. Las `TarjetaPage` ya estan migradas con titulos, pero falta reasociar
   las tarjetas.

Tabla legacy `Tarjeta`:
    ID, ClassName, Created, LastEdited, Titulo, LinkInterno, LinkExterno,
    PaginaID, ImagenID, Subtitulo, Fecha

Uso:
    python manage.py reparar_tarjetas              # dry-run
    python manage.py reparar_tarjetas --apply      # aplica
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples
from apps.tarjetas.models import TarjetaPage, Tarjeta


class Command(BaseCommand):
    help = 'Reasocia Tarjeta huerfanas a su TarjetaPage padre via PaginaID legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al dump SQL legacy. Default: <BASE_DIR>/dinapi_web_old/dinapi.sql')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en modo dry-run.')

    def handle(self, *args, **options):
        apply = options['apply']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'dinapi_web_old' / 'dinapi.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL legacy: {sql_path}')

        self.stdout.write(f'Leyendo {sql_path} ...')
        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # Tarjeta cols: ID(0), ClassName, Created, LastEdited, Titulo, LinkInterno,
        # LinkExterno, PaginaID(7), ImagenID, Subtitulo, Fecha
        tarjetas_legacy = {}
        for tup in iter_insert_tuples(sql_text, 'Tarjeta'):
            if len(tup) < 8:
                continue
            tarjetas_legacy[tup[0]] = tup[7]
        self.stdout.write(f'  Tarjetas legacy parseadas: {len(tarjetas_legacy)}')

        with transaction.atomic():
            paginas_por_legacy = {p.legacy_id: p for p in TarjetaPage.objects.all()}

            reasignadas = 0
            sin_padre = 0
            ya_ok = 0
            for tarjeta in Tarjeta.objects.all():
                target_legacy = tarjetas_legacy.get(tarjeta.legacy_id)
                if not target_legacy:
                    continue
                padre = paginas_por_legacy.get(target_legacy)
                if not padre:
                    sin_padre += 1
                    continue
                if tarjeta.pagina_id == padre.id:
                    ya_ok += 1
                    continue
                self.stdout.write(
                    f'  tarjeta legacy_id={tarjeta.legacy_id:4d}  ->  '
                    f'TarjetaPage legacy_id={padre.legacy_id:4d}  ({tarjeta.titulo[:55]})'
                )
                tarjeta.pagina = padre
                tarjeta.save(update_fields=['pagina'])
                reasignadas += 1

            self.stdout.write(
                f'\n  Resumen: {reasignadas} reasignadas, {ya_ok} ya estaban OK, '
                f'{sin_padre} sin TarjetaPage padre en BD.'
            )

            if not apply:
                transaction.set_rollback(True)

        if not apply:
            self.stdout.write(self.style.WARNING(
                '\nSin cambios persistidos. Ejecuta con --apply para guardar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nCambios aplicados.'))
