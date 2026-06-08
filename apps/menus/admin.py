from django.contrib import admin
from .models import MenuDerecho, MenuPrincipal, Popup


@admin.register(MenuPrincipal)
class MenuPrincipalAdmin(admin.ModelAdmin):
	list_display = ('indent_titulo', 'padre', 'orden', 'pagina_destino_legacy_id',
	                'link_externo_corto', 'target_blank', 'activo')
	list_filter = ('activo', 'padre', 'target_blank')
	search_fields = ('titulo', 'link_externo', 'link_interno_url')
	list_editable = ('orden', 'activo')
	ordering = ('orden', 'id')
	fields = ('titulo', 'padre', 'orden', 'pagina_destino_legacy_id',
	          'link_interno_url', 'link_externo', 'target_blank', 'activo')

	def indent_titulo(self, obj):
		return f'    └ {obj.titulo}' if obj.padre_id else obj.titulo
	indent_titulo.short_description = 'Titulo'

	def link_externo_corto(self, obj):
		if not obj.link_externo:
			return ''
		return obj.link_externo[:50] + ('...' if len(obj.link_externo) > 50 else '')
	link_externo_corto.short_description = 'Link externo'


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
