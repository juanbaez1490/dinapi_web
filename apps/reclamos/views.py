from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static

from .forms import ReclamoForm
from .models import Reclamo


def reclamo_form_view(request):
    """Muestra y procesa el formulario de reclamos."""
    if request.method == 'POST':
        form = ReclamoForm(request.POST, request.FILES)
        if form.is_valid():
            reclamo = form.save()
            _enviar_confirmacion(request, reclamo)
            messages.success(
                request,
                'Su reclamo fue recibido correctamente. '
                'En breve recibira una confirmacion en {}.'.format(reclamo.email),
            )
            return redirect('reclamos:formulario')
    else:
        form = ReclamoForm()

    return render(request, 'reclamos/form.html', {'form': form})


def _enviar_confirmacion(request, reclamo):
    """Envia email de confirmacion al usuario y notificacion interna."""
    logo_url = request.build_absolute_uri(static('img/header/logo_nacional.png'))
    contexto_email = {'reclamo': reclamo, 'logo_url': logo_url}

    try:
        # Confirmacion al usuario
        send_mail(
            subject='DINAPI — Reclamo recibido: {}'.format(reclamo.get_tema_display()),
            message='Su reclamo fue registrado con el numero de referencia #{}.'.format(reclamo.pk),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reclamo.email],
            html_message=render_to_string('reclamos/email_confirmacion.html', contexto_email),
            fail_silently=True,
        )
        # Notificacion interna
        if settings.EMAIL_HOST_USER:
            send_mail(
                subject='[Reclamo] {} — {}'.format(reclamo.get_tema_display(), reclamo.nombre),
                message='Nuevo reclamo #{}. Ver en admin.'.format(reclamo.pk),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],
                html_message=render_to_string('reclamos/email_notificacion_interna.html', contexto_email),
                fail_silently=True,
            )
    except Exception as e:
        # No interrumpir el flujo si el email falla
        print('Error enviando email de reclamo #{}: {}'.format(reclamo.pk, e))
