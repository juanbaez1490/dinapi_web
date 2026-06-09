"""
apps/core/admin.py
==================
Admin unificado de Páginas con vista jerárquica.

- Un único modelo "Páginas" en el sidebar (no 23 proxy models).
- Listado con indentación según parent_legacy_id (Padre → Hijo → Nieto).
- Filtros: tipo, activo, en menú + toggle "Mostrar páginas técnicas"
  (boletines y períodos, ocultos por defecto).
- Páginas P2 (DiaPI, ProtegeLoTuyo, GestorEnlaces) NO aparecen.
- En el detalle: panel con páginas hijas + link a subelementos según tipo
  (Archivos, Tarjetas, AcordeonItems).
"""
from django.contrib import admin
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .models import Pagina, SiteConfig, Anuncio, CarouselItem, EnlaceInteres, TemaEje


# ---------------------------------------------------------------------------
# Sets de tipos para filtros y ocultamiento
# ---------------------------------------------------------------------------

# Tipos "técnicos" — colecciones de boletines/periodos que no se editan a mano.
# Ocultos por defecto en el listado; visibles al activar el filtro.
TIPOS_TECNICOS = {
    Pagina.TipoPagina.BOLETIN,
    Pagina.TipoPagina.BOLETIN_MARCA,
    Pagina.TipoPagina.PERIODO_BOLETIN,
    Pagina.TipoPagina.PERIODO_BOLETIN_MARCA,
    Pagina.TipoPagina.PERIODO_BOLETIN_MARCA_GENERICO,
}

# Tipos P2 — funciones que ya no están en uso, no aparecen en el admin.
TIPOS_P2_OCULTOS = {
    Pagina.TipoPagina.DIA_PI,
    Pagina.TipoPagina.PROTEGE_LO_TUYO,
    Pagina.TipoPagina.GESTOR_ENLACES,
}

# Mapeo tipo de página → app/modelo del subelemento editable
# (legacy_id de la Pagina se usa como filtro en la URL del admin).
SUBELEMENTOS_POR_TIPO = {
    Pagina.TipoPagina.ACORDEON: (
        'tarjetas', 'acordeonitem',
        'pagina__legacy_id',
        'Items del acordeón',
    ),
    Pagina.TipoPagina.TARJETAS: (
        'tarjetas', 'tarjeta',
        'pagina__legacy_id',
        'Tarjetas',
    ),
    Pagina.TipoPagina.TARJETAS_SIMPLES: (
        'tarjetas', 'tarjetasimple',
        'pagina_legacy_id',
        'Tarjetas simples',
    ),
    Pagina.TipoPagina.ARCHIVOS: (
        'archivos', 'archivo',
        'pagina_legacy_id',
        'Archivos / PDFs',
    ),
    Pagina.TipoPagina.ARCHIVO_DESPLEGABLE: (
        'archivos', 'archivo',
        'pagina_legacy_id',
        'Archivos / PDFs',
    ),
}


# ---------------------------------------------------------------------------
# Filtros custom
# ---------------------------------------------------------------------------

class MostrarTecnicasFilter(admin.SimpleListFilter):
    """Toggle para mostrar/ocultar páginas técnicas (boletines y períodos)."""
    title = 'Páginas técnicas'
    parameter_name = 'tecnicas'

    def lookups(self, request, model_admin):
        return [
            ('si', 'Mostrar (boletines, períodos)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'si':
            return queryset
        return queryset.exclude(tipo__in=TIPOS_TECNICOS)

    def choices(self, changelist):
        # Personaliza la etiqueta del default
        yield {
            'selected': self.value() is None,
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': 'Ocultas (default)',
        }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }


class FiltroSoloRootFilter(admin.SimpleListFilter):
    """Toggle para mostrar solo páginas raíz (sin padre)."""
    title = 'Jerarquía'
    parameter_name = 'jerarquia'

    def lookups(self, request, model_admin):
        return [
            ('root', 'Solo páginas raíz (sin padre)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'root':
            return queryset.filter(parent_legacy_id__isnull=True)
        return queryset


# ---------------------------------------------------------------------------
# PaginaAdmin — el único admin de páginas
# ---------------------------------------------------------------------------

@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = [
        'titulo_indentado',
        'tipo_display',
        'padre_display',
        'hijos_count_display',
        'activo',
        'mostrar_en_menu',
        'orden_menu',
    ]
    list_editable = ['activo', 'mostrar_en_menu', 'orden_menu']
    list_filter = [MostrarTecnicasFilter, FiltroSoloRootFilter, 'tipo', 'activo', 'mostrar_en_menu']
    list_per_page = 100
    search_fields = ['titulo', 'slug']
    prepopulated_fields = {}
    ordering = ['parent_legacy_id', 'orden_menu', 'titulo']
    save_on_top = True

    readonly_fields = ['legacy_id', 'hijos_panel', 'subelementos_panel']

    fieldsets = [
        ('Información básica', {
            'fields': ['titulo', 'slug', 'tipo', 'subtitulo'],
        }),
        ('Jerarquía', {
            'fields': ['parent_legacy_id', 'orden_menu', 'mostrar_en_menu'],
            'description': 'Indica la página padre por su legacy_id. '
                           'Si no tiene padre, dejar vacío (será una página raíz).',
        }),
        ('Contenido', {
            'fields': ['contenido', 'descripcion', 'imagen_principal'],
        }),
        ('Publicación', {
            'fields': ['activo', 'fecha_publicacion', 'plantilla_personalizada'],
        }),
        ('Páginas hijas y subelementos', {
            'fields': ['hijos_panel', 'subelementos_panel'],
        }),
        ('Datos legacy (referencia, no editar)', {
            'fields': ['legacy_id'],
            'classes': ['collapse'],
        }),
    ]

    # ------ Queryset con annotations ------

    def get_queryset(self, request):
        qs = super().get_queryset(request).exclude(tipo__in=TIPOS_P2_OCULTOS)

        # Conteo de hijos vía subquery (parent_legacy_id no es FK)
        hijos_sq = (
            Pagina.objects
            .filter(parent_legacy_id=OuterRef('legacy_id'))
            .exclude(tipo__in=TIPOS_P2_OCULTOS)
            .values('parent_legacy_id')
            .annotate(c=Count('id'))
            .values('c')
        )
        qs = qs.annotate(
            _hijos_count=Coalesce(Subquery(hijos_sq), 0, output_field=IntegerField()),
        )

        # Cachea (en la instancia) un mapa legacy_id → (titulo, parent_legacy_id)
        # para construir indentación y enlaces a padre sin N+1 queries.
        self._lookup = {
            p['legacy_id']: (p['titulo'], p['parent_legacy_id'], p['id'])
            for p in Pagina.objects
                .exclude(tipo__in=TIPOS_P2_OCULTOS)
                .values('legacy_id', 'titulo', 'parent_legacy_id', 'id')
                if p['legacy_id'] is not None
        }
        return qs

    # ------ Columnas del listado ------

    def _calc_nivel(self, legacy_id, max_depth=8):
        """Recursivo, con guard anti-ciclos."""
        if not legacy_id:
            return 0
        nivel = 0
        visited = set()
        current = legacy_id
        while current and nivel < max_depth and current not in visited:
            visited.add(current)
            info = self._lookup.get(current)
            if not info:
                break
            parent = info[1]
            if not parent:
                break
            nivel += 1
            current = parent
        return nivel

    def titulo_indentado(self, obj):
        nivel = self._calc_nivel(obj.parent_legacy_id) + (1 if obj.parent_legacy_id else 0)
        if nivel == 0:
            prefix = ''
        else:
            prefix = format_html(
                '<span style="color: #aab; font-family: monospace;">{}└─ </span>',
                '   ' * (nivel - 1),
            )
        return format_html(
            '{}{}<small style="color: #999; margin-left: .5em;">{}</small>',
            prefix, obj.titulo, obj.slug,
        )
    titulo_indentado.short_description = 'Título'
    titulo_indentado.admin_order_field = 'titulo'

    def tipo_display(self, obj):
        return obj.get_tipo_display()
    tipo_display.short_description = 'Tipo'
    tipo_display.admin_order_field = 'tipo'

    def padre_display(self, obj):
        if not obj.parent_legacy_id:
            return mark_safe('<em style="color: #aaa;">— raíz —</em>')
        info = self._lookup.get(obj.parent_legacy_id)
        if not info:
            return f'legacy_id={obj.parent_legacy_id} (no encontrado)'
        titulo, _, pk = info
        url = reverse('admin:core_pagina_change', args=[pk])
        return format_html('<a href="{}">{}</a>', url, titulo)
    padre_display.short_description = 'Padre'

    def hijos_count_display(self, obj):
        n = getattr(obj, '_hijos_count', 0)
        if not n:
            return mark_safe('<span style="color: #ccc;">0</span>')
        url = reverse('admin:core_pagina_changelist') + f'?parent_legacy_id={obj.legacy_id}'
        return format_html('<a href="{}" style="font-weight: 600;">{}</a>', url, n)
    hijos_count_display.short_description = '# hijos'
    hijos_count_display.admin_order_field = '_hijos_count'

    # ------ Panels readonly en el detalle ------

    def hijos_panel(self, obj):
        """Lista de páginas hijas con link a editar; si son muchas, muestra link al listado filtrado."""
        if not obj or not obj.pk:
            return '(Guardá la página primero para ver sus hijos.)'

        hijos_qs = (
            Pagina.objects
            .filter(parent_legacy_id=obj.legacy_id)
            .exclude(tipo__in=TIPOS_P2_OCULTOS)
            .order_by('orden_menu', 'titulo')
        )
        total = hijos_qs.count()

        if total == 0:
            url = reverse('admin:core_pagina_add')
            return format_html(
                '<p style="margin: 0;">Esta página no tiene hijos. '
                '<a href="{}?parent_legacy_id={}" class="button">+ Agregar página hija</a></p>',
                url, obj.legacy_id,
            )

        listado_url = (
            reverse('admin:core_pagina_changelist')
            + f'?parent_legacy_id={obj.legacy_id}'
        )
        add_url = reverse('admin:core_pagina_add') + f'?parent_legacy_id={obj.legacy_id}'

        if total > 20:
            return format_html(
                '<p>Esta página tiene <strong>{}</strong> páginas hijas.</p>'
                '<p><a href="{}" class="button">Ver listado completo →</a> '
                '<a href="{}" class="button" style="margin-left: .5em;">+ Agregar hija</a></p>',
                total, listado_url, add_url,
            )

        rows = format_html_join(
            '',
            '<tr>'
            '<td style="padding: 4px 8px;"><a href="{}">{}</a></td>'
            '<td style="padding: 4px 8px; color: #777;"><small>{}</small></td>'
            '<td style="padding: 4px 8px; color: #999;"><small>{}</small></td>'
            '</tr>',
            (
                (
                    reverse('admin:core_pagina_change', args=[h.pk]),
                    h.titulo,
                    h.get_tipo_display(),
                    '✓' if h.activo else '—',
                )
                for h in hijos_qs[:50]
            ),
        )
        return format_html(
            '<table style="border-collapse: collapse; margin-bottom: .6rem;">'
            '<thead><tr style="background: #f5f7fa; color: #555;">'
            '<th style="text-align: left; padding: 6px 8px;">Título</th>'
            '<th style="text-align: left; padding: 6px 8px;">Tipo</th>'
            '<th style="text-align: left; padding: 6px 8px;">Activo</th>'
            '</tr></thead>'
            '<tbody>{}</tbody></table>'
            '<a href="{}" class="button">+ Agregar página hija</a>',
            rows, add_url,
        )
    hijos_panel.short_description = 'Páginas hijas'

    def subelementos_panel(self, obj):
        """Link al admin del subelemento (Archivo, Tarjeta, etc.) según el tipo."""
        if not obj or not obj.pk or not obj.tipo:
            return '(Guardá la página primero.)'

        spec = SUBELEMENTOS_POR_TIPO.get(obj.tipo)
        if not spec:
            return mark_safe('<em>Este tipo de página no tiene subelementos editables.</em>')

        app_label, model_name, filter_field, label = spec
        try:
            url = reverse(f'admin:{app_label}_{model_name}_changelist')
            url += f'?{filter_field}={obj.legacy_id}'
            add_url = reverse(f'admin:{app_label}_{model_name}_add')
        except Exception:
            return mark_safe(
                '<em style="color: #c33;">No se pudo resolver el admin del subelemento.</em>'
            )

        return format_html(
            '<p style="margin-bottom: .5rem;">Esta página tiene <strong>{}</strong> asociados.</p>'
            '<a href="{}" class="button">Ver / editar {}</a> '
            '<a href="{}" class="button" style="margin-left: .5em;">+ Agregar nuevo</a>',
            label, url, label.lower(), add_url,
        )
    subelementos_panel.short_description = 'Subelementos'

    # ------ Form behavior ------

    def get_prepopulated_fields(self, request, obj=None):
        # Solo pre-poblamos slug cuando es una página nueva.
        if obj is None:
            return {'slug': ('titulo',)}
        return {}

    def get_changeform_initial_data(self, request):
        """Pre-carga parent_legacy_id si viene en la query string (botón '+ Agregar hija')."""
        initial = super().get_changeform_initial_data(request)
        if 'parent_legacy_id' in request.GET:
            try:
                initial['parent_legacy_id'] = int(request.GET['parent_legacy_id'])
            except ValueError:
                pass
        return initial


# ===========================================================================
# Otros modelos de core (sin cambios mayores)
# ===========================================================================

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Identidad',       {'fields': ['titulo_sitio', 'logo', 'descripcion']}),
        ('Contacto',        {'fields': ['email_contacto', 'email_soporte', 'telefono', 'direccion']}),
        ('URLs del footer', {'fields': ['url_horarios', 'url_consultas']}),
        ('Redes sociales',  {'fields': ['url_facebook', 'url_instagram', 'url_youtube', 'url_twitter'],
                             'classes': ['collapse']}),
    ]
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display  = ['titulo', 'activo', 'orden', 'fecha_inicio', 'fecha_fin']
    list_filter   = ['activo']
    list_editable = ['activo', 'orden']
    search_fields = ['titulo']
    ordering      = ['orden', '-fecha_inicio']
    fields        = ['titulo', 'descripcion', 'imagen', 'url',
                     'activo', 'orden', 'fecha_inicio', 'fecha_fin']


@admin.register(CarouselItem)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display  = ['titulo', 'activo', 'orden']
    list_filter   = ['activo']
    list_editable = ['activo', 'orden']
    ordering      = ['orden']
    fields        = ['titulo', 'subtitulo', 'imagen', 'url', 'texto_boton', 'activo', 'orden']


@admin.register(EnlaceInteres)
class EnlaceInteresAdmin(admin.ModelAdmin):
    list_display  = ['titulo', 'url', 'activo', 'orden']
    list_filter   = ['activo']
    list_editable = ['activo', 'orden']
    ordering      = ['orden']
    fields        = ['titulo', 'descripcion', 'url', 'icono', 'activo', 'orden']


@admin.register(TemaEje)
class TemaEjeAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'eje', 'activo', 'orden']
    list_filter   = ['activo', 'eje']
    list_editable = ['activo', 'orden']
    search_fields = ['nombre']
    ordering      = ['eje', 'orden', 'nombre']
    fields        = ['nombre', 'eje', 'pagina', 'url_externa', 'orden', 'activo']
