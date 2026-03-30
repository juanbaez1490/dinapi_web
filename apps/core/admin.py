from django.contrib import admin
from .models import SiteConfig

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('titulo_sitio', 'email_contacto')
    fieldsets = (
        ('Información General', {
            'fields': ('titulo_sitio', 'descripcion', 'logo')
        }),
        ('Contacto', {
            'fields': ('email_contacto', 'email_soporte', 'telefono', 'direccion')
        }),
    )