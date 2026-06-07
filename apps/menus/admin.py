from django.contrib import admin
from .models import MenuDerecho, Popup


@admin.register(MenuDerecho)
class MenuDerechoAdmin(admin.ModelAdmin):
	list_display = (
		'titulo',
		'url_resuelta',
		'destacado',
		'padre',
		'hijo',
		'fecha_ordenamiento',
	)
	list_filter = ('destacado', 'padre', 'hijo')
	search_fields = ('titulo', 'link_externo', 'link_interno_url')
	ordering = ('-fecha_ordenamiento', '-creado_en')


@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'activo', 'actualizado_en')
	list_filter = ('activo',)
	search_fields = ('titulo', 'descripcion', 'url_video')
	ordering = ('-actualizado_en',)
