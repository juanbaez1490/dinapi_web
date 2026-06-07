from django.db import models
from django.utils.text import slugify


class Concurso(models.Model):
    legacy_id = models.PositiveIntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    pagina_legacy_id = models.PositiveIntegerField(null=True, blank=True)

    fecha = models.DateField(null=True, blank=True)
    enlace = models.CharField(max_length=1000, blank=True)

    imagen_corta = models.ImageField(upload_to='concursos/miniaturas/', null=True, blank=True)
    imagen_completa = models.ImageField(upload_to='concursos/detalle/', null=True, blank=True)

    legacy_created = models.DateTimeField(null=True, blank=True)
    legacy_last_edited = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Concurso'
        verbose_name_plural = 'Concursos'
        ordering = ['-fecha', '-legacy_id']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo) or 'concurso'
            self.slug = f'{base_slug}-{self.legacy_id}' if self.legacy_id else base_slug
        super().save(*args, **kwargs)
