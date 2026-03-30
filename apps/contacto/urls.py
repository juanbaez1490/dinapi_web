from django.urls import path
from . import views

app_name = 'contacto'

urlpatterns = [
    path('', views.contact_form_view, name='contact'),
]