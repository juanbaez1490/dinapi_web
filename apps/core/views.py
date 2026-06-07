import re
import unicodedata

from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.noticias.models import Noticia

from .models import Anuncio, CarouselItem, EnlaceInteres, Pagina, TemaEje

# Banners institucionales: (slug_fragment, imagen_static, alt)
_BANNERS_INSTITUCIONALES_CONFIG = [
    ('transparencia',  'img/home/banner-transparencia.png',      'Banner transparencia'),
    ('rendicion',      'img/home/portada-rindiendo-cuentas.jpg', 'Rendicion de cuentas'),
    ('mecip',          'img/home/portada-mecip.jpg',             'Mecip'),
]

# Ejes: numero -> (titulo_grupo, color)
_EJE_META = {
    1: ('Propiedad Industrial',                '#ea2428'),
    2: ('Derecho de Autor y Derechos Conexos', '#00529c'),
    3: ('Observancia',                         '#e8b116'),
}


def home_view(request):
    pagina_home = (
        Pagina.objects.filter(activo=True, tipo=Pagina.TipoPagina.HOME)
        .order_by('orden_menu', 'id')
        .first()
    )
    recomendacion_agente = ''
    if pagina_home:
        recomendacion_agente = pagina_home.subtitulo or pagina_home.descripcion

    noticias_destacadas = Noticia.noticias_destacadas()[:3]

    contexto = {
        'pagina': pagina_home,
        'paginas_menu': Pagina.objects.filter(activo=True, mostrar_en_menu=True).order_by('orden_menu', 'titulo'),
        'noticias_destacadas': noticias_destacadas,
        'ejes_home': _build_ejes_home(),
        'banners_institucionales': _build_banners_institucionales(),
        'banners_servicios': _build_banners_servicios(),
        'recomendacion_agente': recomendacion_agente,
        # Bloques de home dinámicos (Bloque C)
        'carousel_items': _build_carousel(),
        'anuncios': _build_anuncios(),
        'enlaces_interes': _build_enlaces_interes(),
    }
    return render(request, 'core/home.html', contexto)


def pagina_detalle_view(request, slug):
    pagina = get_object_or_404(Pagina, slug=slug, activo=True)
    plantilla = pagina.plantilla_personalizada or 'core/pagina_detalle.html'

    contexto = {
        'pagina': pagina,
        'paginas_menu': Pagina.objects.filter(activo=True, mostrar_en_menu=True).order_by('orden_menu', 'titulo'),
    }

    if pagina.tipo == Pagina.TipoPagina.INSTITUCIONAL:
        plantilla = 'core/institucional.html'
        contexto['tarjetas_institucionales'] = _build_institucional_cards(pagina)
    elif pagina.tipo == Pagina.TipoPagina.ACORDEON:
        # Para AcordeonPage combinamos el HTML del SiteTree (pagina.contenido)
        # con los datos relacionados de tarjetas.AcordeonPage (contenido_superior,
        # items desplegables, anexo). En SilverStripe ambos se renderizaban
        # juntos en el template AcordeonPage.ss.
        from apps.tarjetas.models import AcordeonPage as TarjetasAcordeonPage
        acordeon = (
            TarjetasAcordeonPage.objects
            .prefetch_related('desplegables')
            .filter(legacy_id=pagina.legacy_id)
            .first()
        )
        if acordeon:
            plantilla = 'core/pagina_acordeon.html'
            contexto['acordeon'] = acordeon
            contexto['acordeon_items'] = acordeon.desplegables.all().order_by(
                '-fecha_ordenamiento', '-legacy_id'
            )
    elif pagina.tipo == Pagina.TipoPagina.TARJETAS:
        # Para TarjetaPage pulleamos la TarjetaPage relacionada con sus
        # tarjetas hijas. El template renderiza un grid de cards.
        from apps.tarjetas.models import TarjetaPage as TarjetasTarjetaPage
        tarjeta_page = (
            TarjetasTarjetaPage.objects
            .prefetch_related('tarjetas')
            .filter(legacy_id=pagina.legacy_id)
            .first()
        )
        if tarjeta_page:
            plantilla = 'core/pagina_tarjetas.html'
            contexto['tarjeta_page'] = tarjeta_page
            contexto['tarjetas'] = tarjeta_page.tarjetas.all().order_by(
                'legacy_id'
            )

    return render(request, plantilla, contexto)


# ---------------------------------------------------------------------------
# Helpers privados — Bloques de home
# ---------------------------------------------------------------------------

def _build_carousel():
    """Slides activos del carousel, ordenados por 'orden'."""
    try:
        return list(CarouselItem.objects.filter(activo=True).order_by('orden', 'id'))
    except Exception:
        return []


def _build_anuncios():
    """
    Anuncios activos con filtro de fechas:
    - Sin fecha_inicio  → siempre se muestra
    - Con fecha_inicio  → visible desde esa fecha
    - Con fecha_fin     → se oculta después de esa fecha
    """
    try:
        hoy = timezone.localdate()
        return list(
            Anuncio.objects
            .filter(activo=True)
            .filter(
                models_q_fecha_inicio(hoy)
            )
            .filter(
                models_q_fecha_fin(hoy)
            )
            .order_by('orden', 'id')
        )
    except Exception:
        return []


def _build_enlaces_interes():
    """Accesos rápidos activos del home."""
    try:
        return list(EnlaceInteres.objects.filter(activo=True).order_by('orden', 'id'))
    except Exception:
        return []


def models_q_fecha_inicio(hoy):
    from django.db.models import Q
    return Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=hoy)


def models_q_fecha_fin(hoy):
    from django.db.models import Q
    return Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy)


# ---------------------------------------------------------------------------
# Helpers privados — Bloques existentes
# ---------------------------------------------------------------------------

def _build_ejes_home():
    """Construye los ejes del home desde TemaEje. Vacio si aun no se importaron."""
    temas = (
        TemaEje.objects
        .filter(activo=True)
        .select_related('pagina')
        .order_by('eje', 'orden', 'nombre')
    )

    grupos = {}
    for tema in temas:
        eje_num = tema.eje
        if eje_num not in grupos:
            titulo_eje, color_eje = _EJE_META.get(eje_num, ('Eje {}'.format(eje_num), '#666666'))
            grupos[eje_num] = {'titulo': titulo_eje, 'color': color_eje, 'items': []}
        grupos[eje_num]['items'].append({
            'texto': tema.nombre,
            'url': tema.get_url(resolve_fn=_resolve_pagina_url),
        })

    return [grupos[k] for k in sorted(grupos.keys())]


def _build_banners_institucionales():
    """Busca paginas por slug fragment. URL queda '#' si aun no estan importadas."""
    banners = []
    for slug_fragment, imagen, alt in _BANNERS_INSTITUCIONALES_CONFIG:
        pagina = (
            Pagina.objects
            .filter(activo=True, slug__icontains=slug_fragment)
            .order_by('orden_menu', 'id')
            .first()
        )
        url = _resolve_pagina_url(pagina) if pagina else '#'
        banners.append({'url': url, 'imagen': imagen, 'alt': alt})
    return banners


def _build_banners_servicios():
    """Portales externos del gobierno paraguayo (no son el sitio viejo)."""
    return [
        {
            'url': 'https://informacionpublica.paraguay.gov.py/portal/#!/buscar_informacion#busqueda',
            'imagen': 'img/home/portal-informacion-publica.jpg',
            'alt': 'Portal de informacion publica',
        },
        {
            'url': 'https://denuncias.contraloria.gov.py/',
            'imagen': 'img/home/portal-denuncias-anticorrupcion.jpg',
            'alt': 'Portal de denuncias anticorrupcion',
        },
    ]


def _build_institucional_cards(pagina):
    hijos = list(
        Pagina.objects.filter(activo=True, parent_legacy_id=pagina.legacy_id)
        .order_by('orden_menu', 'legacy_id', 'id')
    )
    if not hijos:
        return []

    hijos_normalizados = [(item, _normalize_text(item.titulo)) for item in hijos]
    card_specs = [
        {'tokens': ['acceso', 'informacion', 'publica']},
        {'tokens': ['autoridades']},
        {'tokens': ['concursos']},
        {'tokens': ['convenios'], 'prefer_without': ['dinapi']},
        {'tokens': ['gestion', 'personas']},
        {'tokens': ['marco', 'normativo']},
        {'tokens': ['mecip']},
        {'tokens': ['mision', 'vision', 'valores', 'institucionales']},
        {'tokens': ['organigrama']},
        {'tokens': ['plan', 'nacional', 'propiedad', 'intelectual']},
        {'tokens': ['programas', 'proyectos']},
    ]

    selected = []
    used_legacy_ids = set()

    for spec in card_specs:
        candidates = []
        for item, norm_title in hijos_normalizados:
            if item.legacy_id in used_legacy_ids:
                continue
            if all(token in norm_title for token in spec['tokens']):
                candidates.append((item, norm_title))
        if not candidates:
            continue

        prefer_without = spec.get('prefer_without')
        if prefer_without:
            candidates.sort(key=lambda d: (any(t in d[1] for t in prefer_without), len(d[1])))
        else:
            candidates.sort(key=lambda d: len(d[1]))

        picked = candidates[0][0]
        selected.append(picked)
        used_legacy_ids.add(picked.legacy_id)

    return [
        {'titulo': _format_card_title(item.titulo), 'url': _resolve_pagina_url(item), 'variant': idx % 3}
        for idx, item in enumerate(selected)
    ]


def _format_card_title(title):
    clean = re.sub(r'\s+', ' ', (title or '').strip())
    return clean.title() if clean.isupper() else clean


def _normalize_text(value):
    if not value:
        return ''
    normalized = unicodedata.normalize('NFD', value)
    ascii_text = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    ascii_text = re.sub(r'[^a-z0-9\s]', ' ', ascii_text.lower())
    return re.sub(r'\s+', ' ', ascii_text).strip()


def _resolve_pagina_url(pagina):
    tipo = pagina.tipo
    try:
        if tipo == Pagina.TipoPagina.HOME:
            return '/'
        if tipo == Pagina.TipoPagina.CONTACTO:
            return reverse('contacto:contact')
        if tipo == Pagina.TipoPagina.RECLAMOS:
            return reverse('reclamos:formulario')
        if tipo in {Pagina.TipoPagina.NOTICIAS, Pagina.TipoPagina.CODEPI, Pagina.TipoPagina.REVISTA}:
            return reverse('noticias:lista')
        if tipo == Pagina.TipoPagina.BIBLIOTECA:
            return reverse('biblioteca:lista')
        if tipo in {Pagina.TipoPagina.CONCURSOS, Pagina.TipoPagina.CONCURSO_JUVENTUD}:
            return reverse('concursos:lista')
        if tipo in {Pagina.TipoPagina.BOLETIN, Pagina.TipoPagina.PERIODO_BOLETIN}:
            return reverse('boletines:general')
        if tipo in {
            Pagina.TipoPagina.BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA_GENERICO,
        }:
            return reverse('boletines:marcas')
        if tipo in {Pagina.TipoPagina.ARCHIVOS, Pagina.TipoPagina.ARCHIVO_DESPLEGABLE}:
            return reverse('biblioteca:lista')
        if tipo == Pagina.TipoPagina.CALENDARIO:
            return reverse('calendario:index')
        if tipo == Pagina.TipoPagina.TARJETAS:
            # Cada TarjetaPage tiene su propio grid de tarjetas;
            # llevamos al detalle individual, no al listado global.
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        if tipo == Pagina.TipoPagina.TARJETAS_SIMPLES:
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        if tipo == Pagina.TipoPagina.ACORDEON:
            # Cada AcordeonPage tiene su propio contenido (header + items + HTML legacy);
            # llevamos al detalle individual, no al listado global.
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
    except NoReverseMatch:
        return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
