from django import forms
from .models import MensajeContacto

class FormularioContacto(forms.ModelForm):
    """Formulario de contacto - Mapea desde ContactPage.php"""
    
    class Meta:
        model = MensajeContacto
        fields = ['nombre', 'apellido', 'email', 'tema', 'documento', 'telefono', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre*',
                'required': True,
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido*',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Correo electrónico*',
                'required': True,
            }),
            'tema': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nro. de Documento',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono',
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Mensaje*',
                'rows': 5,
                'required': True,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].label = 'Nombre'
        self.fields['apellido'].label = 'Apellido'
        self.fields['email'].label = 'Correo Electrónico'
        self.fields['tema'].label = 'Especifique su necesidad'
        self.fields['documento'].label = 'Nro. de Documento'
        self.fields['telefono'].label = 'Teléfono'
        self.fields['mensaje'].label = 'Mensaje'