from django.contrib import admin
from .models import MensajeContacto

@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'email', 'tema', 'fecha_creacion', 'leido', 'respondido')
    list_filter = ('tema', 'leido', 'respondido', 'fecha_creacion')
    search_fields = ('nombre', 'apellido', 'email', 'mensaje')
    readonly_fields = ('fecha_creacion',)
    
    fieldsets = (
        ('Información del Contacto', {
            'fields': ('nombre', 'apellido', 'email', 'documento', 'telefono')
        }),
        ('Mensaje', {
            'fields': ('tema', 'mensaje')
        }),
        ('Estado', {
            'fields': ('leido', 'respondido')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_como_leido', 'marcar_como_respondido']
    
    def marcar_como_leido(self, request, queryset):
        queryset.update(leido=True)
    marcar_como_leido.short_description = "Marcar como leído"
    
    def marcar_como_respondido(self, request, queryset):
        queryset.update(respondido=True)
    marcar_como_respondido.short_description = "Marcar como respondido"