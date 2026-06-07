from collections import OrderedDict

from django.views.generic import DetailView, TemplateView

from .models import PeriodoBoletin, Boletin


class BoletinGeneralListView(TemplateView):
    """Vista equivalente a BoletinPage de SilverStripe.
    Agrupa BoletinGeneral (tipo=general) por periodo, ordenados de más nuevo a más viejo.
    """
    template_name = 'boletines/general.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodos = (
            PeriodoBoletin.objects
            .filter(tipo=PeriodoBoletin.Tipo.GENERAL)
            .prefetch_related('boletines')
            .order_by('-legacy_created', '-legacy_id')
        )
        context['periodos'] = periodos
        return context


class BoletinMarcaListView(TemplateView):
    """Vista equivalente a BoletinMarcaPage de SilverStripe.
    Muestra periodos de marca con sus 4 sub-tipos agrupados.
    """
    template_name = 'boletines/marcas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodos = (
            PeriodoBoletin.objects
            .filter(tipo=PeriodoBoletin.Tipo.MARCA)
            .prefetch_related('boletines')
            .order_by('-legacy_created', '-legacy_id')
        )
        # Agrupa por padre para reproducir la jerarquía BoletinMarcaPage > PeriodoBoletin
        por_padre: OrderedDict = OrderedDict()
        for periodo in periodos:
            por_padre.setdefault(periodo.padre_legacy_id, []).append(periodo)

        context['periodos_por_padre'] = por_padre
        return context


class PeriodoBoletinDetailView(DetailView):
    """Detalle de un PeriodoBoletin — lista todos los Boletin asociados.
    Sirve tanto para tipo GENERAL como MARCA.
    """
    model = PeriodoBoletin
    template_name = 'boletines/periodo_detalle.html'
    context_object_name = 'periodo'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        boletines = self.object.boletines.all().order_by('-fecha', '-legacy_id')
        # Agrupar por tipo para mostrar separadores en marcas
        por_tipo = OrderedDict()
        for boletin in boletines:
            por_tipo.setdefault(boletin.get_tipo_display(), []).append(boletin)
        context['boletines'] = boletines
        context['boletines_por_tipo'] = por_tipo
        return context
