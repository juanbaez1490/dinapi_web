from __future__ import annotations

from pathlib import Path
import re
import shutil

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.noticias.models import Noticia
from apps.core.models import Pagina


ASSET_PATTERNS = [
    # src/href="assets/..."
    (re.compile(r'(["\'])assets/'), r'\1/media/legacy/assets/'),
    # src/href="/assets/..."
    (re.compile(r'(["\'])/assets/'), r'\1/media/legacy/assets/'),
    # urls absolutas del sitio viejo
    (re.compile(r'(["\'])https?://www\.dinapi\.gov\.py/portal/v3/assets/'), r'\1/media/legacy/assets/'),
    (re.compile(r'(["\'])/portal/v3/assets/'), r'\1/media/legacy/assets/'),
    # Casos sin comillas (texto plano en HTML heredado)
    (re.compile(r'https?://www\.dinapi\.gov\.py/portal/v3/assets/'), r'/media/legacy/assets/'),
    (re.compile(r'/portal/v3/assets/'), r'/media/legacy/assets/'),
]


class Command(BaseCommand):
    help = "Copia assets de SilverStripe a media y normaliza rutas en contenido HTML migrado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-assets",
            default="dinapi_web_old/assets",
            help="Directorio assets del proyecto SilverStripe.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo informa cambios, sin escribir archivos ni DB.",
        )

    def handle(self, *args, **options):
        source_assets = Path(options["source_assets"]).resolve()
        dry_run = options["dry_run"]

        if not source_assets.exists() or not source_assets.is_dir():
            raise CommandError(f"No se encontro directorio de assets: {source_assets}")

        media_root = Path(settings.MEDIA_ROOT)
        legacy_assets_target = media_root / "legacy" / "assets"
        noticia_images_target = media_root / "noticias" / "imagenes-noticias"

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se guardaran cambios."))

        copied_files = self._copy_assets(
            source_assets=source_assets,
            legacy_assets_target=legacy_assets_target,
            noticia_images_target=noticia_images_target,
            dry_run=dry_run,
        )

        db_changes = self._normalize_db_urls(dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS("Sincronizacion de assets finalizada"))
        self.stdout.write(f"Archivos copiados/actualizados: {copied_files}")
        self.stdout.write(
            "Contenido actualizado: "
            f"noticias={db_changes['noticias']} paginas={db_changes['paginas']}"
        )

    def _copy_assets(
        self,
        source_assets: Path,
        legacy_assets_target: Path,
        noticia_images_target: Path,
        dry_run: bool,
    ) -> int:
        copied = 0
        media_root = Path(settings.MEDIA_ROOT)

        # Capa 1: copia completa para preservar enlaces historicos (HTML embebido).
        copied += self._copy_tree(source_assets, legacy_assets_target, dry_run=dry_run)

        # Capa 2: compatibilidad con ImageField de Noticia (media/noticias/imagenes-noticias).
        legacy_news_images = source_assets / "noticias" / "imagenes-noticias"
        if legacy_news_images.exists() and legacy_news_images.is_dir():
            copied += self._copy_tree(legacy_news_images, noticia_images_target, dry_run=dry_run)

        # Capa 3: subcarpetas que los ImageField del modelo referencian
        # con su misma estructura (sin prefijo legacy/assets/).
        # Cada subdir legacy se espeja 1-a-1 bajo MEDIA_ROOT.
        imagefield_subdirs = [
            "imagenes-tarjeta",
            "Uploads",
            "imagenes-pop-up",
            "iconos-quick-access",
            "imagenes-acordeon",
            "iconos-eje",
            "configuracion",
            "paginas",
            "concursos",
            "tarjetas",
            "acordeon",
        ]
        for sub in imagefield_subdirs:
            src = source_assets / sub
            if not src.exists() or not src.is_dir():
                continue
            dst = media_root / sub
            copied += self._copy_tree(src, dst, dry_run=dry_run)

        return copied

    def _copy_tree(self, source: Path, target: Path, dry_run: bool) -> int:
        count = 0
        for src_file in source.rglob("*"):
            if not src_file.is_file():
                continue

            rel_path = src_file.relative_to(source)
            dst_file = target / rel_path

            should_copy = True
            if dst_file.exists():
                should_copy = (
                    src_file.stat().st_size != dst_file.stat().st_size
                    or int(src_file.stat().st_mtime) > int(dst_file.stat().st_mtime)
                )

            if not should_copy:
                continue

            count += 1
            if dry_run:
                continue

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

        return count

    def _normalize_db_urls(self, dry_run: bool) -> dict:
        changes = {"noticias": 0, "paginas": 0}

        context = transaction.atomic if not dry_run else _null_context
        with context():
            for noticia in Noticia.objects.all().only("id", "contenido"):
                original = noticia.contenido or ""
                updated = _normalize_html_assets(original)
                if updated != original:
                    changes["noticias"] += 1
                    if not dry_run:
                        noticia.contenido = updated
                        noticia.save(update_fields=["contenido"])

            for pagina in Pagina.objects.all().only("id", "contenido"):
                original = pagina.contenido or ""
                updated = _normalize_html_assets(original)
                if updated != original:
                    changes["paginas"] += 1
                    if not dry_run:
                        pagina.contenido = updated
                        pagina.save(update_fields=["contenido"])

        return changes


class _null_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _normalize_html_assets(content: str) -> str:
    normalized = content
    for pattern, replacement in ASSET_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized
