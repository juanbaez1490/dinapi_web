"""
Importa la tabla legacy `TarjetaSimple` al modelo apps.tarjetas.TarjetaSimple.

Tabla legacy:
    ID, ClassName, Created, LastEdited, Titulo, LinkInterno, LinkExterno, PaginaID

Uso:
    python manage.py import_silverstripe_tarjetas_simples              # dry-run
    python manage.py import_silverstripe_tarjetas_simples --apply
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples
from apps.tarjetas.models import TarjetaSimple


class Command(BaseCommand):
    help = 'Importa TarjetaSimple desde el SQL legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--truncate', action='store_true')

    def handle(self, *args, **options):
        apply = options['apply']
        truncate = options['truncate']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        rows = list(iter_insert_tuples(sql_text, 'TarjetaSimple'))
        self.stdout.write(f'TarjetaSimple legacy parseadas: {len(rows)}')

        with transaction.atomic():
            if apply and truncate:
                n = TarjetaSimple.objects.all().delete()[0]
                self.stdout.write(f'  Truncate: {n} borradas')

            creadas, actualizadas = 0, 0
            for tup in rows:
                if len(tup) < 8:
                    continue
                legacy_id = tup[0]
                created_at = tup[2]
                titulo = tup[4] or ''
                link_interno = tup[5] or None
                link_externo = tup[6] or ''
                pagina_id = tup[7] or None

                self.stdout.write(
                    f'  legacy_id={legacy_id:3d}  pagina={pagina_id}  '
                    f'link_int={link_interno or "-"}  link_ext={"si" if link_externo else "-"}  '
                    f'{titulo[:60]}'
                )

                if apply:
                    _, created = TarjetaSimple.objects.update_or_create(
                        legacy_id=legacy_id,
                        defaults={
                            'titulo': titulo,
                            'pagina_legacy_id': pagina_id,
                            'link_interno_legacy_id': link_interno,
                            'link_externo': link_externo,
                            'legacy_created': created_at,
                        },
                    )
                    if created:
                        creadas += 1
                    else:
                        actualizadas += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen: creadas={creadas} actualizadas={actualizadas}'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))
