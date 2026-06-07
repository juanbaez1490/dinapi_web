from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from apps.noticias.models import CategoriaNoticia, Noticia


INSERT_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` \((?P<columns>[^)]+)\) VALUES$")


class Command(BaseCommand):
    help = "Importa CategoriaNoticia y Noticia desde un dump SQL de SilverStripe (MySQL)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sql-path",
            default="dinapi_web_old/dinapi.sql",
            help="Ruta al archivo SQL exportado de SilverStripe.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Cantidad maxima de noticias a importar (0 = sin limite).",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Borra categorias/noticias actuales antes de importar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analiza e informa, pero no guarda cambios.",
        )

    def handle(self, *args, **options):
        sql_path = Path(options["sql_path"]).resolve()
        limit = options["limit"]
        truncate = options["truncate"]
        dry_run = options["dry_run"]

        if not sql_path.exists():
            raise CommandError(f"No existe el archivo SQL: {sql_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run activo: no se escribiran cambios."))

        summary = self._run_import(sql_path=sql_path, limit=limit, truncate=truncate, dry_run=dry_run)

        self.stdout.write(self.style.SUCCESS("Importacion finalizada"))
        self.stdout.write(
            f"Categorias: creadas={summary['cats_created']} actualizadas={summary['cats_updated']}"
        )
        self.stdout.write(
            f"Noticias: creadas={summary['news_created']} actualizadas={summary['news_updated']} omitidas={summary['news_skipped']}"
        )

    def _run_import(self, sql_path: Path, limit: int, truncate: bool, dry_run: bool) -> Dict[str, int]:
        summary = {
            "cats_created": 0,
            "cats_updated": 0,
            "news_created": 0,
            "news_updated": 0,
            "news_skipped": 0,
        }

        old_cat_map: Dict[int, CategoriaNoticia] = {}
        old_image_map: Dict[int, str] = {}

        if truncate and not dry_run:
            Noticia.objects.all().delete()
            CategoriaNoticia.objects.all().delete()

        def process_statement(table: str, columns: List[str], rows: Iterable[List[object]]) -> None:
            nonlocal old_cat_map, old_image_map, summary

            if table == "CategoriaNoticia":
                for row in rows:
                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get("ID"))
                    nombre = (data.get("Categoria") or "Sin categoria").strip()
                    slug_base = slugify(nombre) or "categoria"
                    slug = slug_base
                    if old_id is not None:
                        slug = f"{slug_base}-{old_id}"

                    if dry_run:
                        continue

                    categoria, created = CategoriaNoticia.objects.update_or_create(
                        slug=slug,
                        defaults={
                            "nombre": nombre,
                            "descripcion": "",
                        },
                    )
                    if old_id is not None:
                        old_cat_map[old_id] = categoria
                    if created:
                        summary["cats_created"] += 1
                    else:
                        summary["cats_updated"] += 1

            elif table == "File":
                for row in rows:
                    data = dict(zip(columns, row))
                    class_name = (data.get("ClassName") or "").strip()
                    if class_name not in {"Image", "File"}:
                        continue
                    old_id = _to_int(data.get("ID"))
                    filename = (data.get("Filename") or "").strip()
                    if not old_id or not filename:
                        continue
                    old_image_map[old_id] = filename

            elif table == "Noticia":
                imported = 0
                for row in rows:
                    if limit and imported >= limit:
                        break

                    data = dict(zip(columns, row))
                    old_id = _to_int(data.get("ID"))
                    titulo = (data.get("Titulo") or "").strip()
                    if not titulo:
                        summary["news_skipped"] += 1
                        continue

                    categoria_old_id = _to_int(data.get("Categoria"))
                    categoria = old_cat_map.get(categoria_old_id)
                    if not categoria and not dry_run:
                        categoria, _ = CategoriaNoticia.objects.get_or_create(
                            slug="sin-categoria",
                            defaults={"nombre": "Sin categoria", "descripcion": ""},
                        )

                    fecha = _parse_date(data.get("Fecha")) or timezone.now().date()
                    destacado = bool(_to_int(data.get("Destacado")) or 0)
                    contenido = data.get("Content") or ""
                    slug = f"{slugify(titulo) or 'noticia'}-{old_id or 'sin-id'}"

                    imagen_path: Optional[str] = None
                    imagen_old_id = _to_int(data.get("ImagenID"))
                    if imagen_old_id and imagen_old_id in old_image_map:
                        raw_filename = old_image_map[imagen_old_id]
                        # Convierte assets/noticias/... a noticias/... para MEDIA_ROOT en Django.
                        if raw_filename.startswith("assets/"):
                            imagen_path = raw_filename[len("assets/") :]
                        else:
                            imagen_path = raw_filename

                    if dry_run:
                        imported += 1
                        continue

                    defaults = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "fecha": fecha,
                        "contenido": contenido,
                        "destacado": destacado,
                        "activo": True,
                    }
                    if imagen_path:
                        defaults["imagen"] = imagen_path

                    noticia, created = Noticia.objects.update_or_create(slug=slug, defaults=defaults)
                    if created:
                        summary["news_created"] += 1
                    else:
                        summary["news_updated"] += 1
                    imported += 1

        context = transaction.atomic if not dry_run else _null_context
        with context():
            self._scan_mysql_dump(sql_path, process_statement)

        return summary

    def _scan_mysql_dump(self, sql_path: Path, on_statement) -> None:
        target_tables = {"CategoriaNoticia", "File", "Noticia"}

        with sql_path.open("r", encoding="utf-8", errors="ignore") as f:
            in_insert = False
            current_table = ""
            current_columns: List[str] = []
            values_buffer: List[str] = []

            for line in f:
                stripped = line.rstrip("\n")

                if not in_insert:
                    match = INSERT_RE.match(stripped.strip())
                    if not match:
                        continue

                    table = match.group("table")
                    if table not in target_tables:
                        continue

                    columns = [c.strip().strip("`") for c in match.group("columns").split(",")]
                    in_insert = True
                    current_table = table
                    current_columns = columns
                    values_buffer = []
                    continue

                values_buffer.append(stripped)

                if stripped.strip().endswith(";"):
                    values_text = "\n".join(values_buffer)
                    tuple_strings = _extract_tuples(values_text)
                    rows = [_parse_tuple(ts) for ts in tuple_strings]
                    on_statement(current_table, current_columns, rows)

                    in_insert = False
                    current_table = ""
                    current_columns = []
                    values_buffer = []


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
    assert tuple_text.startswith("(") and tuple_text.endswith(")")
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
    return [_decode_sql_value(p) for p in parts]


def _decode_sql_value(value: str) -> object:
    if value.upper() == "NULL":
        return None

    if value.startswith("'") and value.endswith("'"):
        s = value[1:-1]
        s = (
            s.replace("\\\\", "\\")
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace("\\0", "\0")
        )
        return s

    # Mantener numeros como enteros cuando sea posible.
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


def _parse_date(value: object):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None
