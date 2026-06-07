"""
Repara datos faltantes en AcordeonPage y AcordeonItem desde el legacy SQL.

Problemas resueltos:
1. Todos los AcordeonItem quedaron con pagina_id NULL (FK huerfana).
   Causa: la migracion original no mapeo `Acordeon.PaginaID` legacy a la FK.
2. Casi todas las AcordeonPage quedaron con contenido_superior y otros
   campos vacios, aunque el legacy SQL los tiene.

Lee `dinapi_web_old/dinapi.sql` (mysqldump del SilverStripe legacy) y:
- Para cada `AcordeonItem` por legacy_id, busca su `Acordeon.PaginaID`
  legacy y setea la FK `pagina` apuntando a la `AcordeonPage` con ese
  `legacy_id`.
- Para cada `AcordeonPage` por legacy_id, sincroniza titulo_padre,
  titulo_anexo y contenido_superior desde el legacy.

Uso:
    python manage.py reparar_acordeones                # dry-run (default)
    python manage.py reparar_acordeones --apply        # aplica y guarda
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples as _iter_insert_tuples
from apps.tarjetas.models import AcordeonPage, AcordeonItem


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Reasocia AcordeonItem huerfanos a su AcordeonPage padre y sincroniza campos vacios desde el SQL legacy.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql', default=None,
            help='Ruta al dump SQL legacy. Default: <BASE_DIR>/dinapi_web_old/dinapi.sql',
        )
        parser.add_argument(
            '--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en modo dry-run.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'dinapi_web_old' / 'dinapi.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL legacy: {sql_path}')

        self.stdout.write(f'Leyendo {sql_path} ...')
        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # --- Parsea Acordeon (items) ---
        # Columnas: ID, ClassName, Created, LastEdited, Titulo, Content,
        #           AdjuntoID, TituloAdjunto, PaginaID, FechaOrdenamiento
        items_legacy = {}  # legacy_id -> pagina_legacy_id
        for tup in _iter_insert_tuples(sql_text, 'Acordeon'):
            if len(tup) < 9:
                continue
            items_legacy[tup[0]] = tup[8]
        self.stdout.write(f'  Items legacy parseados: {len(items_legacy)}')

        # --- Parsea AcordeonPage ---
        # Columnas: ID, ImagenID, TituloPadre, TituloAnexo, AnexoID, ContenidoSuperior
        pages_legacy = {}  # legacy_id -> dict(titulo_padre, titulo_anexo, contenido_superior)
        for tup in _iter_insert_tuples(sql_text, 'AcordeonPage'):
            if len(tup) < 6:
                continue
            pages_legacy[tup[0]] = {
                'titulo_padre': tup[2] or '',
                'titulo_anexo': tup[3] or '',
                'contenido_superior': tup[5] or '',
            }
        self.stdout.write(f'  AcordeonPage legacy parseados: {len(pages_legacy)}')

        # --- Aplica cambios ---
        with transaction.atomic():
            self._reasociar_items(items_legacy)
            self._sincronizar_paginas(pages_legacy)
            if not apply:
                transaction.set_rollback(True)

        if not apply:
            self.stdout.write(self.style.WARNING(
                '\nSin cambios persistidos. Ejecuta con --apply para guardar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nCambios aplicados.'))

    # ----- subrutinas -----

    def _reasociar_items(self, items_legacy):
        self.stdout.write('\n--- Reasociacion de AcordeonItem huerfanos ---')
        paginas_por_legacy = {p.legacy_id: p for p in AcordeonPage.objects.all()}

        reasignados = 0
        sin_padre = 0
        ya_ok = 0
        for item in AcordeonItem.objects.all():
            target_legacy = items_legacy.get(item.legacy_id)
            if not target_legacy:
                continue
            padre = paginas_por_legacy.get(target_legacy)
            if not padre:
                sin_padre += 1
                continue
            if item.pagina_id == padre.id:
                ya_ok += 1
                continue
            self.stdout.write(
                f'  item legacy_id={item.legacy_id:4d}  ->  AcordeonPage legacy_id={padre.legacy_id:4d}  '
                f'({item.titulo[:50]})'
            )
            item.pagina = padre
            item.save(update_fields=['pagina'])
            reasignados += 1

        self.stdout.write(
            f'  Resumen items: {reasignados} reasignados, {ya_ok} ya estaban OK, '
            f'{sin_padre} apuntan a una AcordeonPage que no existe en BD.'
        )

    def _sincronizar_paginas(self, pages_legacy):
        self.stdout.write('\n--- Sincronizacion de AcordeonPage ---')

        cambiados = 0
        for pagina in AcordeonPage.objects.all():
            data = pages_legacy.get(pagina.legacy_id)
            if not data:
                continue

            cambios = []
            for campo in ('titulo_padre', 'titulo_anexo', 'contenido_superior'):
                actual = getattr(pagina, campo) or ''
                nuevo = data[campo] or ''
                if not actual and nuevo:
                    setattr(pagina, campo, nuevo)
                    cambios.append(f'{campo}({len(nuevo)} chars)')

            if cambios:
                self.stdout.write(
                    f'  AcordeonPage legacy_id={pagina.legacy_id:4d}  +  {", ".join(cambios)}'
                )
                pagina.save(update_fields=['titulo_padre', 'titulo_anexo', 'contenido_superior'])
                cambiados += 1

        self.stdout.write(f'  Resumen paginas: {cambiados} rellenadas.')
