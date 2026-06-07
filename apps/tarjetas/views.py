from django.shortcuts import render
from django.views.generic import DetailView, TemplateView

from .models import TarjetaPage, AcordeonPage


class TarjetaPageListView(TemplateView):
	template_name = 'tarjetas/lista.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['paginas_tarjetas'] = TarjetaPage.objects.prefetch_related('tarjetas').all()
		return context


class AcordeonPageListView(TemplateView):
	template_name = 'tarjetas/acordeon.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['paginas_acordeon'] = AcordeonPage.objects.prefetch_related('desplegables').all()
		return context


class TarjetaPageDetailView(DetailView):
	model = TarjetaPage
	template_name = 'tarjetas/detalle.html'
	context_object_name = 'pagina'
	slug_field = 'legacy_id'
	slug_url_kwarg = 'legacy_id'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['tarjetas'] = self.object.tarjetas.all()
		return context


class AcordeonPageDetailView(DetailView):
	model = AcordeonPage
	template_name = 'tarjetas/acordeon_detalle.html'
	context_object_name = 'pagina'
	slug_field = 'legacy_id'
	slug_url_kwarg = 'legacy_id'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['items'] = self.object.desplegables.all()
		return context
