from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import Noticia, CategoriaNoticia

class NoticiaListView(ListView):
    """Lista de noticias - Mapea ListaNoticiasBuscador de Page.php"""
    model = Noticia
    template_name = 'noticias/lista.html'
    context_object_name = 'noticias'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Noticia.objects.filter(activo=True).order_by('-fecha')
        
        # Búsqueda
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                models.Q(titulo__icontains=search) | 
                models.Q(contenido__icontains=search)
            )
        
        # Filtrar por categoría
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria__slug=categoria)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaNoticia.objects.all()
        context['noticias_destacadas'] = Noticia.noticias_destacadas()[:5]
        return context


class NoticiaDetailView(DetailView):
    """Detalle de noticia"""
    model = Noticia
    template_name = 'noticias/detalle.html'
    context_object_name = 'noticia'
    slug_field = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Noticias relacionadas (misma categoría)
        context['noticias_relacionadas'] = Noticia.objects.filter(
            categoria=self.object.categoria,
            activo=True
        ).exclude(id=self.object.id)[:4]
        return context


def noticias_destacadas(request):
    """Vista para mostrar noticias destacadas - Mapea ListaNoticiasDestacadas"""
    noticias = Noticia.noticias_destacadas()
    context = {
        'noticias': noticias,
        'titulo': 'Noticias Destacadas'
    }
    return render(request, 'noticias/destacadas.html', context)


def buscar_noticias(request):
    """Búsqueda de noticias - Mapea ListaNoticiasBuscador de Page.php"""
    query = request.GET.get('q', '')
    if query:
        noticias = Noticia.objects.filter(
            models.Q(titulo__icontains=query) | 
            models.Q(contenido__icontains=query),
            activo=True
        ).order_by('-fecha')
    else:
        noticias = Noticia.objects.none()
    
    context = {
        'noticias': noticias,
        'query': query,
        'titulo': f'Resultados de búsqueda: "{query}"'
    }
    return render(request, 'noticias/busqueda.html', context)