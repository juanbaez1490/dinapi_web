from django.urls import path

from . import views

app_name = 'concursos'

urlpatterns = [
    path('', views.ConcursoListView.as_view(), name='lista'),
    path('detalle-concurso', views.legacy_detalle_redirect, name='legacy_detalle'),
    path('<slug:slug>/', views.ConcursoDetailView.as_view(), name='detalle'),
]
