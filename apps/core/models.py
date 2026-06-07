from django.db import models
from django.utils import timezone


class SiteConfig(models.Model):
    """Configuracion global del sitio (similar a SiteConfig en Silverstripe)"""
    titulo_sitio = models.CharField(max_length=255, default='DINAPI')
    email_contacto = models.EmailField(default='contacto@dinapi.gov.py')
    email_soporte = models.EmailField(default='soporte@dinapi.gov.py')
    telefono = models.CharField(max_length=50, blank=True)
    direccion = models.CharField(max_length=500, blank=True)
    logo = models.ImageField(upload_to='configuracion/', null=True, blank=True)
    descripcion = models.TextField(blank=True)

    # URLs configurables del footer
    url_horarios = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL de la pagina de horarios de atencion (interna o externa).',
    )
    url_consultas = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL del formulario de consultas/reclamos. Vacio = vista interna.',
    )

    # Redes sociales
    url_facebook  = models.URLField(max_length=300, blank=True, default='', verbose_name='Facebook')
    url_instagram = models.URLField(max_length=300, blank=True, default='', verbose_name='Instagram')
    url_youtube   = models.URLField(max_length=300, blank=True, default='', verbose_name='YouTube')
    url_twitter   = models.URLField(max_length=300, blank=True, default='', verbose_name='X / Twitter')

    class Meta:
        verbose_name = 'Configuracion del Sitio'
        verbose_name_plural = 'Configuracion del Sitio'

    def __str__(self):
        return self.titulo_sitio


class BasePage(models.Model):
    """Modelo base para todas las paginas"""
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    contenido = models.TextField(blank=True)
    descripcion = models.CharField(max_length=500, blank=True, help_text='Para SEO')
    imagen_principal = models.ImageField(upload_to='paginas/', null=True, blank=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo


class Pagina(BasePage):
    """Representa tipos de paginas de SilverStripe usando un solo modelo."""

    class TipoPagina(models.TextChoices):
        PAGE = 'Page', 'Pagina'
        HOME = 'HomePage', 'Home'
        GENERAL = 'GeneralPage', 'General'
        INSTITUCIONAL = 'InstitucionalPage', 'Institucional'
        CONTACTO = 'ContactPage', 'Contacto'
        NOTICIAS = 'NoticiaPage', 'Noticias'
        REVISTA = 'RevistaPage', 'Revista'
        BIBLIOTECA = 'BibliotecaPage', 'Biblioteca'
        CONCURSOS = 'ConcursosPage', 'Concursos'
        RECLAMOS = 'ReclamosPage', 'Reclamos'
        ARCHIVOS = 'ArchivoPage', 'Archivos'
        ACORDEON = 'AcordeonPage', 'Acordeon'
        TARJETAS = 'TarjetaPage', 'Tarjetas'
        TARJETAS_SIMPLES = 'TarjetaSimplePage', 'Tarjetas Simples'
        CALENDARIO = 'CalendarioPage', 'Calendario'
        BOLETIN = 'BoletinPage', 'Boletin'
        BOLETIN_MARCA = 'BoletinMarcaPage', 'Boletin Marca'
        PERIODO_BOLETIN = 'PeriodoBoletinPage', 'Periodo Boletin'
        PERIODO_BOLETIN_MARCA = 'PeriodoBoletinMarcaPage', 'Periodo Boletin Marca'
        PERIODO_BOLETIN_MARCA_GENERICO = 'PeriodoBoletinMarcaGenericoPage', 'Periodo Boletin Marca Generico'
        PROTEGE_LO_TUYO = 'ProtegeLoTuyoPage', 'Protege lo Tuyo'
        DIA_PI = 'DiaPIPage', 'Dia PI'
        CODEPI = 'CodepiNoticiaPage', 'Codepi Noticias'
        GESTOR_ENLACES = 'GestorEnlacesPage', 'Gestor de Enlaces'
        ARCHIVO_DESPLEGABLE = 'ArchivoDesplegablePage', 'Archivo Desplegable'
        CONCURSO_JUVENTUD = 'ConcursoJuventudPage', 'Concurso Juventud'

    tipo = models.CharField(max_length=80, choices=TipoPagina.choices, default=TipoPagina.GENERAL)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    parent_legacy_id = models.PositiveIntegerField(null=True, blank=True)
    subtitulo = models.CharField(max_length=255, blank=True)
    mostrar_en_menu = models.BooleanField(default=True)
    orden_menu = models.PositiveIntegerField(default=0)
    plantilla_personalizada = models.CharField(
        max_length=255,
        blank=True,
        help_text='Ruta de plantilla opcional, por ejemplo: core/home.html'
    )

    class Meta:
        verbose_name = 'Pagina'
        verbose_name_plural = 'Paginas'
        ordering = ['orden_menu', 'titulo']


class TemaEje(models.Model):
    """
    Ejes tematicos del home (Propiedad Industrial, Derecho de Autor, Observancia).
    Cada fila es un item dentro de un eje; el campo `eje` agrupa los items.
    Mapea desde la tabla TemaEje de SilverStripe (12 filas).
    """

    class EjeChoices(models.IntegerChoices):
        PROPIEDAD_INDUSTRIAL = 1, 'Propiedad Industrial'
        DERECHO_AUTOR = 2, 'Derecho de Autor y Derechos Conexos'
        OBSERVANCIA = 3, 'Observancia'

    nombre = models.CharField(max_length=255)
    eje = models.PositiveSmallIntegerField(choices=EjeChoices.choices)
    pagina = models.ForeignKey(
        Pagina,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='temas_eje',
        help_text='Pagina interna a la que apunta este item.',
    )
    url_externa = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL externa de respaldo si no hay pagina interna asignada.',
    )
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tema Eje'
        verbose_name_plural = 'Temas Eje'
        ordering = ['eje', 'orden', 'nombre']

    def __str__(self):
        return '[Eje {}] {}'.format(self.eje, self.nombre)

    def get_url(self, resolve_fn=None):
        """Devuelve la URL resuelta: interna si hay pagina, externa si no."""
        if self.pagina:
            if resolve_fn:
                return resolve_fn(self.pagina)
            try:
                from django.urls import reverse
                return reverse('core:pagina_detalle', kwargs={'slug': self.pagina.slug})
            except Exception:
                pass
        if self.url_externa:
            return self.url_externa
        return '#'


class CarouselItem(models.Model):
    """
    Slide del carousel principal del home.
    Mapea desde la tabla HomeSlide / Slide / CarouselItem del legacy.
    """
    titulo = models.CharField(max_length=255, verbose_name='Título')
    subtitulo = models.CharField(max_length=500, blank=True, verbose_name='Subtítulo')
    imagen = models.ImageField(
        upload_to='home/carousel/%Y/%m/',
        null=True, blank=True,
        verbose_name='Imagen de fondo',
    )
    url = models.URLField(max_length=500, blank=True, verbose_name='URL del botón CTA')
    texto_boton = models.CharField(max_length=100, blank=True, default='Ver más', verbose_name='Texto del botón')
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Slide del Carousel'
        verbose_name_plural = 'Carousel (slides)'
        ordering = ['orden', 'id']

    def __str__(self):
        return self.titulo


class Anuncio(models.Model):
    """
    Anuncio o banner institucional para el home / secciones internas.
    Permite activación/desactivación por fecha.
    """
    titulo = models.CharField(max_length=255, verbose_name='Título')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    imagen = models.ImageField(
        upload_to='home/anuncios/%Y/%m/',
        null=True, blank=True,
        verbose_name='Imagen',
    )
    url = models.URLField(max_length=500, blank=True, verbose_name='URL (CTA)')
    fecha_inicio = models.DateField(
        null=True, blank=True,
        verbose_name='Visible desde',
        help_text='Dejar vacío = siempre visible.',
    )
    fecha_fin = models.DateField(
        null=True, blank=True,
        verbose_name='Visible hasta',
        help_text='Dejar vacío = sin vencimiento.',
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Anuncio'
        verbose_name_plural = 'Anuncios'
        ordering = ['orden', '-fecha_inicio', 'id']

    def __str__(self):
        return self.titulo


class EnlaceInteres(models.Model):
    """
    Enlace de interés / acceso rápido del home.
    Mapea desde EnlaceInteres / QuickLink del legacy.
    """
    titulo = models.CharField(max_length=255, verbose_name='Título')
    descripcion = models.CharField(max_length=500, blank=True, verbose_name='Descripción corta')
    url = models.URLField(max_length=500, verbose_name='URL')
    icono = models.CharField(
        max_length=100, blank=True,
        verbose_name='Clase de ícono',
        help_text='Clase CSS Bootstrap Icons, p. ej. bi-shield-check',
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Enlace de Interés'
        verbose_name_plural = 'Enlaces de Interés'
        ordering = ['orden', 'id']

    def __str__(self):
        return self.titulo
