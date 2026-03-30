from django.shortcuts import render, redirect
from django.views.generic import CreateView, ListView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib import messages
from django.conf import settings
from .models import MensajeContacto
from .forms import FormularioContacto

def contact_form_view(request):
    """Vista para mostrar y procesar formulario de contacto"""
    if request.method == 'POST':
        form = FormularioContacto(request.POST)
        if form.is_valid():
            mensaje = form.save()
            
            # Enviar email de confirmación
            try:
                subject = f"Mensaje desde el Sitio Web de DINAPI de: {mensaje.nombre} {mensaje.apellido}"
                html_message = render_to_string('contacto/email_mensaje.html', {
                    'mensaje': mensaje,
                    'logo_url': 'https://www.dinapi.gov.py/portal/v3/themes/dinapi/img/logo.png',
                })
                
                send_mail(
                    subject,
                    f"Nuevo mensaje de contacto de {mensaje.nombre}",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.EMAIL_HOST_USER],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                messages.success(request, '¡Tu mensaje fue enviado correctamente!')
                return redirect('contacto:contact')
            except Exception as e:
                messages.warning(request, '¡Tu mensaje fue guardado pero hubo un error al enviar el email!')
                print(f"Error enviando email: {e}")
                return redirect('contacto:contact')
    else:
        form = FormularioContacto()
    
    context = {
        'form': form,
    }
    return render(request, 'contacto/formulario.html', context)