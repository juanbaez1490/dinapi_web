from django.urls import path

from . import views

app_name = 'boletines'

urlpatterns = [
    path('', views.BoletinGeneralListView.as_view(), name='general'),
    path('marcas/', views.BoletinMarcaListView.as_view(), name='marcas'),
    path('periodo/<slug:slug>/', views.PeriodoBoletinDetailView.as_view(), name='periodo_detalle'),
]
