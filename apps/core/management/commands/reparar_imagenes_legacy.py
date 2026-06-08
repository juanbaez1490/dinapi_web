"""
Repara los campos de imagen de Biblioteca y Noticia desde el SQL legacy:
- Para cada fila, lee el FK a tabla `File` legacy (ImagenPrincipalID / ImagenID).
- Resuelve Filename via la tabla File del SQL.
- Si el archivo fisico existe en dinapi_web_old/<Filename>:
    a. lo copia a media/<destino>/
    b. setea el campo `imagen_principal` / `imagen` del modelo
- Si NO existe el archivo fisico, opcionalmente limpia el campo
  (para que el template renderice el placeholder en lugar de imagen rota).

Casos comunes que produce "imagen rota":
- El SQL es mas nuevo que el snapshot de assets (las imagenes 2025-2026
  estan referenciadas pero no copiadas).
- Las primeras filas de File legacy (IDs 18, 21, 23) tienen Filename NULL
  pero estan referenciadas como placeholder por cientos de Bibliotecas.

Uso:
    python manage.py reparar_imagenes_legacy                  # dry-run
    python manage.py reparar_imagenes_legacy --apply
    python manage.py reparar_imagenes_legacy --apply --no-clean
"""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples


class Command(BaseCommand):
    help = 'Asocia/limpia campos de imagen de Biblioteca y Noticia segun los archivos fisicos disponibles.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al SQL legacy. Default: <BASE_DIR>/bd_legacy_bk_dinapi_2026-06-05.sql')
        parser.add_argument('--assets-root', default=None,
            help='Carpeta raiz de assets legacy. Default: <BASE_DIR>/dinapi_web_old')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')
        parser.add_argument('--no-clean', action='store_true',
            help='No limpia los campos cuando el archivo fisico no existe '
                 '(mantiene el path roto). Por default los limpia.')

    def handle(self, *args, **options):
        apply = options['apply']
        clean = not options['no_clean']

        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        assets_root = Path(options['assets_root'] or Path(settings.BASE_DIR) / 'dinapi_web_old')
        media_root = Path(settings.MEDIA_ROOT)

        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        self.stdout.write(f'SQL:        {sql_path}')
        self.stdout.write(f'Assets:     {assets_root}')
        self.stdout.write(f'Media:      {media_root}')
        self.stdout.write(f'Modo:       {"APLICAR" if apply else "DRY-RUN"}')
        self.stdout.write(f'Clean:      {"SI" if clean else "NO (mantiene paths rotos)"}\n')

        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # Lookup: File ID -> Filename (sin assets/)
        files_by_id = {}
        for t in iter_insert_tuples(sql_text, 'File'):
            if len(t) < 7 or not t[6]:
                continue
            files_by_id[t[0]] = t[6]
        self.stdout.write(f'Files indexados del SQL: {len(files_by_id)}\n')

        # === Biblioteca ===
        # Schema columnas: 0=ID, 1=ClassName, 2=Created, 3=LastEdited, 4=Titulo,
        # 5=Descripcion, 6=DescVideos, 7=DescImagenes, 8=DescDocumentos,
        # 9=EnlacesReferencias, 10=ImagenPrincipalID, 11=CategoriaID,
        # 12=FechaOrdenamiento, 13=Ocultar
        self.stdout.write('--- Biblioteca ---')
        bib_legacy = {}  # legacy_id -> ImagenPrincipalID
        for t in iter_insert_tuples(sql_text, 'Biblioteca'):
            if len(t) >= 11:
                bib_legacy[t[0]] = t[10]

        stats_bib = self._procesar_modelo(
            modelo_app='biblioteca',
            modelo_name='Biblioteca',
            campo='imagen_principal',
            destino_subdir='biblioteca/imagenes-principales',
            legacy_lookup=bib_legacy,
            files_by_id=files_by_id,
            assets_root=assets_root,
            media_root=media_root,
            apply=apply,
            clean=clean,
        )

        # === Noticia ===
        self.stdout.write('\n--- Noticia ---')
        not_legacy = {}  # legacy_id -> ImagenID
        for t in iter_insert_tuples(sql_text, 'Noticia'):
            if len(t) >= 10:
                not_legacy[t[0]] = t[9]

        stats_not = self._procesar_modelo(
            modelo_app='noticias',
            modelo_name='Noticia',
            campo='imagen',
            destino_subdir='noticias/imagenes-noticias',
            legacy_lookup=not_legacy,
            files_by_id=files_by_id,
            assets_root=assets_root,
            media_root=media_root,
            apply=apply,
            clean=clean,
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Resumen ===\n'
            f'Biblioteca:  asociadas={stats_bib["asociadas"]}  '
            f'limpiadas={stats_bib["limpiadas"]}  '
            f'ya_ok={stats_bib["ya_ok"]}  sin_legacy={stats_bib["sin_legacy"]}\n'
            f'Noticia:     asociadas={stats_not["asociadas"]}  '
            f'limpiadas={stats_not["limpiadas"]}  '
            f'ya_ok={stats_not["ya_ok"]}  sin_legacy={stats_not["sin_legacy"]}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))

    # ---------------------------------------------------------------

    def _procesar_modelo(self, modelo_app, modelo_name, campo, destino_subdir,
                          legacy_lookup, files_by_id, assets_root, media_root,
                          apply, clean):
        import re
        from django.apps import apps

        Model = apps.get_model(modelo_app, modelo_name)
        slug_re = re.compile(r'-(\d+)$')

        stats = {'asociadas': 0, 'limpiadas': 0, 'ya_ok': 0, 'sin_legacy': 0}
        dest_dir = media_root / destino_subdir

        with transaction.atomic():
            for obj in Model.objects.iterator():
                # Resolver legacy_id: prioriza obj.legacy_id, sino del slug
                legacy_id = getattr(obj, 'legacy_id', None)
                if not legacy_id and hasattr(obj, 'slug'):
                    m = slug_re.search(obj.slug or '')
                    if m:
                        legacy_id = int(m.group(1))
                if not legacy_id:
                    stats['sin_legacy'] += 1
                    continue

                file_id = legacy_lookup.get(legacy_id)
                fname = files_by_id.get(file_id) if file_id else None
                src = (assets_root / fname) if fname else None
                # Solo aceptamos archivos con extension de imagen valida.
                # En el legacy SilverStripe varios IDs huerfanos apuntan a
                # 'assets/error-404.html' como placeholder; excluimos eso.
                IMG_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
                tiene_archivo = (
                    src and src.exists() and src.is_file()
                    and src.suffix.lower() in IMG_EXTS
                )

                current = str(getattr(obj, campo) or '')
                expected_rel = ''
                if tiene_archivo:
                    expected_rel = f'{destino_subdir}/{src.name}'

                # Caso A: deberia tener archivo y ya esta correcto
                if expected_rel and current == expected_rel \
                        and (media_root / expected_rel).exists():
                    stats['ya_ok'] += 1
                    continue

                # Caso B: hay archivo fisico para asociar
                if tiene_archivo:
                    if apply:
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_file = dest_dir / src.name
                        if not dest_file.exists():
                            shutil.copy2(src, dest_file)
                        setattr(obj, campo, expected_rel)
                        Model.objects.filter(pk=obj.pk).update(**{campo: expected_rel})
                    stats['asociadas'] += 1
                    continue

                # Caso C: no hay archivo. Si clean y el campo tiene algo roto, limpiar.
                if clean and current:
                    media_full = media_root / current
                    if not media_full.exists():
                        if apply:
                            Model.objects.filter(pk=obj.pk).update(**{campo: ''})
                        stats['limpiadas'] += 1
                        continue

                stats['ya_ok'] += 1

            if not apply:
                transaction.set_rollback(True)
        return stats
