from django.contrib import admin
from .models import TarjetaPage, Tarjeta, AcordeonPage, AcordeonItem


class TarjetaInline(admin.TabularInline):
	model = Tarjeta
	extra = 0
	fields = ('titulo', 'fecha', 'link_externo', 'link_interno', 'link_interno_url', 'imagen')


@admin.register(TarjetaPage)
class TarjetaPageAdmin(admin.ModelAdmin):
	list_display = ('legacy_id', 'titulo')
	search_fields = ('titulo',)
	inlines = [TarjetaInline]


@admin.register(Tarjeta)
class TarjetaAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'pagina', 'fecha', 'legacy_id')
	search_fields = ('titulo', 'subtitulo')
	list_filter = ('fecha',)


class AcordeonItemInline(admin.TabularInline):
	model = AcordeonItem
	extra = 0
	fields = ('titulo', 'fecha_ordenamiento', 'titulo_adjunto', 'adjunto')


@admin.register(AcordeonPage)
class AcordeonPageAdmin(admin.ModelAdmin):
	list_display = ('legacy_id', 'titulo_padre', 'titulo_anexo')
	search_fields = ('titulo_padre',)
	inlines = [AcordeonItemInline]


@admin.register(AcordeonItem)
class AcordeonItemAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'pagina', 'fecha_ordenamiento', 'legacy_id')
	search_fields = ('titulo', 'titulo_adjunto')
	list_filter = ('fecha_ordenamiento',)
