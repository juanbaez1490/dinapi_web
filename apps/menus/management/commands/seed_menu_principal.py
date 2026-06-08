"""
Pre-popula el modelo MenuPrincipal con la estructura del navbar del sitio
legacy DINAPI. Mapea cada item a su Pagina equivalente Django via
pagina_destino_legacy_id.

Estructura (matchea el legacy):
- Institucional                                     [pagina 301]
- Derecho de Autor y Derechos Conexos               [dropdown sin destino propio]
   * Registro de Derechos de Autor                  [pagina 900]
   * Promocion de Industrias Creativas y Folclore   [pagina 347]
   * Sociedades de Gestion Colectiva                [pagina 348]
- Propiedad Industrial                              [dropdown]
   * Marcas                                         [pagina 304]
   * Patentes                                       [pagina 305]
   * Dibujos y Modelos Industriales                 [pagina 306]
   * Indicaciones Geograficas y Denominaciones de Origen  [pagina 307]
   * Conocimientos Tradicionales y Recursos Geneticos     [pagina 941]
   * Gestiones Administrativas                      [pagina 308]
- Observancia                                       [dropdown]
   * Promocion y Prevencion                         [pagina 883]
   * Mediacion y Conciliacion                       [pagina 858]
   * Lucha Contra la Pirateria y Falsificacion      [pagina 879]
   * Registro de Importadores                       [pagina 866]
- Servicios Digitales                               [dropdown]
   * Registro de Agentes                            [link externo]
   * Biblioteca Virtual                             [link interno /biblioteca/]
   * Tramite Digital                                [link externo]
   * Clasificados REDPI                             [link externo]
- Noticias                                          [pagina 346 - Centro de noticias]

Uso:
    python manage.py seed_menu_principal              # dry-run
    python manage.py seed_menu_principal --apply
    python manage.py seed_menu_principal --apply --reset  # borra antes
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.menus.models import MenuPrincipal


# Estructura del navbar legacy. Cada padre es una tupla (titulo, props_padre, [hijos])
# props_padre puede tener: pagina_legacy_id, link_externo, link_interno_url, target_blank
NAVBAR = [
    # ( titulo,                                  padre_props,                                    hijos )
    ('Institucional',                            {'pagina_legacy_id': 301},                       []),

    ('Derecho de Autor y Derechos Conexos',      {},                                              [
        ('Registro de Derechos de Autor y Derechos Conexos',  {'pagina_legacy_id': 900}),
        ('Promocion de Industrias Creativas y Folclore',      {'pagina_legacy_id': 347}),
        ('Sociedades de Gestion Colectiva',                   {'pagina_legacy_id': 348}),
    ]),

    ('Propiedad Industrial',                     {},                                              [
        ('Marcas',                                            {'pagina_legacy_id': 304}),
        ('Patentes',                                          {'pagina_legacy_id': 305}),
        ('Dibujos y Modelos Industriales',                    {'pagina_legacy_id': 306}),
        ('Indicaciones Geograficas y Denominaciones de Origen', {'pagina_legacy_id': 307}),
        ('Conocimientos Tradicionales y Recursos Geneticos',  {'pagina_legacy_id': 941}),
        ('Gestiones Administrativas',                         {'pagina_legacy_id': 308}),
    ]),

    ('Observancia',                              {},                                              [
        ('Promocion y Prevencion',                            {'pagina_legacy_id': 883}),
        ('Mediacion y Conciliacion',                          {'pagina_legacy_id': 858}),
        ('Lucha Contra la Pirateria y Falsificacion',         {'pagina_legacy_id': 879}),
        ('Registro de Importadores',                          {'pagina_legacy_id': 866}),
    ]),

    ('Servicios Digitales',                      {},                                              [
        ('Registro de Agentes',                               {'link_externo': 'https://tp-escritos-backend.dinapi.gov.py/registro_agente',
                                                                'target_blank': True}),
        ('Biblioteca Virtual',                                {'link_interno_url': '/biblioteca/'}),
        ('Tramite Digital',                                   {'link_externo': 'https://joaju.dinapi.gov.py/',
                                                                'target_blank': True}),
        ('Clasificados REDPI',                                {'link_externo': 'https://redpi.dinapi.gov.py/',
                                                                'target_blank': True}),
    ]),

    ('Noticias',                                 {'pagina_legacy_id': 346},                       []),
]


class Command(BaseCommand):
    help = 'Pre-popula MenuPrincipal con la estructura del navbar legacy DINAPI.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')
        parser.add_argument('--reset', action='store_true',
            help='Borra todos los MenuPrincipal antes de crear.')

    def handle(self, *args, **options):
        apply = options['apply']
        reset = options['reset']

        with transaction.atomic():
            if apply and reset:
                n = MenuPrincipal.objects.all().delete()[0]
                self.stdout.write(f'Reset: {n} items previos borrados.')

            creados = 0
            for orden_padre, (titulo, props, hijos) in enumerate(NAVBAR, start=1):
                self.stdout.write(f'  [{orden_padre}] {titulo}')
                if apply:
                    padre, _ = MenuPrincipal.objects.update_or_create(
                        titulo=titulo, padre__isnull=True,
                        defaults={
                            'orden': orden_padre * 10,
                            **{k: v for k, v in props.items() if k in (
                                'pagina_destino_legacy_id', 'link_interno_url',
                                'link_externo', 'target_blank',
                            )},
                            **({'pagina_destino_legacy_id': props['pagina_legacy_id']}
                                if 'pagina_legacy_id' in props else {}),
                            'activo': True,
                        },
                    )
                    creados += 1
                else:
                    padre = None

                for orden_hijo, (h_titulo, h_props) in enumerate(hijos, start=1):
                    self.stdout.write(f'      - {h_titulo}')
                    if apply:
                        MenuPrincipal.objects.update_or_create(
                            titulo=h_titulo, padre=padre,
                            defaults={
                                'orden': orden_hijo * 10,
                                **{k: v for k, v in h_props.items() if k in (
                                    'pagina_destino_legacy_id', 'link_interno_url',
                                    'link_externo', 'target_blank',
                                )},
                                **({'pagina_destino_legacy_id': h_props['pagina_legacy_id']}
                                    if 'pagina_legacy_id' in h_props else {}),
                                'activo': True,
                            },
                        )
                        creados += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"Aplicado" if apply else "Dry-run"}: {creados} items menu.'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. Re-ejecuta con --apply.'
            ))
