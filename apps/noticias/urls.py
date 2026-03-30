from django.urls import path
from . import views

app_name = 'noticias'

urlpatterns = [
    path('', views.NoticiaListView.as_view(), name='lista'),
    path('destacadas/', views.noticias_destacadas, name='destacadas'),
    path('buscar/', views.buscar_noticias, name='buscar'),
    path('<slug:slug>/', views.NoticiaDetailView.as_view(), name='detalle'),
]