"""
Archivos institucionales — PDFs y links de paginas tipo ArchivoPage y
ArchivoDesplegablePage del legacy SilverStripe.

En el legacy:
  - `Archivo`               : items (titulo, pdf, link externo, fecha)
  - `ArchivoPage`           : pagina que lista Archivos
  - `ArchivoDesplegablePage`: pagina que agrupa varias ArchivoPage como secciones

En Django mantenemos solo `Archivo` con FK a `core.Pagina`; el tipo de pagina
(ArchivoPage vs ArchivoDesplegablePage) lo trae la propia Pagina via `tipo`,
y la jerarquia de subpaginas via `parent_legacy_id`.
"""
from django.db import models


class Archivo(models.Model):
    """
    Item individual (PDF o link externo) que pertenece a una `Pagina` tipo
    ArchivoPage o ArchivoDesplegablePage.
    """
    legacy_id = models.PositiveIntegerField(unique=True)
    pagina_legacy_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True,
        help_text='ID legacy de la Pagina contenedora (mapea a core.Pagina.legacy_id).',
    )
    titulo = models.TextField()
    link_externo = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Si el archivo es un link externo en lugar de un PDF subido.',
    )
    pdf = models.FileField(
        upload_to='archivos/%Y/', null=True, blank=True,
        help_text='PDF subido. Vacio si es un link externo o si solo se conoce metadata.',
    )
    pdf_legacy_path = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Ruta original del PDF en el assets/ legacy. Util para auditoria.',
    )
    fecha_ordenamiento = models.DateField(null=True, blank=True)
    legacy_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Archivo institucional'
        verbose_name_plural = 'Archivos institucionales'
        ordering = ['-fecha_ordenamiento', '-legacy_id']
        indexes = [
            models.Index(fields=['pagina_legacy_id']),
        ]

    def __str__(self):
        return self.titulo[:100]

    @property
    def enlace_resuelto(self):
        """URL final: prioriza el PDF subido, luego link externo."""
        if self.pdf:
            return self.pdf.url
        if self.link_externo:
            return self.link_externo
        return ''

    @property
    def es_externo(self):
        return not self.pdf and bool(self.link_externo)
