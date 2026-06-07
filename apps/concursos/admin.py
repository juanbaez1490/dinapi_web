from django.contrib import admin

from .models import Concurso


@admin.register(Concurso)
class ConcursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'legacy_id', 'pagina_legacy_id')
    list_filter = ('fecha',)
    search_fields = ('titulo', 'legacy_id')
    ordering = ('-fecha', '-legacy_id')
