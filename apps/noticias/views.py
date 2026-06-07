from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Noticia, CategoriaNoticia, RevistaPage


def _get_ultimo_boletin():
    """Devuelve el boletin mas reciente con imagen o pdf para el sidebar."""
    try:
        from apps.boletines.models import Boletin
        return (
            Boletin.objects
            .filter(activo=True)
            .exclude(imagen='', pdf='')
            .order_by('-fecha_publicacion', '-id')
            .first()
        )
    except Exception:
        return None


class NoticiaListView(ListView):
    model = Noticia
    template_name = 'noticias/lista.html'
    context_object_name = 'noticias'
    paginate_by = 10

    def get_queryset(self):
        queryset = Noticia.objects.filter(activo=True).order_by('-fecha')
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(titulo__icontains=search) | Q(contenido__icontains=search)
            )
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria__slug=categoria)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaNoticia.objects.all()
        context['noticias_destacadas'] = Noticia.noticias_destacadas()[:5]
        context['ultimo_boletin'] = _get_ultimo_boletin()
        return context


class NoticiaDetailView(DetailView):
    model = Noticia
    template_name = 'noticias/detalle.html'
    context_object_name = 'noticia'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['noticias_relacionadas'] = Noticia.objects.filter(
            categoria=self.object.categoria,
            activo=True
        ).exclude(id=self.object.id)[:4]
        context['ultimo_boletin'] = _get_ultimo_boletin()
        return context


class RevistaDetailView(DetailView):
    model = RevistaPage
    template_name = 'noticias/revista_detalle.html'
    context_object_name = 'revista'
    slug_field = 'slug'

    def get_queryset(self):
        return RevistaPage.objects.filter(activo=True)


def noticias_destacadas(request):
    noticias = Noticia.noticias_destacadas()
    return render(request, 'noticias/destacadas.html', {
        'noticias': noticias,
        'titulo': 'Noticias Destacadas',
    })


def buscar_noticias(request):
    query = request.GET.get('q', '')
    if query:
        noticias = Noticia.objects.filter(
            Q(titulo__icontains=query) | Q(contenido__icontains=query),
            activo=True
        ).order_by('-fecha')
    else:
        noticias = Noticia.objects.none()

    return render(request, 'noticias/busqueda.html', {
        'noticias': noticias,
        'query': query,
        'titulo': 'Resultados de busqueda: "{}"'.format(query),
    })
