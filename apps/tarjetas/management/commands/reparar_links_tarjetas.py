"""
Repara las Tarjeta cuyo `link_externo` apunta al sitio v3 legacy
(dinapi.gov.py/portal/v3/...) para que apunten a la pagina equivalente
en el sitio Django.

Estrategia:
  1. Parsear SiteTree del SQL legacy y construir un map
     full_path -> legacy_id (recorriendo URLSegment + ParentID hacia arriba).
  2. Para cada Tarjeta con link_externo apuntando a /portal/v3/<path>:
     - Buscar <path> en el map.
     - Resolver la Pagina Django por legacy_id.
     - Setear link_interno_url = URL Django y vaciar link_externo.

Uso:
    python manage.py reparar_links_tarjetas              # dry-run
    python manage.py reparar_links_tarjetas --apply
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples
from apps.core.models import Pagina
from apps.tarjetas.models import Tarjeta


# Patron de URL legacy. Acepta tanto dominio absoluto como path relativo.
LEGACY_URL_RE = re.compile(
    r'^(?:https?://(?:www\.)?dinapi\.gov\.py)?/?portal/v3/(?P<path>[^?#]*?)/?(?:[?#].*)?$',
    re.IGNORECASE,
)


def _build_path_map(sql_text):
    """Construye dict {path_completo: legacy_id} desde la tabla SiteTree.

    SiteTree cols: 0=ID, 1=ClassName, 2=Created, 3=LastEdited, 4=URLSegment,
                   5=Title, 6=MenuTitle, ..., 19=ParentID
    """
    # Primero indexamos URLSegment y ParentID por ID
    nodes = {}
    for t in iter_insert_tuples(sql_text, 'SiteTree'):
        if len(t) < 20:
            continue
        legacy_id = t[0]
        url_segment = (t[4] or '').strip().strip('/')
        parent_id = t[19] or 0
        if url_segment:
            nodes[legacy_id] = (url_segment, parent_id)

    # Recorrer hacia arriba para construir path full
    path_map = {}
    # Map separado por segmento solo (solo lo usamos si el segmento es unico)
    segment_index = {}

    for legacy_id, (segment, parent_id) in nodes.items():
        parts = [segment]
        current_parent = parent_id
        depth = 0
        while current_parent and depth < 10:
            parent_info = nodes.get(current_parent)
            if not parent_info:
                break
            parts.insert(0, parent_info[0])
            current_parent = parent_info[1]
            depth += 1
        full_path = '/'.join(parts).lower()
        path_map[full_path] = legacy_id

        seg_lower = segment.lower()
        segment_index.setdefault(seg_lower, []).append(legacy_id)

    # Solo registramos segmentos que son UNICOS en todo el SiteTree
    # (asi evitamos asignaciones ambiguas como dos URLSegment='aprender-2')
    for seg, ids in segment_index.items():
        if len(ids) == 1 and seg not in path_map:
            path_map[seg] = ids[0]
    return path_map


class Command(BaseCommand):
    help = 'Reapunta link_externo de Tarjeta del sitio v3 legacy a la pagina Django equivalente.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al SQL legacy. Default: <BASE_DIR>/bd_legacy_bk_dinapi_2026-06-05.sql')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')

    def handle(self, *args, **options):
        apply = options['apply']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')
        path_map = _build_path_map(sql_text)
        self.stdout.write(f'Paths de SiteTree indexados: {len(path_map)}')

        # Cache de paginas Django por legacy_id
        paginas_por_legacy = {
            p.legacy_id: p for p in Pagina.objects.filter(activo=True)
        }
        self.stdout.write(f'Paginas Django activas: {len(paginas_por_legacy)}\n')

        # Iterar Tarjetas con link_externo legacy
        candidatas = Tarjeta.objects.exclude(link_externo='').filter(
            link_externo__icontains='/portal/v3/',
        )
        self.stdout.write(f'Tarjetas con link_externo legacy: {candidatas.count()}\n')

        actualizadas = 0
        sin_match_path = 0
        sin_pagina_django = 0

        with transaction.atomic():
            for t in candidatas.iterator():
                m = LEGACY_URL_RE.match(t.link_externo.strip())
                if not m:
                    continue
                path = m.group('path').strip('/').lower()
                if not path:
                    continue

                # Match exacto del path completo primero. Si no, intentar
                # quitar el ultimo segmento (a veces el legacy URL tiene un
                # `aprender-N` redundante apuntando al mismo contenedor padre).
                legacy_id = path_map.get(path)
                if not legacy_id and '/' in path:
                    parent_path = path.rsplit('/', 1)[0]
                    legacy_id = path_map.get(parent_path)
                if not legacy_id:
                    # Ultimo recurso: segmento solo, pero solo si es unico
                    # en todo SiteTree (registrado en path_map gracias al
                    # filtro en _build_path_map).
                    last_seg = path.rsplit('/', 1)[-1]
                    legacy_id = path_map.get(last_seg)
                if not legacy_id:
                    sin_match_path += 1
                    self.stdout.write(self.style.WARNING(
                        f'  [no match path]  Tarjeta {t.legacy_id}: {path!r}'
                    ))
                    continue

                pagina = paginas_por_legacy.get(legacy_id)
                if not pagina:
                    sin_pagina_django += 1
                    self.stdout.write(self.style.WARNING(
                        f'  [no Pagina]      Tarjeta {t.legacy_id}: path={path!r} -> legacy {legacy_id}'
                    ))
                    continue

                django_url = f'/{pagina.slug}/'
                self.stdout.write(
                    f'  Tarjeta {t.legacy_id:3d}: {path[:45]:45s} -> {django_url}'
                )
                if apply:
                    Tarjeta.objects.filter(pk=t.pk).update(
                        link_externo='',
                        link_interno_url=django_url,
                    )
                actualizadas += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen:\n'
            f'  Actualizadas:           {actualizadas}\n'
            f'  Sin match en SiteTree:  {sin_match_path}\n'
            f'  Sin Pagina Django:      {sin_pagina_django}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))
