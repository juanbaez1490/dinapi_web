"""
apps/core/admin.py
==================
Admin completo con proxy models para cada tipo de página.

Cada tipo aparece como sección separada en el admin, muestra solo los campos
relevantes, y asigna el campo `tipo` automáticamente al guardar.

IMPORTANTE: verificá los imports de modelos de otras apps (marcados con ⚠️)
y ajustá los nombres de clase si difieren en tu proyecto.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Pagina, SiteConfig, Anuncio, CarouselItem, EnlaceInteres, TemaEje


# ===========================================================================
# INLINES — modelos relacionados que se editan dentro de la página
# ===========================================================================

# AcordeonItem tiene FK a tarjetas.AcordeonPage (no a core.Pagina),
# por eso el inline se gestiona desde el admin de la app tarjetas.
HAS_ACORDEON_INLINE = False


# ===========================================================================
# MIXIN BASE — comportamiento compartido por todos los proxy admins
# ===========================================================================

class PaginaAdminMixin:
    """Mixin con campos comunes y lógica de guardado automático de `tipo`."""

    TIPO = None  # cada subclase define su tipo

    list_display  = ["titulo", "slug", "activo", "mostrar_en_menu", "orden_menu", "fecha_publicacion"]
    list_filter   = ["activo", "mostrar_en_menu"]
    search_fields = ["titulo", "slug"]
    prepopulated_fields = {"slug": ("titulo",)}
    ordering      = ["orden_menu", "titulo"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo=self.TIPO)

    def save_model(self, request, obj, form, change):
        obj.tipo = self.TIPO
        super().save_model(request, obj, form, change)


# ===========================================================================
# PROXY MODELS — uno por tipo de página
# ===========================================================================

class ArchivoPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Archivo"
        verbose_name_plural = "Páginas — Archivos (203)"

class ArchivoDesplegablePageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Archivo desplegable"
        verbose_name_plural = "Páginas — Archivos desplegables (8)"

class GeneralPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — General"
        verbose_name_plural = "Páginas — Generales (67)"

class PageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Base"
        verbose_name_plural = "Páginas — Base (5)"

class InstitucionalPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Institucional"
        verbose_name_plural = "Páginas — Institucionales (1)"

class HomePageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Home"
        verbose_name_plural = "Páginas — Home (1)"

class AcordeonPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Acordeón"
        verbose_name_plural = "Páginas — Acordeón (18)"

class NoticiaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Noticia"
        verbose_name_plural = "Páginas — Noticias (1)"

class CodepiNoticiaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Noticia CODEPI"
        verbose_name_plural = "Páginas — Noticias CODEPI (2)"

class RevistaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Revista"
        verbose_name_plural = "Páginas — Revistas (1)"

class BoletinPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Boletín"
        verbose_name_plural = "Páginas — Boletines (4)"

class BoletinMarcaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Boletín Marca"
        verbose_name_plural = "Páginas — Boletines Marca (11)"

class PeriodoBoletinPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Período Boletín"
        verbose_name_plural = "Páginas — Períodos Boletín (33)"

class PeriodoBoletinMarcaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Período Boletín Marca"
        verbose_name_plural = "Páginas — Períodos Boletín Marca (76)"

class PeriodoBoletinMarcaGenericoPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Período Boletín Marca Genérico"
        verbose_name_plural = "Páginas — Períodos Boletín Marca Genérico (60)"

class TarjetaPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Tarjeta"
        verbose_name_plural = "Páginas — Tarjetas (14)"

class TarjetaSimplePageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Tarjeta Simple"
        verbose_name_plural = "Páginas — Tarjetas Simples (1)"

class ConcursosPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Concursos"
        verbose_name_plural = "Páginas — Concursos (1)"

class ConcursoJuventudPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Concurso Juventud"
        verbose_name_plural = "Páginas — Concursos Juventud (1)"

class ReclamosPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Reclamos"
        verbose_name_plural = "Páginas — Reclamos (1)"

# P2 — se registran de solo lectura para visibilidad sin edición accidental
class DiaPIPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Día PI (P2)"
        verbose_name_plural = "Páginas — Día PI (P2)"

class ProtegeLoTuyoPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Protege lo Tuyo (P2)"
        verbose_name_plural = "Páginas — Protege lo Tuyo (P2)"

class GestorEnlacesPageProxy(Pagina):
    class Meta:
        proxy = True
        verbose_name        = "Página — Gestor de enlaces (P2)"
        verbose_name_plural = "Páginas — Gestor de enlaces (P2)"


# ===========================================================================
# MODELADMIN — uno por tipo
# ===========================================================================

# ── Páginas genéricas (ArchivoPage, GeneralPage, Page, etc.) ────────────────

CAMPOS_GENERICOS = [
    ("Identificación",  {"fields": ["titulo", "slug", "subtitulo"]}),
    ("Contenido",       {"fields": ["contenido", "descripcion", "imagen_principal"]}),
    ("Publicación",     {"fields": ["activo", "fecha_publicacion", "plantilla_personalizada"]}),
    ("Menú",            {"fields": ["mostrar_en_menu", "orden_menu"]}),
]

@admin.register(ArchivoPageProxy)
class ArchivoPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "ArchivoPage"
    fieldsets = CAMPOS_GENERICOS

@admin.register(ArchivoDesplegablePageProxy)
class ArchivoDesplegablePageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "ArchivoDesplegablePage"
    fieldsets = CAMPOS_GENERICOS

@admin.register(GeneralPageProxy)
class GeneralPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "GeneralPage"
    fieldsets = CAMPOS_GENERICOS

@admin.register(PageProxy)
class PageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "Page"
    fieldsets = CAMPOS_GENERICOS

@admin.register(InstitucionalPageProxy)
class InstitucionalPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "InstitucionalPage"
    fieldsets = CAMPOS_GENERICOS

# ── Home ─────────────────────────────────────────────────────────────────────

@admin.register(HomePageProxy)
class HomePageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO = "HomePage"
    fieldsets = [
        ("Identificación", {"fields": ["titulo", "slug"]}),
        ("Estado",         {"fields": ["activo"]}),
    ]

# ── Acordeón — con inline de ítems ───────────────────────────────────────────

@admin.register(AcordeonPageProxy)
class AcordeonPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO = "AcordeonPage"
    fieldsets = [
        ("Identificación", {"fields": ["titulo", "slug", "subtitulo"]}),
        ("Contenido",      {"fields": ["contenido", "imagen_principal"]}),
        ("Publicación",    {"fields": ["activo", "fecha_publicacion"]}),
        ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
    ]
    inlines = [AcordeonItemInline] if HAS_ACORDEON_INLINE else []

# ── Noticias ─────────────────────────────────────────────────────────────────

CAMPOS_NOTICIA = [
    ("Identificación", {"fields": ["titulo", "slug", "subtitulo"]}),
    ("Contenido",      {"fields": ["contenido", "descripcion", "imagen_principal"]}),
    ("Publicación",    {"fields": ["activo", "fecha_publicacion"]}),
    ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
]

@admin.register(NoticiaPageProxy)
class NoticiaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "NoticiaPage"
    fieldsets = CAMPOS_NOTICIA

@admin.register(CodepiNoticiaPageProxy)
class CodepiNoticiaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "CodepiNoticiaPage"
    fieldsets = CAMPOS_NOTICIA

@admin.register(RevistaPageProxy)
class RevistaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "RevistaPage"
    fieldsets = CAMPOS_NOTICIA

# ── Boletines ────────────────────────────────────────────────────────────────

CAMPOS_BOLETIN = [
    ("Identificación", {"fields": ["titulo", "slug", "subtitulo"]}),
    ("Contenido",      {"fields": ["contenido", "descripcion", "imagen_principal"]}),
    ("Publicación",    {"fields": ["activo", "fecha_publicacion"]}),
    ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
]

@admin.register(BoletinPageProxy)
class BoletinPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "BoletinPage"
    fieldsets = CAMPOS_BOLETIN

@admin.register(BoletinMarcaPageProxy)
class BoletinMarcaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "BoletinMarcaPage"
    fieldsets = CAMPOS_BOLETIN

@admin.register(PeriodoBoletinPageProxy)
class PeriodoBoletinPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "PeriodoBoletinPage"
    fieldsets = CAMPOS_BOLETIN

@admin.register(PeriodoBoletinMarcaPageProxy)
class PeriodoBoletinMarcaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "PeriodoBoletinMarcaPage"
    fieldsets = CAMPOS_BOLETIN

@admin.register(PeriodoBoletinMarcaGenericoPageProxy)
class PeriodoBoletinMarcaGenericoPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "PeriodoBoletinMarcaGenericoPage"
    fieldsets = CAMPOS_BOLETIN

# ── Tarjetas ─────────────────────────────────────────────────────────────────

CAMPOS_TARJETA = [
    ("Identificación", {"fields": ["titulo", "slug", "subtitulo"]}),
    ("Contenido",      {"fields": ["contenido", "descripcion", "imagen_principal"]}),
    ("Publicación",    {"fields": ["activo", "fecha_publicacion"]}),
    ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
]

@admin.register(TarjetaPageProxy)
class TarjetaPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "TarjetaPage"
    fieldsets = CAMPOS_TARJETA

@admin.register(TarjetaSimplePageProxy)
class TarjetaSimplePageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "TarjetaSimplePage"
    fieldsets = CAMPOS_TARJETA

# ── Concursos ────────────────────────────────────────────────────────────────

@admin.register(ConcursosPageProxy)
class ConcursosPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO = "ConcursosPage"
    fieldsets = [
        ("Identificación", {"fields": ["titulo", "slug"]}),
        ("Contenido",      {"fields": ["contenido", "descripcion", "imagen_principal"]}),
        ("Publicación",    {"fields": ["activo", "fecha_publicacion"]}),
        ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
    ]

@admin.register(ConcursoJuventudPageProxy)
class ConcursoJuventudPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO      = "ConcursoJuventudPage"
    fieldsets = CAMPOS_GENERICOS

# ── Reclamos ─────────────────────────────────────────────────────────────────

@admin.register(ReclamosPageProxy)
class ReclamosPageAdmin(PaginaAdminMixin, admin.ModelAdmin):
    TIPO = "ReclamosPage"
    fieldsets = [
        ("Identificación", {"fields": ["titulo", "slug"]}),
        ("Estado",         {"fields": ["activo"]}),
        ("Menú",           {"fields": ["mostrar_en_menu", "orden_menu"]}),
    ]

# ── P2: solo lectura ─────────────────────────────────────────────────────────

class P2AdminBase(PaginaAdminMixin, admin.ModelAdmin):
    """Admin de solo lectura para tipos P2 — visibles pero no editables."""
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(DiaPIPageProxy)
class DiaPIPageAdmin(P2AdminBase):
    TIPO = "DiaPIPage"

@admin.register(ProtegeLoTuyoPageProxy)
class ProtegeLoTuyoPageAdmin(P2AdminBase):
    TIPO = "ProtegeLoTuyoPage"

@admin.register(GestorEnlacesPageProxy)
class GestorEnlacesPageAdmin(P2AdminBase):
    TIPO = "GestorEnlacesPage"


# ===========================================================================
# OTROS MODELOS DE CORE
# ===========================================================================

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Identidad",      {"fields": ["titulo_sitio", "logo", "descripcion"]}),
        ("Contacto",       {"fields": ["email_contacto", "email_soporte", "telefono", "direccion"]}),
        ("URLs del footer",{"fields": ["url_horarios", "url_consultas"]}),
        ("Redes sociales", {"fields": ["url_facebook", "url_instagram", "url_youtube", "url_twitter"], "classes": ["collapse"]}),
    ]
    def has_add_permission(self, request):
        # Solo puede existir un SiteConfig
        return not SiteConfig.objects.exists()

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display  = ["titulo", "activo", "orden", "fecha_inicio", "fecha_fin"]
    list_filter   = ["activo"]
    search_fields = ["titulo"]
    ordering      = ["orden", "-fecha_inicio"]
    fields        = ["titulo", "descripcion", "imagen", "url",
                     "activo", "orden", "fecha_inicio", "fecha_fin"]

@admin.register(CarouselItem)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display  = ["titulo", "activo", "orden"]
    list_filter   = ["activo"]
    ordering      = ["orden"]
    fields        = ["titulo", "subtitulo", "imagen", "url", "texto_boton", "activo", "orden"]

@admin.register(EnlaceInteres)
class EnlaceInteresAdmin(admin.ModelAdmin):
    list_display  = ["titulo", "url", "activo", "orden"]
    list_filter   = ["activo"]
    ordering      = ["orden"]
    fields        = ["titulo", "descripcion", "url", "icono", "activo", "orden"]

@admin.register(TemaEje)
class TemaEjeAdmin(admin.ModelAdmin):
    list_display  = ["nombre", "eje", "activo", "orden"]
    list_filter   = ["activo", "eje"]
    search_fields = ["nombre"]
    ordering      = ["eje", "orden", "nombre"]
    fields        = ["nombre", "eje", "pagina", "url_externa", "orden", "activo"]
