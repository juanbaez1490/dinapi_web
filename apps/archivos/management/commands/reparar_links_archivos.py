"""
Normaliza `Archivo.link_externo` que apuntan al sitio v3 legacy
(https://www.dinapi.gov.py/portal/v3/assets/...) hacia rutas locales
(/media/legacy/assets/...) cuando el archivo fisico fue sincronizado
por `sync_silverstripe_assets`.

Tambien resetea links rotos (asset NO disponible en media/legacy/assets)
para que el template caiga a placeholder o el campo `pdf` si lo tiene.

Patrones detectados:
  - https://www.dinapi.gov.py/portal/v3/assets/<path>
  - http://www.dinapi.gov.py/portal/v3/assets/<path>
  - /portal/v3/assets/<path>
  - assets/<path>

Uso:
    python manage.py reparar_links_archivos              # dry-run
    python manage.py reparar_links_archivos --apply
"""
import re
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.archivos.models import Archivo


# Captura el "path" dentro de assets/ en cualquiera de los formatos legacy
LEGACY_ASSETS_RE = re.compile(
    r'^(?:https?://(?:www\.)?dinapi\.gov\.py)?/?(?:portal/v3/)?(?:assets/)+'
    r'(?P<path>[^?#]+)',
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = 'Normaliza link_externo de Archivo del sitio v3 legacy a /media/legacy/assets/...'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')

    def handle(self, *args, **options):
        apply = options['apply']
        legacy_root = Path(settings.MEDIA_ROOT) / 'legacy' / 'assets'

        self.stdout.write(f'Legacy root: {legacy_root}')
        self.stdout.write(f'Modo: {"APLICAR" if apply else "DRY-RUN"}\n')

        # Solo procesamos link_externo no vacios
        qs = Archivo.objects.exclude(link_externo='').filter(
            link_externo__icontains='dinapi.gov.py',
        )
        # Tambien capturamos los que empiezan con /portal/v3/ o /assets/
        qs2 = Archivo.objects.exclude(link_externo='').filter(
            link_externo__iregex=r'^/?(portal/v3/|assets/)',
        )
        candidatas = (qs | qs2).distinct()
        self.stdout.write(f'Archivos candidatos: {candidatas.count()}\n')

        normalizadas = 0
        no_archivo_local = 0
        sin_match_patron = 0

        with transaction.atomic():
            for a in candidatas.iterator():
                link = a.link_externo.strip()
                m = LEGACY_ASSETS_RE.match(link)
                if not m:
                    sin_match_patron += 1
                    continue

                rel_path = unquote(m.group('path').strip().split('?', 1)[0].split('#', 1)[0])
                local_file = legacy_root / rel_path
                nueva_url = f'/media/legacy/assets/{rel_path}'

                if not local_file.exists():
                    no_archivo_local += 1
                    self.stdout.write(self.style.WARNING(
                        f'  [no fisico]  Archivo {a.legacy_id:5d}: {rel_path[:60]}'
                    ))
                    continue

                if a.link_externo == nueva_url:
                    # ya estaba normalizado
                    continue

                self.stdout.write(
                    f'  Archivo {a.legacy_id:5d}: {rel_path[:70]}'
                )
                if apply:
                    Archivo.objects.filter(pk=a.pk).update(link_externo=nueva_url)
                normalizadas += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen:\n'
            f'  Normalizadas:               {normalizadas}\n'
            f'  Sin archivo fisico local:   {no_archivo_local}\n'
            f'  Sin match de patron:        {sin_match_patron}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))
