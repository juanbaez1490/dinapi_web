"""
Importa los Archivos (PDFs / links externos) desde el dump SQL legacy
de SilverStripe hacia el modelo `apps.archivos.Archivo`.

Tabla legacy `Archivo`:
    ID, ClassName, Created, LastEdited, Titulo, LinkExterno,
    PdfID, PaginaID, FechaOrdenamiento

Tabla legacy `File`:
    ID, ClassName, Created, LastEdited, Name, Title, Filename, ...

El comando hace lookup PdfID -> Filename y copia el PDF fisico desde
`dinapi_web_old/<Filename>` (donde Filename incluye 'assets/...') hacia
`media/archivos/<YYYY>/<basename>`.

Uso:
    python manage.py import_silverstripe_archivos                    # dry-run
    python manage.py import_silverstripe_archivos --apply             # importa
    python manage.py import_silverstripe_archivos --apply --no-copy-files  # solo metadata
"""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.archivos.models import Archivo
from apps.core.management._sql_parser import iter_insert_tuples


class Command(BaseCommand):
    help = 'Importa Archivos institucionales (PDFs y links) desde el SQL legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al SQL legacy. Default: <BASE_DIR>/bd_legacy_bk_dinapi_2026-06-05.sql')
        parser.add_argument('--assets-root', default=None,
            help='Carpeta raiz donde resolver los Filename del legacy. '
                 'Default: <BASE_DIR>/dinapi_web_old')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')
        parser.add_argument('--no-copy-files', action='store_true',
            help='Solo importa metadata (titulo, link, pagina). No copia PDFs fisicos.')
        parser.add_argument('--truncate', action='store_true',
            help='Borra todos los Archivo antes de importar.')
        parser.add_argument('--limit', type=int, default=0,
            help='Solo importa los primeros N Archivos. 0 = todos. Util para pruebas.')

    def handle(self, *args, **options):
        apply = options['apply']
        no_copy = options['no_copy_files']
        truncate = options['truncate']
        limit = options['limit']

        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        assets_root = Path(options['assets_root'] or Path(settings.BASE_DIR) / 'dinapi_web_old')

        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')
        if not assets_root.exists():
            raise CommandError(f'No existe la carpeta de assets: {assets_root}')

        self.stdout.write(f'SQL:         {sql_path}')
        self.stdout.write(f'Assets root: {assets_root}')
        self.stdout.write(f'Modo:        {"APLICAR" if apply else "DRY-RUN"}')
        self.stdout.write(f'Copy files:  {"NO" if no_copy else "SI"}')
        if limit:
            self.stdout.write(f'Limit:       {limit}\n')

        self.stdout.write('\nParseando SQL...')
        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # File: ID -> Filename
        files_by_id = {}
        for tup in iter_insert_tuples(sql_text, 'File'):
            if len(tup) < 7:
                continue
            fid = tup[0]
            filename = tup[6]  # Filename column
            if filename:
                files_by_id[fid] = filename
        self.stdout.write(f'  Files indexados: {len(files_by_id)}')

        # Archivo: lista completa
        archivos_legacy = []
        for tup in iter_insert_tuples(sql_text, 'Archivo'):
            if len(tup) < 9:
                continue
            archivos_legacy.append({
                'legacy_id': tup[0],
                'created': tup[2],
                'titulo': tup[4] or '',
                'link_externo': tup[5] or '',
                'pdf_id': tup[6] or 0,
                'pagina_id': tup[7] or 0,
                'fecha_ordenamiento': tup[8],
            })
        self.stdout.write(f'  Archivos legacy: {len(archivos_legacy)}\n')

        if limit:
            archivos_legacy = archivos_legacy[:limit]

        # --- Resumen pre-flight ---
        con_pdf = sum(1 for a in archivos_legacy if a['pdf_id'])
        con_link = sum(1 for a in archivos_legacy if a['link_externo'])
        pdfs_encontrados = sum(
            1 for a in archivos_legacy
            if a['pdf_id'] and a['pdf_id'] in files_by_id
            and (assets_root / files_by_id[a['pdf_id']]).exists()
        )
        pdfs_faltantes = sum(
            1 for a in archivos_legacy
            if a['pdf_id'] and (
                a['pdf_id'] not in files_by_id
                or not (assets_root / files_by_id[a['pdf_id']]).exists()
            )
        )
        self.stdout.write(
            f'  Con PDF asociado:        {con_pdf}\n'
            f'  Con link externo:        {con_link}\n'
            f'  PDFs fisicos encontrados:{pdfs_encontrados}\n'
            f'  PDFs faltantes:          {pdfs_faltantes}\n'
        )

        # --- Persistir ---
        media_archivos = Path(settings.MEDIA_ROOT) / 'archivos'

        with transaction.atomic():
            if apply and truncate:
                n = Archivo.objects.all().delete()[0]
                self.stdout.write(f'  Truncate: {n} Archivos borrados\n')

            stats = {'creados': 0, 'actualizados': 0, 'pdfs_copiados': 0, 'pdfs_skip': 0}
            for a in archivos_legacy:
                pdf_legacy_path = ''
                pdf_target = None
                if a['pdf_id'] and a['pdf_id'] in files_by_id:
                    pdf_legacy_path = files_by_id[a['pdf_id']]
                    src = assets_root / pdf_legacy_path
                    if src.exists() and not no_copy and apply:
                        year = src.stat().st_mtime
                        import time as _t
                        year_str = _t.strftime('%Y', _t.localtime(year))
                        dest_dir = media_archivos / year_str
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest = dest_dir / src.name
                        if not dest.exists():
                            shutil.copy2(src, dest)
                            stats['pdfs_copiados'] += 1
                        else:
                            stats['pdfs_skip'] += 1
                        pdf_target = f'archivos/{year_str}/{src.name}'

                if apply:
                    obj, created = Archivo.objects.update_or_create(
                        legacy_id=a['legacy_id'],
                        defaults={
                            'titulo': a['titulo'],
                            'link_externo': a['link_externo'],
                            'pagina_legacy_id': a['pagina_id'] or None,
                            'fecha_ordenamiento': a['fecha_ordenamiento'],
                            'pdf_legacy_path': pdf_legacy_path,
                            'pdf': pdf_target or '',
                            'legacy_created': a['created'],
                        },
                    )
                    if created:
                        stats['creados'] += 1
                    else:
                        stats['actualizados'] += 1

            if not apply:
                transaction.set_rollback(True)

        # --- Resumen final ---
        self.stdout.write(self.style.SUCCESS(
            f'\nResumen:\n'
            f'  Archivos {"creados" if apply else "se crearian"}:        {stats["creados"]}\n'
            f'  Archivos {"actualizados" if apply else "se actualizarian"}: {stats["actualizados"]}\n'
            f'  PDFs {"copiados" if apply else "se copiarian"}:           {stats["pdfs_copiados"]}\n'
            f'  PDFs ya existian (skip):                  {stats["pdfs_skip"]}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. Ejecuta con --apply para guardar.'
            ))
