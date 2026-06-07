from collections import OrderedDict

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, TemplateView

from .models import Concurso


class ConcursoListView(TemplateView):
    template_name = 'concursos/lista.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Concurso.objects.all().order_by('-fecha', '-legacy_id')

        agrupado = OrderedDict()
        for concurso in queryset:
            year = concurso.fecha.year if concurso.fecha else 'Sin fecha'
            agrupado.setdefault(year, []).append(concurso)

        context['concursos_por_anio'] = agrupado
        return context


class ConcursoDetailView(DetailView):
    model = Concurso
    template_name = 'concursos/detalle.html'
    context_object_name = 'concurso'
    slug_field = 'slug'


def legacy_detalle_redirect(request):
    legacy_id = request.GET.get('idConcurso')
    if not legacy_id:
        return redirect('concursos:lista')

    concurso = get_object_or_404(Concurso, legacy_id=legacy_id)
    return redirect('concursos:detalle', slug=concurso.slug)
