from django.db.models import Q
from django.views.generic import ListView, DetailView

from .models import Biblioteca, CategoriaBiblioteca, EtiquetaBiblioteca


class BibliotecaListView(ListView):
    model = Biblioteca
    template_name = 'biblioteca/lista.html'
    context_object_name = 'items'
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Biblioteca.objects
            .filter(ocultar=False)
            .select_related('categoria')
            .prefetch_related('etiquetas')
            .order_by('-fecha_ordenamiento', '-fecha_creacion')
        )

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(titulo__icontains=q)
                | Q(descripcion__icontains=q)
                | Q(categoria__nombre__icontains=q)
                | Q(etiquetas__nombre__icontains=q)
            ).distinct()

        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            queryset = queryset.filter(categoria__slug=categoria)

        etiqueta = self.request.GET.get('etiqueta', '').strip()
        if etiqueta:
            queryset = queryset.filter(etiquetas__slug=etiqueta)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaBiblioteca.objects.all()
        context['etiquetas'] = EtiquetaBiblioteca.objects.all()
        context['q'] = self.request.GET.get('q', '')
        context['categoria_activa'] = self.request.GET.get('categoria', '')
        context['etiqueta_activa'] = self.request.GET.get('etiqueta', '')
        return context


class BibliotecaDetailView(DetailView):
    model = Biblioteca
    template_name = 'biblioteca/detalle.html'
    context_object_name = 'item'
    slug_field = 'slug'

    def get_queryset(self):
        return (
            Biblioteca.objects
            .filter(ocultar=False)
            .select_related('categoria')
            .prefetch_related('videos', 'imagenes', 'documentos', 'etiquetas')
        )
