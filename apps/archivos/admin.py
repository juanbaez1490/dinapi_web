from django.contrib import admin
from .models import Archivo


@admin.register(Archivo)
class ArchivoAdmin(admin.ModelAdmin):
    list_display = ['titulo_corto', 'pagina_legacy_id', 'tiene_pdf', 'es_externo', 'fecha_ordenamiento']
    list_filter = ['pagina_legacy_id']
    search_fields = ['titulo', 'link_externo']
    readonly_fields = ['legacy_id', 'pdf_legacy_path', 'legacy_created']
    fields = ['titulo', 'pagina_legacy_id', 'pdf', 'link_externo', 'fecha_ordenamiento',
              'legacy_id', 'pdf_legacy_path', 'legacy_created']

    def titulo_corto(self, obj):
        return obj.titulo[:80] + ('...' if len(obj.titulo) > 80 else '')
    titulo_corto.short_description = 'Titulo'

    def tiene_pdf(self, obj):
        return bool(obj.pdf)
    tiene_pdf.boolean = True
    tiene_pdf.short_description = 'PDF'
