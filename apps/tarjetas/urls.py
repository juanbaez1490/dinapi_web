from django.urls import path

from . import views

app_name = 'tarjetas'

urlpatterns = [
    path('', views.TarjetaPageListView.as_view(), name='lista'),
    path('acordeon/', views.AcordeonPageListView.as_view(), name='acordeon'),
    path('acordeon/<int:legacy_id>/', views.AcordeonPageDetailView.as_view(), name='acordeon_detalle'),
    path('<int:legacy_id>/', views.TarjetaPageDetailView.as_view(), name='detalle'),
]
