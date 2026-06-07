from django.contrib import admin

from .models import PeriodoBoletin, Boletin


class BoletinInline(admin.TabularInline):
    model = Boletin
    extra = 0
    fields = ('tipo', 'titulo', 'fecha', 'pdf', 'imagen')
    ordering = ('-fecha',)


@admin.register(PeriodoBoletin)
class PeriodoBoletinAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'legacy_id', 'padre_legacy_id', 'orden')
    list_filter = ('tipo',)
    search_fields = ('titulo',)
    ordering = ('-legacy_created',)
    inlines = [BoletinInline]


@admin.register(Boletin)
class BoletinAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'periodo', 'fecha', 'legacy_id')
    list_filter = ('tipo', 'periodo')
    search_fields = ('titulo',)
    ordering = ('-fecha',)
