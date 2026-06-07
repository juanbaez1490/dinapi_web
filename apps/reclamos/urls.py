from django.urls import path
from . import views

app_name = 'reclamos'

urlpatterns = [
    path('', views.reclamo_form_view, name='formulario'),
]
