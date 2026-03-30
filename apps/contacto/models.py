from django.db import models
from django.utils import timezone

class MensajeContacto(models.Model):
    """Modelo para guardar mensajes de contacto - Mapea desde MensajeContacto.php"""
    
    TEMAS_CHOICES = [
        ('Consulta', 'Consulta'),
        ('Reclamo', 'Reclamo'),
        ('Sugerencia', 'Sugerencia'),
    ]
    
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    email = models.EmailField()
    tema = models.CharField(max_length=50, choices=TEMAS_CHOICES)
    documento = models.CharField(max_length=50, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    mensaje = models.TextField()
    
    # Campos de control
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    respondido = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Mensaje de Contacto'
        verbose_name_plural = 'Mensajes de Contacto'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['-fecha_creacion']),
            models.Index(fields=['leido']),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.tema} ({self.fecha_creacion.strftime('%d/%m/%Y')})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"