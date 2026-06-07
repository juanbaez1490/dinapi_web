"""
Management command: validate_migration
Uso: python manage.py validate_migration

Compara conteos de registros entre MySQL origen y SQLite/Postgres destino,
verifica campos críticos sin valores nulos inesperados, e imprime un reporte
con ✅ / ⚠️ por tabla.

Colocar en:  <tu_app>/management/commands/validate_migration.py
(o en cualquier app que ya tenga el directorio management/commands/)
"""

import sys
from django.core.management.base import BaseCommand
from django.db import connections, connection


# ---------------------------------------------------------------------------
# CONFIGURACIÓN: ajustá "mysql_source" al alias definido en settings.DATABASES
# ---------------------------------------------------------------------------
MYSQL_ALIAS = "mysql_source"   # alias de la BD origen en settings.DATABASES

# Mapa: tabla Django (en destino) → tabla MySQL origen
# Ajustá los nombres de tabla si difieren en el origen.
TABLE_MAP = {
    # destino (tabla real SQLite)              origen MySQL (ajustar si difiere)
    # ── Noticias ────────────────────────────────────────────────────────────
    "noticias_noticia":                        "noticias_noticia",
    "noticias_categorianoticia":               "noticias_categorianoticia",
    # ── Páginas (en app core) ────────────────────────────────────────────────
    "core_pagina":                             "paginas_pagina",
    # ── Boletines ────────────────────────────────────────────────────────────
    "boletines_boletin":                       "boletines_boletin",
    "boletines_periodoboletin":                "boletines_periodoboletin",
    # ── Biblioteca ───────────────────────────────────────────────────────────
    "biblioteca_biblioteca":                   "biblioteca_biblioteca",
    "biblioteca_documentobiblioteca":          "biblioteca_documento",
    "biblioteca_categoriabiblioteca":          "biblioteca_categoria",
    "biblioteca_etiquetabiblioteca":           "biblioteca_etiqueta",
    "biblioteca_imagenbiblioteca":             "biblioteca_imagen",
    "biblioteca_videobiblioteca":              "biblioteca_video",
    "biblioteca_biblioteca_documentos":        "biblioteca_biblioteca_documentos",
    "biblioteca_biblioteca_etiquetas":         "biblioteca_biblioteca_etiquetas",
    # ── Concursos ────────────────────────────────────────────────────────────
    "concursos_concurso":                      "concursos_concurso",
    # ── Tarjetas y acordeón (en app tarjetas) ───────────────────────────────
    "tarjetas_tarjeta":                        "tarjetas_tarjeta",
    "tarjetas_acordeonpage":                   "acordeon_acordeon",
    "tarjetas_acordeonitem":                   "acordeon_item",
    # ── Calendario ───────────────────────────────────────────────────────────
    "calendario_actividad":                    "calendario_evento",
    # ── Core: anuncios, carousel, enlaces, tema_eje, siteconfig ─────────────
    "core_anuncio":                            "anuncios_anuncio",
    "core_carouselitem":                       "carousel_slide",
    "core_enlaceinteres":                      "enlaces_interes_enlace",
    "core_temaeje":                            "tema_eje_temaeje",
    "core_siteconfig":                         "siteconfig_siteconfig",
    # ── Reclamos ─────────────────────────────────────────────────────────────
    "reclamos_reclamo":                        "reclamos_reclamo",
    # ── Menús ────────────────────────────────────────────────────────────────
    "menus_menuderecho":                       "menus_menuderecho",
    "menus_popup":                             "menus_popup",
}

# Campos críticos que NO deben tener NULL (destino): tabla → [campos]
CRITICAL_NULL_CHECKS = {
    "noticias_noticia":               ["id", "titulo", "fecha"],
    "noticias_categorianoticia":      ["id", "nombre"],
    "core_pagina":                    ["id", "titulo", "slug"],
    "boletines_boletin":              ["id", "titulo"],
    "boletines_periodoboletin":       ["id"],
    "biblioteca_biblioteca":          ["id", "titulo"],
    "biblioteca_documentobiblioteca": ["id", "titulo"],
    "biblioteca_categoriabiblioteca": ["id", "nombre"],
    "biblioteca_etiquetabiblioteca":  ["id", "nombre"],
    "concursos_concurso":             ["id", "titulo"],
    "tarjetas_tarjeta":               ["id", "titulo"],
    "tarjetas_acordeonpage":          ["id"],           # titulo_padre es opcional (heredado del contexto)
    "tarjetas_acordeonitem":          ["id", "titulo"],  # contenido puede ser vacío (ítems solo-título)
    "calendario_actividad":           ["id", "titulo"],
    "core_anuncio":                   ["id", "titulo"],
    "core_carouselitem":              ["id"],
    "core_enlaceinteres":             ["id", "titulo", "url"],
    "core_temaeje":                   ["id", "nombre"],
    "core_siteconfig":                ["id"],
    "reclamos_reclamo":               ["id", "nombre", "email"],
    "menus_menuderecho":              ["id"],
    "menus_popup":                    ["id"],
}

# Valores de recuento mínimo esperado (0 = no verificar mínimo)
MIN_EXPECTED = {
    "noticias_noticia": 1,
    "core_pagina":      1,
}


class Command(BaseCommand):
    help = (
        "Valida la migración comparando conteos MySQL→destino "
        "y verificando nulos en campos críticos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--mysql-alias",
            default=MYSQL_ALIAS,
            help=f"Alias de la BD MySQL en settings.DATABASES (default: {MYSQL_ALIAS})",
        )
        parser.add_argument(
            "--skip-mysql",
            action="store_true",
            help="Omitir comparación con MySQL (solo verificar nulos en destino)",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Detener al primer ⚠️  encontrado",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        alias   = options["mysql_alias"]
        skip_src = options["skip_mysql"]
        fail_fast = options["fail_fast"]

        warnings = 0
        ok_count = 0

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  REPORTE DE VALIDACIÓN DE MIGRACIÓN")
        self.stdout.write("=" * 60 + "\n")

        # ── 1. Verificar conexión a MySQL origen ──────────────────────
        if not skip_src:
            try:
                src_conn = connections[alias]
                src_conn.ensure_connection()
                self.stdout.write(f"🔌 MySQL origen  [{alias}]: CONECTADO\n")
            except Exception as exc:
                self.stderr.write(
                    f"⚠️  No se pudo conectar a MySQL origen [{alias}]: {exc}\n"
                    "    Continuando solo con verificación de nulos (--skip-mysql implícito).\n"
                )
                skip_src = True

        # ── 2. Recorrer tablas ────────────────────────────────────────
        for dest_table, src_table in TABLE_MAP.items():
            issues = []

            # -- 2a. Conteo en destino ------------------------------------
            dest_count = self._count(connection, dest_table)

            # -- 2b. Conteo en origen (MySQL) -----------------------------
            if not skip_src:
                src_count = self._count(connections[alias], src_table)
                if src_count is None:
                    issues.append(f"tabla '{src_table}' no encontrada en MySQL origen")
                elif dest_count is None:
                    issues.append(f"tabla '{dest_table}' no encontrada en destino")
                elif src_count != dest_count:
                    diff = src_count - dest_count
                    issues.append(
                        f"conteo difiere: MySQL={src_count}  destino={dest_count}  "
                        f"(faltan {diff})" if diff > 0 else
                        f"conteo difiere: MySQL={src_count}  destino={dest_count}  "
                        f"(sobran {abs(diff)})"
                    )

            # -- 2c. Mínimo esperado -------------------------------------
            if dest_count is not None:
                min_exp = MIN_EXPECTED.get(dest_table, 0)
                if min_exp and dest_count < min_exp:
                    issues.append(
                        f"destino tiene {dest_count} registros, mínimo esperado {min_exp}"
                    )

            # -- 2d. Nulos en campos críticos ----------------------------
            null_issues = self._check_nulls(dest_table)
            issues.extend(null_issues)

            # -- 2e. Imprimir resultado ----------------------------------
            cnt_str = f"{dest_count:>6}" if dest_count is not None else "  N/A "
            if issues:
                warnings += 1
                self.stdout.write(
                    f"⚠️   {dest_table:<45} [{cnt_str}]"
                )
                for iss in issues:
                    self.stdout.write(f"       → {iss}")
                if fail_fast:
                    self.stderr.write("\n[--fail-fast] Detenido en primer ⚠️\n")
                    sys.exit(1)
            else:
                ok_count += 1
                src_info = ""
                if not skip_src and self._count(connections[alias], src_table) is not None:
                    src_info = f"  (MySQL={self._count(connections[alias], src_table)})"
                self.stdout.write(
                    f"✅  {dest_table:<45} [{cnt_str}]{src_info}"
                )

        # ── 3. Resumen ────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"  ✅  OK:        {ok_count}")
        self.stdout.write(f"  ⚠️   Warnings:  {warnings}")
        self.stdout.write("=" * 60 + "\n")

        if warnings:
            self.stderr.write(
                f"\n⚠️  La migración tiene {warnings} problema(s) pendiente(s). "
                "Revisá los detalles arriba.\n"
            )
            sys.exit(1)
        else:
            self.stdout.write(
                "\n✅  Todos los conteos y campos críticos están OK. "
                "La migración está limpia.\n"
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _count(self, conn, table_name: str):
        """Retorna el conteo de filas de una tabla, o None si no existe."""
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                return cur.fetchone()[0]
        except Exception:
            return None

    def _check_nulls(self, table_name: str):
        """Devuelve lista de strings describiendo nulos inesperados."""
        fields = CRITICAL_NULL_CHECKS.get(table_name)
        if not fields:
            return []

        issues = []
        for field in fields:
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        f"SELECT COUNT(*) FROM {table_name} "
                        f"WHERE {field} IS NULL OR CAST({field} AS TEXT) = ''"
                    )
                    null_count = cur.fetchone()[0]
                    if null_count:
                        issues.append(
                            f"campo '{field}' tiene {null_count} valor(es) nulo(s)/vacío(s)"
                        )
            except Exception as exc:
                issues.append(f"no se pudo verificar campo '{field}': {exc}")
        return issues
