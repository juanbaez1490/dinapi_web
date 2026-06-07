from django.contrib import admin
from .models import Actividad


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_inicio', 'fecha_fin', 'lugar', 'activo')
    list_filter = ('activo',)
    search_fields = ('titulo', 'descripcion', 'lugar')
    date_hierarchy = 'fecha_inicio'
    list_editable = ('activo',)
    ordering = ('-fecha_inicio',)
    fieldsets = (
        ('Contenido', {
            'fields': ('titulo', 'descripcion', 'lugar'),
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin'),
        }),
        ('Control', {
            'fields': ('activo',),
        }),
        ('Migración', {
            'fields': ('legacy_id',),
            'classes': ('collapse',),
        }),
    )
