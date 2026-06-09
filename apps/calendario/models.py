from django.db import models
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


class Actividad(models.Model):
    """
    Actividad o evento del calendario institucional.
    No hay tabla intermedia Calendario: todas las actividades son globales
    y se filtran por mes/año en la vista.
    """
    titulo = models.CharField(max_length=255, verbose_name='Título')
    descripcion = CKEditor5Field(blank=True, verbose_name='Descripción', config_name='default')
    fecha_inicio = models.DateTimeField(verbose_name='Fecha y hora de inicio')
    fecha_fin = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de fin')
    lugar = models.CharField(max_length=255, blank=True, verbose_name='Lugar')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['fecha_inicio']
        indexes = [
            models.Index(fields=['fecha_inicio']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return '{} — {}'.format(
            self.fecha_inicio.strftime('%d/%m/%Y'),
            self.titulo,
        )
