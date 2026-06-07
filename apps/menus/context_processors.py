from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse

from .models import MenuDerecho, Popup
from apps.core.models import Pagina, SiteConfig


def menu_popup_context(request):
    """Inyecta menu derecho, popup activo y site_config en todas las plantillas."""
    try:
        menu_principal_simples = []
        menu_principal_grupos = []

        paginas_activas = list(
            Pagina.objects.filter(activo=True)
            .exclude(tipo=Pagina.TipoPagina.HOME)
            .order_by('orden_menu', 'legacy_id', 'id')
        )
        paginas_activas_por_legacy = {
            p.legacy_id: p for p in paginas_activas if p.legacy_id is not None
        }

        paginas_menu = [p for p in paginas_activas if p.mostrar_en_menu]
        paginas_menu_por_legacy = {
            p.legacy_id: p for p in paginas_menu if p.legacy_id is not None
        }

        hijos_por_padre = {}
        for pagina in paginas_menu:
            if pagina.parent_legacy_id:
                hijos_por_padre.setdefault(pagina.parent_legacy_id, []).append(pagina)

        top_level_paginas = []
        for pagina in paginas_menu:
            parent_id = pagina.parent_legacy_id
            if not parent_id:
                top_level_paginas.append(pagina)
                continue
            parent_real = paginas_activas_por_legacy.get(parent_id)
            if parent_real and parent_real.tipo == Pagina.TipoPagina.HOME:
                top_level_paginas.append(pagina)
                continue
            if parent_id in paginas_menu_por_legacy:
                continue
            if parent_real is None:
                top_level_paginas.append(pagina)

        for pagina in top_level_paginas:
            hijos_directos = hijos_por_padre.get(pagina.legacy_id, [])
            if hijos_directos:
                menu_principal_grupos.append({
                    'padre': pagina,
                    'url': _resolve_pagina_url(pagina),
                    'hijos': _flatten_descendants(hijos_directos, hijos_por_padre),
                })
            else:
                menu_principal_simples.append({
                    'pagina': pagina,
                    'url': _resolve_pagina_url(pagina),
                })

        items_menu = list(MenuDerecho.objects.all().order_by('legacy_id', 'id'))
        padres = []
        hijos = []
        enlaces_simples = []
        padres_con_hijos = []
        grupo_actual = None

        for item in items_menu:
            if item.padre:
                padres.append(item)
                grupo_actual = {'padre': item, 'hijos': []}
                padres_con_hijos.append(grupo_actual)
                continue
            if item.hijo:
                hijos.append(item)
                if grupo_actual is not None:
                    grupo_actual['hijos'].append(item)
                continue
            enlaces_simples.append(item)

        popup_activo = Popup.objects.filter(activo=True).first()
        site_config = SiteConfig.objects.first()

    except (ProgrammingError, OperationalError):
        menu_principal_simples = []
        menu_principal_grupos = []
        padres = []
        hijos = []
        enlaces_simples = []
        padres_con_hijos = []
        popup_activo = None
        site_config = None

    return {
        'menu_principal_simples': menu_principal_simples,
        'menu_principal_grupos': menu_principal_grupos,
        'menu_derecho_padres': padres,
        'menu_derecho_hijos': hijos,
        'menu_derecho_simples': enlaces_simples,
        'menu_derecho_grupos': padres_con_hijos,
        'popup_activo': popup_activo,
        'site_config': site_config,
    }


def _flatten_descendants(paginas, hijos_por_padre, nivel=1):
    resultado = []
    for pagina in paginas:
        resultado.append({
            'pagina': pagina,
            'url': _resolve_pagina_url(pagina),
            'nivel': nivel,
        })
        if pagina.legacy_id in hijos_por_padre:
            resultado.extend(
                _flatten_descendants(hijos_por_padre[pagina.legacy_id], hijos_por_padre, nivel=nivel + 1)
            )
    return resultado


def _resolve_pagina_url(pagina):
    tipo = pagina.tipo
    try:
        if tipo == Pagina.TipoPagina.HOME:
            return reverse('core:home')
        if tipo == Pagina.TipoPagina.CONTACTO:
            return reverse('contacto:contact')
        if tipo == Pagina.TipoPagina.RECLAMOS:
            try:
                return reverse('reclamos:formulario')
            except NoReverseMatch:
                return reverse('contacto:contact')
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
        if tipo in {Pagina.TipoPagina.TARJETAS, Pagina.TipoPagina.TARJETAS_SIMPLES}:
            return reverse('tarjetas:lista')
        if tipo == Pagina.TipoPagina.ACORDEON:
            return reverse('tarjetas:acordeon')
        return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
    except NoReverseMatch:
        return '#'
