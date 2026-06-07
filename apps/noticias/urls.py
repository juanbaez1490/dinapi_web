from django.urls import path
from . import views

app_name = 'noticias'

urlpatterns = [
    path('', views.NoticiaListView.as_view(), name='lista'),
    path('destacadas/', views.noticias_destacadas, name='destacadas'),
    path('buscar/', views.buscar_noticias, name='buscar'),
    path('revista/<slug:slug>/', views.RevistaDetailView.as_view(), name='revista_detalle'),
    path('<slug:slug>/', views.NoticiaDetailView.as_view(), name='detalle'),
]