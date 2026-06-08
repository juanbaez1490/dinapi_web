"""
Context processors globales del proyecto.

`sidebar_legacy_context`: inyecta los datos para el sidebar lateral con:
  - infodinapi_sidebar: ultima revista InfoDINAPI publicada (link a su detalle).
  - noticias_destacadas_sidebar: 3 noticias destacadas mas recientes.

Los templates que quieren mostrar el sidebar incluyen el partial
`core/_sidebar_legacy.html`; los demas simplemente ignoran las variables.
"""
from django.db.utils import OperationalError, ProgrammingError


def sidebar_legacy_context(request):
    """Devuelve datos para el sidebar lateral que aparece en paginas de detalle."""
    try:
        from apps.biblioteca.models import Biblioteca
        from apps.noticias.models import Noticia

        # Preferimos la ultima InfoDINAPI que tenga imagen_principal cargada,
        # asi el sidebar muestra una portada real en lugar de placeholder.
        # Si no hay ninguna con imagen, caemos a la mas reciente igual.
        base_qs = Biblioteca.objects.filter(
            titulo__icontains='infodinapi', ocultar=False,
        ).order_by('-fecha_ordenamiento', '-fecha_creacion')
        infodinapi = base_qs.exclude(imagen_principal='').first() or base_qs.first()

        # Priorizamos destacadas con imagen cargada para que el sidebar se
        # vea completo. Si no hay 3 con imagen, completamos con las demas
        # (renderizan con placeholder).
        destacadas_qs = (
            Noticia.objects
            .filter(activo=True, destacado=True)
            .order_by('-fecha', '-fecha_creacion')
        )
        con_imagen = list(destacadas_qs.exclude(imagen='')[:3])
        if len(con_imagen) < 3:
            faltan = 3 - len(con_imagen)
            ids_ya = {n.id for n in con_imagen}
            extras = list(destacadas_qs.exclude(id__in=ids_ya)[:faltan])
            noticias_destacadas = con_imagen + extras
        else:
            noticias_destacadas = con_imagen
    except (OperationalError, ProgrammingError):
        infodinapi = None
        noticias_destacadas = []

    return {
        'sidebar_infodinapi': infodinapi,
        'sidebar_noticias_destacadas': noticias_destacadas,
    }
