from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags

class CategoriaNoticia(models.Model):
    """Categoría de noticias"""
    nombre = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Categoría de Noticia'
        verbose_name_plural = 'Categorías de Noticias'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Noticia(models.Model):
    """Modelo de Noticia - Mapea desde Noticia.php de Silverstripe"""
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    categoria = models.ForeignKey(CategoriaNoticia, on_delete=models.PROTECT, related_name='noticias')
    fecha = models.DateField(default=timezone.now)
    contenido = models.TextField(help_text='Contenido HTML de la noticia')
    imagen = models.ImageField(upload_to='noticias/imagenes-noticias/', null=True, blank=True)
    
    # Campos de control
    destacado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        ordering = ['-fecha', '-fecha_creacion']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['-destacado']),
        ]
    
    def __str__(self):
        return self.titulo
    
    def get_epigrafe(self, caracteres=330):
        """Extrae un resumen de hasta N caracteres sin HTML"""
        return strip_tags(self.contenido)[:caracteres]
    
    @classmethod
    def noticias_destacadas(cls):
        """Retorna noticias destacadas (como en Silverstripe)"""
        return cls.objects.filter(destacado=True, activo=True).order_by('-fecha')


class RevistaPage(models.Model):
    """Página/sección de revista (para gestionar revistas)"""
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='revistas/', null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Revista'
        verbose_name_plural = 'Revistas'
    
    def __str__(self):
        return self.titulo