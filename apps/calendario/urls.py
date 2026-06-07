from django.urls import path
from . import views

app_name = 'calendario'

urlpatterns = [
    path('', views.calendario_view, name='index'),
    path('actividades/', views.actividades_json, name='actividades_json'),
]
