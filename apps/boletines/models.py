from django.db import models
from django.utils.text import slugify


class PeriodoBoletin(models.Model):
    """Representa un PeriodoBoletinPage o PeriodoBoletinMarcaPage de SilverStripe."""

    class Tipo(models.TextChoices):
        GENERAL = 'general', 'General (Patentes / Diseño Industrial)'
        MARCA = 'marca', 'Marca'

    legacy_id = models.PositiveIntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    padre_legacy_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='ID del SiteTree padre (BoletinPage o BoletinMarcaPage)',
    )
    orden = models.PositiveIntegerField(default=0)
    legacy_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Periodo de Boletin'
        verbose_name_plural = 'Periodos de Boletines'
        ordering = ['-legacy_created', '-legacy_id']

    def __str__(self):
        return f'{self.titulo} ({self.get_tipo_display()})'


class Boletin(models.Model):
    """Entrada de boletin de SilverStripe unificada.

    Las cuatro tablas originales (BoletinGeneral, BoletinLogotiposMarcas,
    BoletinMarcasDocumentos, BoletinMovimientosAdministrativos) comparten
    el mismo esquema y se importan con un discriminador 'tipo'.
    """

    TIPO_GENERAL = 'general'
    TIPO_ACTO = 'acto_juridico'
    TIPO_LOGOTIPO = 'logotipo'
    TIPO_MARCA_DOC = 'marcas_documentos'
    TIPO_MOVIMIENTO = 'movimiento_admin'

    TIPO_CHOICES = [
        (TIPO_GENERAL, 'General (Patentes / Diseño Industrial)'),
        (TIPO_ACTO, 'Acto Juridico'),
        (TIPO_LOGOTIPO, 'Logotipo de Marca'),
        (TIPO_MARCA_DOC, 'Marcas y Documentos'),
        (TIPO_MOVIMIENTO, 'Movimiento Administrativo'),
    ]

    legacy_id = models.PositiveIntegerField()
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    periodo = models.ForeignKey(
        PeriodoBoletin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boletines',
    )
    titulo = models.CharField(max_length=255)
    fecha = models.DateField(null=True, blank=True)
    pdf = models.FileField(upload_to='boletines/pdf/', null=True, blank=True)
    imagen = models.ImageField(upload_to='boletines/imagenes/', null=True, blank=True)

    legacy_created = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Boletin'
        verbose_name_plural = 'Boletines'
        unique_together = [('legacy_id', 'tipo')]
        ordering = ['-fecha', '-legacy_id']

    def __str__(self):
        return f'{self.titulo} [{self.get_tipo_display()}]'
