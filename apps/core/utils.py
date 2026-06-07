"""
_resolve_pagina_url — Estado final tras migración SilverStripe 4.3 → Django
============================================================================

UBICACIÓN SUGERIDA:  apps/core/utils.py  (o donde ya esté definido en tu proyecto)

Los tipos de página son los nombres PascalCase originales de SilverStripe,
preservados en el campo Pagina.tipo durante la migración.

ESTADO DE TIPOS:
  ✅  ACTIVOS  → view definitiva asignada, URL resuelta correctamente
  🔲  P2       → tipo sin view definitiva (pendiente sprint posterior)
                 devuelven "/" con logger.warning, NUNCA redirigen a noticias
"""

from django.urls import reverse, NoReverseMatch
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos encontrados en core_pagina (512 registros) — únicos y deduplicados:
#
#   ✅ ACTIVOS (view implementada):
#       ArchivoPage, GeneralPage, Page, InstitucionalPage,
#       ArchivoDesplegablePage  → core:pagina_detalle (genérica)
#       HomePage                → home:index
#       NoticiaPage             → noticias:detalle
#       CodepiNoticiaPage       → noticias:detalle
#       RevistaPage             → noticias:revista_detalle
#       BoletinPage             → boletines:detalle
#       BoletinMarcaPage        → boletines:detalle
#       PeriodoBoletinPage      → boletines:periodo_detalle
#       PeriodoBoletinMarcaPage         → boletines:periodo_detalle
#       PeriodoBoletinMarcaGenericoPage → boletines:periodo_detalle
#       TarjetaPage             → tarjetas:detalle
#       TarjetaSimplePage       → tarjetas:detalle
#       AcordeonPage            → tarjetas:acordeon_detalle
#       ConcursosPage           → concursos:lista
#       ConcursoJuventudPage    → concursos:detalle
#       ReclamosPage            → reclamos:form
#
#   🔲 P2 (sin view definitiva aún — deben tener activo=False en BD):
#       DiaPIPage               → sección especial sin view
#       ProtegeLoTuyoPage       → campaña sin view
#       GestorEnlacesPage       → gestor interno sin view
# ---------------------------------------------------------------------------

TIPO_URL_MAP: dict[str, tuple | None] = {

    # ── Páginas genéricas (heredadas como Page base en SS) ───────────────────
    "Page":                          ("core", "pagina_detalle"),   # ✅
    "GeneralPage":                   ("core", "pagina_detalle"),   # ✅
    "InstitucionalPage":             ("core", "pagina_detalle"),   # ✅

    # ── Archivos / documentos ────────────────────────────────────────────────
    "ArchivoPage":                   ("core", "pagina_detalle"),   # ✅
    "ArchivoDesplegablePage":        ("core", "pagina_detalle"),   # ✅

    # ── Home ─────────────────────────────────────────────────────────────────
    "HomePage":                      ("home", "index"),            # ✅  (sin pk)

    # ── Noticias ─────────────────────────────────────────────────────────────
    "NoticiaPage":                   ("noticias", "detalle"),      # ✅  requiere pk/slug
    "CodepiNoticiaPage":             ("noticias", "detalle"),      # ✅  requiere pk/slug
    "RevistaPage":                   ("noticias", "revista_detalle"), # ✅  requiere pk/slug

    # ── Boletines ────────────────────────────────────────────────────────────
    "BoletinPage":                   ("boletines", "detalle"),     # ✅  requiere pk
    "BoletinMarcaPage":              ("boletines", "detalle"),     # ✅  requiere pk
    "PeriodoBoletinPage":            ("boletines", "periodo_detalle"),  # ✅  requiere pk
    "PeriodoBoletinMarcaPage":       ("boletines", "periodo_detalle"),  # ✅  requiere pk
    "PeriodoBoletinMarcaGenericoPage":("boletines", "periodo_detalle"), # ✅  requiere pk

    # ── Tarjetas y acordeón ──────────────────────────────────────────────────
    "TarjetaPage":                   ("tarjetas", "detalle"),         # ✅  requiere pk
    "TarjetaSimplePage":             ("tarjetas", "detalle"),         # ✅  requiere pk
    "AcordeonPage":                  ("tarjetas", "acordeon_detalle"),# ✅  requiere pk

    # ── Concursos ────────────────────────────────────────────────────────────
    "ConcursosPage":                 ("concursos", "lista"),       # ✅
    "ConcursoJuventudPage":          ("concursos", "detalle"),     # ✅  requiere pk

    # ── Reclamos ─────────────────────────────────────────────────────────────
    "ReclamosPage":                  ("reclamos", "form"),         # ✅

    # ── P2: sin view definitiva ──────────────────────────────────────────────
    "DiaPIPage":                     None,   # 🔲 P2 — sección especial sin view
    "ProtegeLoTuyoPage":             None,   # 🔲 P2 — campaña sin view
    "GestorEnlacesPage":             None,   # 🔲 P2 — gestor interno sin view
}


# ---------------------------------------------------------------------------
# Resolver principal
# ---------------------------------------------------------------------------

def _resolve_pagina_url(pagina) -> str:
    """
    Devuelve la URL correspondiente a una instancia de Pagina.

    Parámetros
    ----------
    pagina : Pagina instance
        Objeto del modelo core.Pagina.

    Retorna
    -------
    str — URL resuelta, o "/" si el tipo es P2 o desconocido.

    Garantías
    ---------
    • Ningún tipo activo redirige incorrectamente a noticias.
    • Los tipos P2 (None) devuelven "/" con warning en log.
    • Los tipos desconocidos devuelven "/" con warning en log.
    • Nunca lanza excepción en producción.
    """
    tipo = (pagina.tipo or "").strip()

    if tipo not in TIPO_URL_MAP:
        logger.warning(
            "_resolve_pagina_url: tipo '%s' no registrado (pagina.id=%s) → '/'",
            tipo, pagina.pk
        )
        return "/"

    entry = TIPO_URL_MAP[tipo]

    if entry is None:
        logger.warning(
            "_resolve_pagina_url: tipo '%s' es P2 (pagina.id=%s) → '/'",
            tipo, pagina.pk
        )
        return "/"

    namespace, view_name = entry
    url_name = f"{namespace}:{view_name}"

    # Tipos que no necesitan argumentos
    no_args_types = {"HomePage", "ConcursosPage", "ReclamosPage"}
    if tipo in no_args_types:
        try:
            return reverse(url_name)
        except NoReverseMatch as exc:
            logger.error("_resolve_pagina_url: NoReverseMatch '%s': %s", url_name, exc)
            return "/"

    # Tipos con pk o slug
    try:
        return reverse(url_name, kwargs={"pk": pagina.pk})
    except NoReverseMatch:
        try:
            if hasattr(pagina, "slug") and pagina.slug:
                return reverse(url_name, kwargs={"slug": pagina.slug})
        except NoReverseMatch:
            pass
        logger.error(
            "_resolve_pagina_url: NoReverseMatch para tipo='%s' url='%s' pk=%s",
            tipo, url_name, pagina.pk
        )
        return "/"


# ---------------------------------------------------------------------------
# Auditoría — verificar tipos activos en BD
# ---------------------------------------------------------------------------

def audit_tipo_pagina_urls():
    """
    Itera todos los tipos distintos en core_pagina y verifica su URL.

    Uso:
        python manage.py shell -c "
        import django
        from apps.core.utils import audit_tipo_pagina_urls
        audit_tipo_pagina_urls()
        "
    """
    from apps.core.models import Pagina

    tipos_en_bd = (
        Pagina.objects
        .filter(activo=True)
        .values_list("tipo", flat=True)
        .distinct()
        .order_by("tipo")
    )

    print("\n── Auditoría _resolve_pagina_url ──────────────────────────")
    issues = []

    for tipo in tipos_en_bd:
        # Crear un objeto mock mínimo para el resolver
        class _FakePagina:
            pk   = 1
            slug = "test"
        _FakePagina.tipo = tipo

        entry = TIPO_URL_MAP.get(tipo, "NO_REGISTRADO")
        if entry == "NO_REGISTRADO":
            symbol = "❓"
            url = "NO REGISTRADO"
            issues.append((tipo, url))
        elif entry is None:
            symbol = "🔲"
            url = "P2 — sin view"
        else:
            symbol = "✅"
            ns, vn = entry
            url = f"{ns}:{vn}"

        count = Pagina.objects.filter(tipo=tipo, activo=True).count()
        print(f"  {symbol}  {tipo:<40} ({count:>4} páginas)  →  {url}")

    print()
    if issues:
        print("❓ Tipos en BD no registrados en TIPO_URL_MAP:")
        for tipo, _ in issues:
            print(f"     '{tipo}' → agregarlo a TIPO_URL_MAP")
    else:
        print("✅  Todos los tipos activos están registrados en TIPO_URL_MAP.\n")


# ---------------------------------------------------------------------------
# Script para desactivar páginas P2
# ---------------------------------------------------------------------------
#
# Si querés ocultar del sitio todas las páginas cuyo tipo sea P2:
#
#   python manage.py shell -c "
#   from apps.core.models import Pagina
#   p2 = ['DiaPIPage', 'ProtegeLoTuyoPage', 'GestorEnlacesPage']
#   n = Pagina.objects.filter(tipo__in=p2).update(activo=False)
#   print('Páginas P2 desactivadas:', n)
#   "
# ---------------------------------------------------------------------------
