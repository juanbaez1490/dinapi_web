import re
import unicodedata

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.noticias.models import Noticia

from .models import Anuncio, CarouselItem, EnlaceInteres, Pagina, TemaEje

# Banners institucionales: (legacy_id_pagina, imagen_static, alt)
# Apuntamos por legacy_id explicito porque el matching por slug-fragment es
# ambiguo (varias paginas pueden contener "transparencia", "rendicion", etc.
# en su slug).
_BANNERS_INSTITUCIONALES_CONFIG = [
    (1001, 'img/home/banner-transparencia.png',      'Banner transparencia'),
    (418,  'img/home/portada-rindiendo-cuentas.jpg', 'Rendicion de cuentas'),
    (675,  'img/home/portada-mecip.jpg',             'Mecip'),
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


def _build_breadcrumbs(pagina):
    """Construye la jerarquia de breadcrumbs caminando parent_legacy_id hacia arriba.

    Devuelve una lista de dicts {titulo, url, current} ordenada raiz -> actual.
    Limite de profundidad 6 para evitar ciclos.
    """
    cadena = []
    actual = pagina
    seen = set()
    for _ in range(6):
        if not actual or actual.id in seen:
            break
        seen.add(actual.id)
        cadena.append(actual)
        if not actual.parent_legacy_id:
            break
        actual = Pagina.objects.filter(
            legacy_id=actual.parent_legacy_id, activo=True,
        ).first()

    cadena.reverse()
    crumbs = [{'titulo': 'Inicio', 'url': reverse('core:home'), 'current': False}]
    for idx, p in enumerate(cadena):
        crumbs.append({
            'titulo': p.titulo,
            'url': _resolve_pagina_url(p),
            'current': idx == len(cadena) - 1,
        })
    return crumbs


def pagina_detalle_view(request, slug):
    pagina = get_object_or_404(Pagina, slug=slug, activo=True)

    # Algunos tipos de Pagina son contenedores que no se renderizan con
    # template propio: redirigen al listado canonico de la app correspondiente.
    if pagina.tipo in (
        Pagina.TipoPagina.BOLETIN,
        Pagina.TipoPagina.PERIODO_BOLETIN,
    ):
        return redirect('boletines:patentes')
    if pagina.tipo in (
        Pagina.TipoPagina.BOLETIN_MARCA,
        Pagina.TipoPagina.PERIODO_BOLETIN_MARCA,
        Pagina.TipoPagina.PERIODO_BOLETIN_MARCA_GENERICO,
    ):
        return redirect('boletines:marcas')

    plantilla = pagina.plantilla_personalizada or 'core/pagina_detalle.html'

    contexto = {
        'pagina': pagina,
        'paginas_menu': Pagina.objects.filter(activo=True, mostrar_en_menu=True).order_by('orden_menu', 'titulo'),
        'breadcrumbs': _build_breadcrumbs(pagina),
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
    elif pagina.tipo in (Pagina.TipoPagina.ARCHIVO_DESPLEGABLE, Pagina.TipoPagina.ARCHIVOS):
        # ArchivoDesplegablePage / ArchivoPage:
        # - Pueden tener subpaginas (otras ArchivoPage/ArchivoDesplegablePage)
        #   que se renderizan como secciones de acordeon.
        # - Esas subpaginas pueden a su vez tener nietos (caso transparencia,
        #   donde "Leyes N° 7089" contiene sub-secciones por ano).
        # - Pueden tener Archivos pegados directamente.
        from apps.archivos.models import Archivo
        subpaginas = list(
            Pagina.objects.filter(
                activo=True,
                parent_legacy_id=pagina.legacy_id,
                tipo__in=[Pagina.TipoPagina.ARCHIVOS, Pagina.TipoPagina.ARCHIVO_DESPLEGABLE],
            ).order_by('orden_menu', 'legacy_id')
        )
        archivos_directos = list(
            Archivo.objects.filter(pagina_legacy_id=pagina.legacy_id)
            .order_by('-fecha_ordenamiento', '-legacy_id')
        )
        if subpaginas:
            archivos_por_subpagina = {}
            subsubpaginas_por_subpagina = {}
            for sub in subpaginas:
                archivos_por_subpagina[sub.id] = list(
                    Archivo.objects.filter(pagina_legacy_id=sub.legacy_id)
                    .order_by('-fecha_ordenamiento', '-legacy_id')
                )
                # Nietos (sub-sub-paginas) con sus archivos
                nietos = list(
                    Pagina.objects.filter(
                        activo=True,
                        parent_legacy_id=sub.legacy_id,
                        tipo__in=[Pagina.TipoPagina.ARCHIVOS, Pagina.TipoPagina.ARCHIVO_DESPLEGABLE],
                    ).order_by('orden_menu', 'legacy_id')
                )
                nietos_con_archivos = []
                for nieto in nietos:
                    archivos_nieto = list(
                        Archivo.objects.filter(pagina_legacy_id=nieto.legacy_id)
                        .order_by('-fecha_ordenamiento', '-legacy_id')
                    )
                    if archivos_nieto:
                        nietos_con_archivos.append({
                            'pagina': nieto,
                            'archivos': archivos_nieto,
                        })
                subsubpaginas_por_subpagina[sub.id] = nietos_con_archivos
            plantilla = 'core/pagina_archivo_desplegable.html'
            contexto['subpaginas'] = subpaginas
            contexto['archivos_por_subpagina'] = archivos_por_subpagina
            contexto['subsubpaginas_por_subpagina'] = subsubpaginas_por_subpagina
            contexto['archivos_directos'] = archivos_directos
        else:
            plantilla = 'core/pagina_archivos.html'
            contexto['archivos'] = archivos_directos
    elif pagina.tipo == Pagina.TipoPagina.TARJETAS_SIMPLES:
        # TarjetaSimplePage = lista de tarjetas con titulo + link (interno
        # por legacy_id o externo). Resolvemos los links internos a slug.
        from apps.tarjetas.models import TarjetaSimple
        tarjetas_qs = TarjetaSimple.objects.filter(pagina_legacy_id=pagina.legacy_id).order_by('legacy_id')
        # Resolver link_interno_legacy_id -> URL
        legacy_ids = [t.link_interno_legacy_id for t in tarjetas_qs if t.link_interno_legacy_id]
        paginas_destino = {
            p.legacy_id: p
            for p in Pagina.objects.filter(legacy_id__in=legacy_ids, activo=True)
        }
        tarjetas_render = []
        for t in tarjetas_qs:
            url = ''
            if t.link_interno_legacy_id and t.link_interno_legacy_id in paginas_destino:
                url = _resolve_pagina_url(paginas_destino[t.link_interno_legacy_id])
            elif t.link_externo:
                url = t.link_externo
            tarjetas_render.append({
                'titulo': t.titulo,
                'url': url,
                'es_externo': bool(t.link_externo and not t.link_interno_legacy_id),
            })
        plantilla = 'core/pagina_tarjeta_simple.html'
        contexto['tarjetas_simples'] = tarjetas_render
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
    """Resuelve cada banner por legacy_id explicito. URL queda '#' si la
    pagina no existe o esta inactiva."""
    banners = []
    for legacy_id, imagen, alt in _BANNERS_INSTITUCIONALES_CONFIG:
        pagina = (
            Pagina.objects
            .filter(activo=True, legacy_id=legacy_id)
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
    """
    Construye las 12 tarjetas del landing institucional con mapping explicito
    de legacy_id a label, replicando lo que muestra el legacy.

    Cada entry es (legacy_id, label_default, url_alternativa).
    Si la Pagina existe en BD, usa su titulo y su URL resuelta.
    Si no existe, usa label_default + url_alternativa (util para entries que
    apuntan a PDFs externos como el Plan Estrategico).
    """
    cards_spec = [
        (330,  'Acceso a la Información Pública',               None),
        (329,  'Autoridades',                                   None),
        (331,  'Concursos',                                     None),
        (968,  'Convenios',                                     None),
        (891,  'Gestión de las personas',                       None),
        (341,  'Marco Normativo de la Propiedad Intelectual',   None),
        (675,  'MECIP',                                         None),
        (327,  'Misión, Visión y Valores Institucionales',      None),
        (328,  'Organigrama',                                   None),
        # Plan Estrategico: link directo a PDF, no hay Pagina equivalente
        (None, 'Plan Estratégico Institucional',
               '/assets/archivos-institucionales/PEI-2024-2028-EDITADO-27022024.pdf'),
        (988,  'Plan Nacional de Propiedad Intelectual',        None),
        (429,  'Programas y Proyectos',                         None),
    ]

    paginas_by_legacy = {
        p.legacy_id: p
        for p in Pagina.objects.filter(
            activo=True,
            legacy_id__in=[lid for lid, _, _ in cards_spec if lid is not None],
        )
    }

    cards = []
    for idx, (legacy_id, label, url_alt) in enumerate(cards_spec):
        if legacy_id is None:
            cards.append({'titulo': label, 'url': url_alt, 'variant': idx % 3})
            continue
        pagina_obj = paginas_by_legacy.get(legacy_id)
        if pagina_obj is None:
            # la pagina no esta en BD o esta desactivada -> saltamos
            continue
        cards.append({
            'titulo': label or _format_card_title(pagina_obj.titulo),
            'url': _resolve_pagina_url(pagina_obj),
            'variant': idx % 3,
        })

    return cards


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
            return reverse('boletines:patentes')
        if tipo in {
            Pagina.TipoPagina.BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA_GENERICO,
        }:
            return reverse('boletines:marcas')
        if tipo in {Pagina.TipoPagina.ARCHIVOS, Pagina.TipoPagina.ARCHIVO_DESPLEGABLE}:
            # Cada ArchivoPage/ArchivoDesplegablePage tiene sus propios PDFs;
            # llevamos al detalle individual, no al listado global de biblioteca.
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
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
