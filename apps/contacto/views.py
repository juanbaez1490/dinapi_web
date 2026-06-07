from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib import messages
from django.conf import settings
from django.templatetags.static import static
from .models import MensajeContacto
from .forms import FormularioContacto


def contact_form_view(request):
    """Vista para mostrar y procesar formulario de contacto"""
    if request.method == 'POST':
        form = FormularioContacto(request.POST)
        if form.is_valid():
            mensaje = form.save()

            logo_url = request.build_absolute_uri(static('img/header/logo_nacional.png'))

            try:
                subject = 'Mensaje desde el Sitio Web de DINAPI de: {} {}'.format(
                    mensaje.nombre, mensaje.apellido
                )
                html_message = render_to_string('contacto/email_mensaje.html', {
                    'mensaje': mensaje,
                    'logo_url': logo_url,
                })
                send_mail(
                    subject,
                    'Nuevo mensaje de contacto de {}'.format(mensaje.nombre),
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.EMAIL_HOST_USER],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Tu mensaje fue enviado correctamente!')
                return redirect('contacto:contact')
            except Exception as e:
                messages.warning(request, 'Tu mensaje fue guardado pero hubo un error al enviar el email!')
                print('Error enviando email: {}'.format(e))
                return redirect('contacto:contact')
    else:
        form = FormularioContacto()

    return render(request, 'contacto/formulario.html', {'form': form})
