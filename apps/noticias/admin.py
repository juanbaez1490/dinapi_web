from django.contrib import admin
from .models import CategoriaNoticia, Noticia, RevistaPage

@admin.register(CategoriaNoticia)
class CategoriaNoticdaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug')
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ('nombre',)

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'fecha', 'destacado', 'activo')
    list_filter = ('categoria', 'destacado', 'activo', 'fecha')
    search_fields = ('titulo', 'contenido')
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'slug', 'categoria', 'fecha')
        }),
        ('Contenido', {
            'fields': ('contenido', 'imagen')
        }),
        ('Opciones', {
            'fields': ('destacado', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RevistaPage)
class RevistaPageAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'activo')
    list_filter = ('activo',)
    prepopulated_fields = {'slug': ('titulo',)}