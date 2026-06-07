from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def _validar_pdf(archivo):
    """Valida que el archivo adjunto sea un PDF."""
    if archivo:
        nombre = archivo.name.lower()
        if not nombre.endswith('.pdf'):
            raise ValidationError('Solo se admiten archivos PDF (.pdf).')
        # Verificar magic bytes: los PDF empiezan con %PDF
        try:
            header = archivo.read(4)
            archivo.seek(0)
            if header != b'%PDF':
                raise ValidationError('El archivo no es un PDF valido.')
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            # Si no se puede leer (e.g. ya cerrado), solo verificar extension
            pass


class Reclamo(models.Model):

    class Tema(models.TextChoices):
        MARCAS              = 'marcas',              'Marcas'
        PATENTES            = 'patentes',            'Patentes'
        DIBUJOS_MODELOS     = 'dibujos_modelos',     'Dibujos y Modelos Industriales'
        DERECHO_AUTOR       = 'derecho_autor',       'Derecho de Autor y Derechos Conexos'
        OBSERVANCIA         = 'observancia',         'Observancia'
        IGDO                = 'igdo',                'Indicaciones Geograficas y Denominaciones de Origen'
        CONOCIMIENTOS_TRAD  = 'conocimientos_trad',  'Conocimientos Tradicionales'
        GESTIONES_ADMIN     = 'gestiones_admin',     'Gestiones Administrativas'
        MEDIACION           = 'mediacion',           'Mediacion y Conciliacion'
        OTRO                = 'otro',                'Otro'

    class Estado(models.TextChoices):
        RECIBIDO   = 'recibido',   'Recibido'
        EN_PROCESO = 'en_proceso', 'En proceso'
        RESUELTO   = 'resuelto',   'Resuelto'
        CERRADO    = 'cerrado',    'Cerrado'

    # Datos del reclamante
    nombre      = models.CharField(max_length=255, verbose_name='Nombre completo')
    email       = models.EmailField(verbose_name='Correo electronico')
    telefono    = models.CharField(max_length=50, blank=True, verbose_name='Telefono')
    expediente  = models.CharField(max_length=255, blank=True, verbose_name='N. de expediente')

    # Contenido del reclamo
    tema        = models.CharField(max_length=50, choices=Tema.choices, verbose_name='Tema')
    descripcion = models.TextField(verbose_name='Descripcion del reclamo')
    adjunto     = models.FileField(
        upload_to='reclamos/adjuntos/%Y/%m/',
        null=True,
        blank=True,
        validators=[_validar_pdf],
        verbose_name='Adjunto (PDF)',
        help_text='Solo archivos PDF. Maximo recomendado: 10 MB.',
    )

    # Control
    fecha_envio = models.DateTimeField(default=timezone.now, verbose_name='Fecha de envio')
    estado      = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.RECIBIDO,
        verbose_name='Estado',
    )
    legacy_id   = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Reclamo'
        verbose_name_plural = 'Reclamos'
        ordering = ['-fecha_envio']
        indexes = [
            models.Index(fields=['-fecha_envio']),
            models.Index(fields=['estado']),
            models.Index(fields=['tema']),
        ]

    def __str__(self):
        return '[{}] {} — {} ({})'.format(
            self.get_estado_display(),
            self.nombre,
            self.get_tema_display(),
            self.fecha_envio.strftime('%d/%m/%Y'),
        )
