from django.db import models
from django.utils.html import strip_tags
from django.utils.text import slugify


class CategoriaBiblioteca(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    color = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Categoria de Biblioteca'
        verbose_name_plural = 'Categorias de Biblioteca'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class EtiquetaBiblioteca(models.Model):
    """Etiquetas/tags para clasificacion transversal de recursos."""
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Etiqueta'
        verbose_name_plural = 'Etiquetas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:100]
        super().save(*args, **kwargs)


class VideoBiblioteca(models.Model):
    """Video embebido (YouTube, Vimeo u otro) asociado a un recurso de biblioteca."""
    titulo = models.CharField(max_length=255)
    url = models.URLField(max_length=500, help_text='URL de embed o enlace directo al video.')
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'
        ordering = ['orden', 'titulo']

    def __str__(self):
        return self.titulo


class ImagenBiblioteca(models.Model):
    """Imagen asociada a un recurso de biblioteca."""
    titulo = models.CharField(max_length=255, blank=True)
    imagen = models.ImageField(
        upload_to='biblioteca/imagenes/%Y/%m/',
        null=True, blank=True,
    )
    url = models.URLField(max_length=500, blank=True, help_text='URL externa si la imagen no esta subida.')
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Imagen'
        verbose_name_plural = 'Imagenes'
        ordering = ['orden', 'titulo']

    def __str__(self):
        return self.titulo or 'Imagen #{}'.format(self.pk)

    def get_url(self):
        if self.imagen:
            return self.imagen.url
        return self.url or ''


class DocumentoBiblioteca(models.Model):
    """Documento (PDF, Word, etc.) asociado a un recurso de biblioteca."""
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(
        upload_to='biblioteca/documentos/%Y/%m/',
        null=True, blank=True,
    )
    url = models.URLField(max_length=500, blank=True, help_text='URL externa si el archivo no esta subido.')
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)
    legacy_id = models.PositiveIntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['orden', 'titulo']

    def __str__(self):
        return self.titulo

    def get_url(self):
        if self.archivo:
            return self.archivo.url
        return self.url or ''


class Biblioteca(models.Model):
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    categoria = models.ForeignKey(
        CategoriaBiblioteca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
    )

    descripcion = models.TextField(blank=True)
    descripcion_videos = models.CharField(max_length=500, blank=True)
    descripcion_imagenes = models.CharField(max_length=500, blank=True)
    descripcion_documentos = models.CharField(max_length=500, blank=True)
    enlaces_referencias = models.TextField(blank=True)
    imagen_principal = models.ImageField(
        upload_to='biblioteca/imagenes-principales/', null=True, blank=True,
    )

    # Relaciones M2M con recursos multimedia y etiquetas
    videos = models.ManyToManyField(
        VideoBiblioteca, blank=True, related_name='bibliotecas',
        verbose_name='Videos',
    )
    imagenes = models.ManyToManyField(
        ImagenBiblioteca, blank=True, related_name='bibliotecas',
        verbose_name='Imagenes',
    )
    documentos = models.ManyToManyField(
        DocumentoBiblioteca, blank=True, related_name='bibliotecas',
        verbose_name='Documentos',
    )
    etiquetas = models.ManyToManyField(
        EtiquetaBiblioteca, blank=True, related_name='bibliotecas',
        verbose_name='Etiquetas',
    )

    fecha_ordenamiento = models.DateField(null=True, blank=True)
    ocultar = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Biblioteca'
        verbose_name_plural = 'Biblioteca'
        ordering = ['-fecha_ordenamiento', '-fecha_creacion']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)[:240]
        super().save(*args, **kwargs)

    def get_epigrafe(self, caracteres=220):
        return strip_tags(self.descripcion or '')[:caracteres]
