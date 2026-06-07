from django.urls import path
from . import views

app_name = 'biblioteca'

urlpatterns = [
    path('', views.BibliotecaListView.as_view(), name='lista'),
    path('<slug:slug>/', views.BibliotecaDetailView.as_view(), name='detalle'),
]
