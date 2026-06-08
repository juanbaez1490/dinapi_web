from django.urls import path

from . import views

app_name = 'boletines'

urlpatterns = [
    path('', views.BoletinIndexView.as_view(), name='index'),
    path('patentes/', views.BoletinPatentesListView.as_view(), name='patentes'),
    path('marcas/', views.BoletinMarcaListView.as_view(), name='marcas'),
    path('periodo/<slug:slug>/', views.PeriodoBoletinDetailView.as_view(), name='periodo_detalle'),
]
