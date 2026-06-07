from django.contrib import admin
from .models import (
    CategoriaBiblioteca,
    EtiquetaBiblioteca,
    VideoBiblioteca,
    ImagenBiblioteca,
    DocumentoBiblioteca,
    Biblioteca,
)


@admin.register(CategoriaBiblioteca)
class CategoriaBibliotecaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'color')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(EtiquetaBiblioteca)
class EtiquetaBibliotecaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(VideoBiblioteca)
class VideoBibliotecaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'url', 'orden')
    search_fields = ('titulo',)
    ordering = ('orden', 'titulo')


@admin.register(ImagenBiblioteca)
class ImagenBibliotecaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'orden')
    search_fields = ('titulo',)
    ordering = ('orden', 'titulo')


@admin.register(DocumentoBiblioteca)
class DocumentoBibliotecaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'orden')
    search_fields = ('titulo',)
    ordering = ('orden', 'titulo')


class VideoInline(admin.TabularInline):
    model = Biblioteca.videos.through
    extra = 0
    verbose_name = 'Video'
    verbose_name_plural = 'Videos'


class ImagenInline(admin.TabularInline):
    model = Biblioteca.imagenes.through
    extra = 0
    verbose_name = 'Imagen'
    verbose_name_plural = 'Imagenes'


class DocumentoInline(admin.TabularInline):
    model = Biblioteca.documentos.through
    extra = 0
    verbose_name = 'Documento'
    verbose_name_plural = 'Documentos'


@admin.register(Biblioteca)
class BibliotecaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'fecha_ordenamiento', 'ocultar', 'n_videos', 'n_documentos')
    list_filter = ('categoria', 'ocultar', 'etiquetas')
    search_fields = ('titulo', 'descripcion', 'enlaces_referencias')
    prepopulated_fields = {'slug': ('titulo',)}
    filter_horizontal = ('etiquetas',)
    inlines = [VideoInline, ImagenInline, DocumentoInline]
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    fieldsets = (
        ('Contenido', {
            'fields': ('titulo', 'slug', 'categoria', 'descripcion', 'imagen_principal'),
        }),
        ('Descripciones de secciones', {
            'fields': ('descripcion_videos', 'descripcion_imagenes', 'descripcion_documentos', 'enlaces_referencias'),
            'classes': ('collapse',),
        }),
        ('Etiquetas', {
            'fields': ('etiquetas',),
        }),
        ('Control', {
            'fields': ('fecha_ordenamiento', 'ocultar'),
        }),
        ('Auditoria', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Videos')
    def n_videos(self, obj):
        return obj.videos.count()

    @admin.display(description='Documentos')
    def n_documentos(self, obj):
        return obj.documentos.count()
