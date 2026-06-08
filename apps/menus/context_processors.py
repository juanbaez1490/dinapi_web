from types import SimpleNamespace

from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse

from .models import MenuDerecho, MenuPrincipal, Popup
from apps.core.models import Pagina, SiteConfig


def menu_popup_context(request):
    """Inyecta menu derecho, popup activo y site_config en todas las plantillas."""
    try:
        menu_principal_simples = []
        menu_principal_grupos = []

        # 1) Preferir MenuPrincipal curado (refleja exactamente el navbar legacy).
        items_curados = list(
            MenuPrincipal.objects.filter(activo=True, padre__isnull=True)
            .order_by('orden', 'id')
            .prefetch_related('hijos')
        )

        if items_curados:
            # Cache de Pagina por legacy_id para resolver URLs sin N+1.
            legacy_ids_necesarios = set()
            for item in items_curados:
                if item.pagina_destino_legacy_id:
                    legacy_ids_necesarios.add(item.pagina_destino_legacy_id)
                for h in item.hijos.all():
                    if h.pagina_destino_legacy_id:
                        legacy_ids_necesarios.add(h.pagina_destino_legacy_id)
            paginas_por_legacy = {
                p.legacy_id: p
                for p in Pagina.objects.filter(legacy_id__in=legacy_ids_necesarios, activo=True)
            }

            for item in items_curados:
                hijos_activos = [h for h in item.hijos.all() if h.activo]
                hijos_activos.sort(key=lambda h: (h.orden, h.id))

                url_padre = _resolve_menu_item_url(item, paginas_por_legacy)

                if hijos_activos:
                    hijos_render = [{
                        'pagina': SimpleNamespace(titulo=h.titulo),
                        'url': _resolve_menu_item_url(h, paginas_por_legacy),
                        'nivel': 1,
                        'target_blank': h.target_blank or bool(h.link_externo),
                    } for h in hijos_activos]
                    menu_principal_grupos.append({
                        'padre': SimpleNamespace(titulo=item.titulo, id=item.id),
                        'url': url_padre,
                        'hijos': hijos_render,
                    })
                else:
                    menu_principal_simples.append({
                        'pagina': SimpleNamespace(titulo=item.titulo),
                        'url': url_padre,
                        'target_blank': item.target_blank or bool(item.link_externo),
                    })

        # 2) Fallback: construir desde Pagina jerarquica si no hay MenuPrincipal poblado.
        else:
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


def _resolve_menu_item_url(item, paginas_por_legacy):
    """Resuelve la URL final de un MenuPrincipal. Orden de precedencia:
    1) link_externo  2) pagina_destino_legacy_id  3) link_interno_url  4) '#'.
    """
    if item.link_externo:
        return item.link_externo
    if item.pagina_destino_legacy_id:
        pagina = paginas_por_legacy.get(item.pagina_destino_legacy_id)
        if pagina:
            return _resolve_pagina_url(pagina)
    if item.link_interno_url:
        return item.link_interno_url
    return '#'


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
            return reverse('boletines:patentes')
        if tipo in {
            Pagina.TipoPagina.BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA,
            Pagina.TipoPagina.PERIODO_BOLETIN_MARCA_GENERICO,
        }:
            return reverse('boletines:marcas')
        if tipo in {Pagina.TipoPagina.ARCHIVOS, Pagina.TipoPagina.ARCHIVO_DESPLEGABLE}:
            # Estas paginas tienen su propio detalle (acordeon de PDFs).
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        if tipo == Pagina.TipoPagina.CALENDARIO:
            return reverse('calendario:index')
        if tipo in {Pagina.TipoPagina.TARJETAS, Pagina.TipoPagina.TARJETAS_SIMPLES}:
            # Cada TarjetaPage tiene su grid propio en su detalle.
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        if tipo == Pagina.TipoPagina.ACORDEON:
            # Cada AcordeonPage tiene su acordeon propio en su detalle.
            return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
        return reverse('core:pagina_detalle', kwargs={'slug': pagina.slug})
    except NoReverseMatch:
        return '#'
