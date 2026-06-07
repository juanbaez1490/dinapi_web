from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('<slug:slug>/', views.pagina_detalle_view, name='pagina_detalle'),
]
