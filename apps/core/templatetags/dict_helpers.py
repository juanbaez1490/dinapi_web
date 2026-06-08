"""Filtros simples para acceder a dicts en templates Django."""
from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Devuelve d[key] de forma segura. Si no esta, devuelve None."""
    if d is None:
        return None
    try:
        return d.get(key)
    except (AttributeError, TypeError):
        return None
