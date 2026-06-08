from collections import OrderedDict

from django.views.generic import DetailView, TemplateView

from .models import PeriodoBoletin, Boletin


class BoletinIndexView(TemplateView):
    """Landing de /boletines/ con dos cards: Patentes y Marcas.
    Aclara la naveg cuando llegan a la URL raiz sin contexto.
    """
    template_name = 'boletines/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_patentes'] = (
            PeriodoBoletin.objects
            .filter(tipo=PeriodoBoletin.Tipo.GENERAL)
            .count()
        )
        context['count_marcas'] = (
            PeriodoBoletin.objects
            .filter(tipo=PeriodoBoletin.Tipo.MARCA)
            .count()
        )
        return context


class BoletinPatentesListView(TemplateView):
    """Vista de los Boletines de Patentes / Diseño Industrial.
    Equivalente a BoletinPage de SilverStripe. En el modelo el tipo se
    llama 'general' por razones historicas pero contiene patentes + DI.
    """
    template_name = 'boletines/patentes.html'

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


# Alias para compat con codigo que aun importe BoletinGeneralListView
BoletinGeneralListView = BoletinPatentesListView


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
