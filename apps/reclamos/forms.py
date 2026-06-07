from django import forms
from django.core.exceptions import ValidationError

from .models import Reclamo


class ReclamoForm(forms.ModelForm):

    class Meta:
        model = Reclamo
        fields = ['nombre', 'email', 'telefono', 'expediente', 'tema', 'descripcion', 'adjunto']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'email':       forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            'expediente':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N. de expediente (si aplica)'}),
            'tema':        forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describa su reclamo con el mayor detalle posible...',
            }),
            'adjunto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }
        labels = {
            'nombre':      'Nombre completo *',
            'email':       'Correo electronico *',
            'telefono':    'Telefono',
            'expediente':  'N. de expediente',
            'tema':        'Tema del reclamo *',
            'descripcion': 'Descripcion *',
            'adjunto':     'Adjunto (PDF)',
        }
        help_texts = {
            'adjunto': 'Opcional. Solo archivos PDF. Maximo recomendado: 10 MB.',
        }

    def clean_adjunto(self):
        adjunto = self.cleaned_data.get('adjunto')
        if not adjunto:
            return adjunto

        # Validacion de extension
        nombre = getattr(adjunto, 'name', '') or ''
        if not nombre.lower().endswith('.pdf'):
            raise ValidationError('Solo se admiten archivos PDF (.pdf).')

        # Validacion de magic bytes (%PDF)
        try:
            header = adjunto.read(4)
            adjunto.seek(0)
            if header != b'%PDF':
                raise ValidationError('El archivo no es un PDF valido.')
        except ValidationError:
            raise
        except Exception:
            pass  # Si el archivo no es legible aun, pasa la validacion de form; el modelo lo captura

        # Limite de tamano: 10 MB
        if hasattr(adjunto, 'size') and adjunto.size > 10 * 1024 * 1024:
            raise ValidationError('El archivo supera el limite de 10 MB.')

        return adjunto
