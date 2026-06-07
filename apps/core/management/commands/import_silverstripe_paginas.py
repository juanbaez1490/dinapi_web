from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from apps.core.models import Pagina


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")


class Command(BaseCommand):
    help = "Importa tipos de pagina desde SiteTree (SilverStripe) hacia core.Pagina."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sql-path",
            default="dinapi_web_old/dinapi.sql",
            help="Ruta al dump SQL de SilverStripe.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Borra Pagina antes de importar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo analiza, sin escribir cambios.",
        )

    def handle(self, *args, **options):
        sql_path = Path(options["sql_path"]).resolve()
        truncate = options["truncate"]
        dry_run = options["dry_run"]

        if not sql_path.exists():
            raise CommandError(f"No existe el archivo SQL: {sql_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo: no se guardaran cambios."))

        summary = self._run(sql_path=sql_path, truncate=truncate, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS("Importacion de paginas finalizada"))
        self.stdout.write(
            f"Paginas: creadas={summary['created']} actualizadas={summary['updated']} omitidas={summary['skipped']}"
        )

    def _run(self, sql_path: Path, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {"created": 0, "updated": 0, "skipped": 0}

        valid_types = {choice[0] for choice in Pagina.TipoPagina.choices}

        if truncate and not dry_run:
            Pagina.objects.all().delete()

        context = transaction.atomic if not dry_run else _null_context
        with context():
            with sql_path.open("r", encoding="utf-8", errors="ignore") as f:
                in_insert = False
                current_columns: List[str] = []
                values_buffer: List[str] = []

                for line in f:
                    stripped = line.rstrip("\n")

                    if not in_insert:
                        match = INSERT_RE.match(stripped.strip())
                        if not match or match.group("table") != "SiteTree":
                            continue

                        current_columns = [c.strip().strip("`") for c in match.group("columns").split(",")]
                        in_insert = True
                        values_buffer = []
                        continue

                    values_buffer.append(stripped)

                    if stripped.strip().endswith(";"):
                        values_text = "\n".join(values_buffer)
                        rows = [_parse_tuple(t) for t in _extract_tuples(values_text)]

                        for row in rows:
                            data = dict(zip(current_columns, row))

                            old_id = _to_int(data.get("ID"))
                            class_name = (data.get("ClassName") or "").strip()
                            if not class_name:
                                summary["skipped"] += 1
                                continue

                            tipo = class_name if class_name in valid_types else Pagina.TipoPagina.GENERAL

                            title = (data.get("Title") or "").strip() or "Pagina"
                            menu_title = (data.get("MenuTitle") or "").strip()
                            titulo = menu_title or title
                            raw_slug = (data.get("URLSegment") or "").strip()
                            base_slug = slugify(raw_slug or titulo) or "pagina"
                            slug = f"{base_slug}-{old_id or 'sin-id'}"

                            parent_legacy_id = _to_int(data.get("ParentID")) or None
                            contenido = data.get("Content") or ""
                            descripcion = (data.get("MetaDescription") or "")[:500]
                            mostrar_en_menu = bool(_to_int(data.get("ShowInMenus")) or 0)
                            orden_menu = _to_int(data.get("Sort")) or 0
                            activo = True
                            fecha_publicacion = _parse_datetime(data.get("Created"))

                            if dry_run:
                                continue

                            pagina = Pagina.objects.filter(legacy_id=old_id).first()
                            if pagina is None:
                                pagina = Pagina.objects.filter(slug=slug).first()

                            defaults = {
                                "legacy_id": old_id,
                                "parent_legacy_id": parent_legacy_id,
                                "tipo": tipo,
                                "titulo": titulo,
                                "slug": slug,
                                "subtitulo": "",
                                "contenido": contenido,
                                "descripcion": descripcion,
                                "mostrar_en_menu": mostrar_en_menu,
                                "orden_menu": orden_menu,
                                "activo": activo,
                                "fecha_publicacion": fecha_publicacion,
                            }

                            if pagina is None:
                                Pagina.objects.create(**defaults)
                                created = True
                            else:
                                for field, value in defaults.items():
                                    setattr(pagina, field, value)
                                pagina.save()
                                created = False

                            if created:
                                summary["created"] += 1
                            else:
                                summary["updated"] += 1

                        in_insert = False
                        current_columns = []
                        values_buffer = []

        return summary


class _null_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _extract_tuples(values_text: str) -> List[str]:
    tuples: List[str] = []
    in_string = False
    escape = False
    depth = 0
    start = -1

    for i, ch in enumerate(values_text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_string = False
            continue

        if ch == "'":
            in_string = True
            continue

        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start >= 0:
                tuples.append(values_text[start : i + 1])
                start = -1

    return tuples


def _parse_tuple(tuple_text: str) -> List[object]:
    inner = tuple_text[1:-1]
    parts: List[str] = []
    buf: List[str] = []
    in_string = False
    escape = False

    for ch in inner:
        if in_string:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_string = False
            continue

        if ch == "'":
            in_string = True
            buf.append(ch)
            continue

        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue

        buf.append(ch)

    parts.append("".join(buf).strip())
    return [_decode_value(p) for p in parts]


def _decode_value(value: str):
    if value.upper() == "NULL":
        return None

    if value.startswith("'") and value.endswith("'"):
        s = value[1:-1]
        return (
            s.replace("\\\\", "\\")
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace("\\0", "\0")
        )

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value

    return value


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: object):
    if not value:
        return None
    try:
        dt = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        return timezone.make_aware(dt, timezone.get_current_timezone())
    except ValueError:
        return None
