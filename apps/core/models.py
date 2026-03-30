from django.db import models
from django.utils import timezone

class SiteConfig(models.Model):
    """Configuración global del sitio (similar a SiteConfig en Silverstripe)"""
    titulo_sitio = models.CharField(max_length=255, default='DINAPI')
    email_contacto = models.EmailField(default='contacto@dinapi.gov.py')
    email_soporte = models.EmailField(default='soporte@dinapi.gov.py')
    telefono = models.CharField(max_length=50, blank=True)
    direccion = models.CharField(max_length=500, blank=True)
    logo = models.ImageField(upload_to='configuracion/', null=True, blank=True)
    descripcion = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Configuración del Sitio'
        verbose_name_plural = 'Configuración del Sitio'
    
    def __str__(self):
        return self.titulo_sitio


class BasePage(models.Model):
    """Modelo base para todas las páginas (Similar a Page en Silverstripe)"""
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    contenido = models.TextField(blank=True)
    descripcion = models.CharField(max_length=500, blank=True, help_text='Para SEO')
    imagen_principal = models.ImageField(upload_to='paginas/', null=True, blank=True)
    
    # Campos de control
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.titulo