from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('noticias/', include('apps.noticias.urls')),
    path('contacto/', include('apps.contacto.urls')),
    path('reclamos/', include('apps.reclamos.urls')),
    path('calendario/', include('apps.calendario.urls')),
    path('biblioteca/', include('apps.biblioteca.urls')),
    path('concursos/', include('apps.concursos.urls')),
    path('boletines/', include('apps.boletines.urls')),
    path('tarjetas/', include('apps.tarjetas.urls')),
    path('menus/', include('apps.menus.urls')),
    path('', include('apps.core.urls')),
]

# Servir archivos estaticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
