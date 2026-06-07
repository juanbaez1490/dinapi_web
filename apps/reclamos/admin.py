from django.contrib import admin
from .models import Reclamo


@admin.register(Reclamo)
class ReclamoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'tema', 'estado', 'fecha_envio', 'tiene_adjunto')
    list_filter = ('estado', 'tema')
    search_fields = ('nombre', 'email', 'expediente', 'descripcion')
    readonly_fields = ('fecha_envio', 'legacy_id')
    ordering = ('-fecha_envio',)
    date_hierarchy = 'fecha_envio'

    fieldsets = (
        ('Reclamante', {
            'fields': ('nombre', 'email', 'telefono', 'expediente'),
        }),
        ('Reclamo', {
            'fields': ('tema', 'descripcion', 'adjunto'),
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_envio'),
        }),
        ('Migracion legacy', {
            'fields': ('legacy_id',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(boolean=True, description='Tiene adjunto')
    def tiene_adjunto(self, obj):
        return bool(obj.adjunto)
