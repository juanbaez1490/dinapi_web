import calendar
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Actividad


def calendario_view(request):
    """Vista principal del calendario. Carga el mes actual; el grid se refresca via AJAX."""
    hoy = timezone.localdate()
    year = int(request.GET.get('year', hoy.year))
    month = int(request.GET.get('month', hoy.month))

    # Validar rango
    year = max(2000, min(year, 2100))
    month = max(1, min(month, 12))

    actividades = _get_actividades(year, month)
    semanas = _build_semanas(year, month, actividades)

    prev_year, prev_month = _prev_month(year, month)
    next_year, next_month = _next_month(year, month)

    contexto = {
        'year': year,
        'month': month,
        'month_nombre': _MESES[month],
        'semanas': semanas,
        'actividades': actividades,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'hoy': hoy,
    }
    return render(request, 'calendario/index.html', contexto)


def actividades_json(request):
    """Endpoint AJAX: devuelve actividades de un mes como JSON."""
    hoy = timezone.localdate()
    try:
        year = int(request.GET.get('year', hoy.year))
        month = int(request.GET.get('month', hoy.month))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)

    year = max(2000, min(year, 2100))
    month = max(1, min(month, 12))

    actividades = _get_actividades(year, month)
    semanas = _build_semanas(year, month, actividades)

    prev_year, prev_month = _prev_month(year, month)
    next_year, next_month = _next_month(year, month)

    data = {
        'year': year,
        'month': month,
        'month_nombre': _MESES[month],
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'semanas': semanas,
        'actividades': [
            {
                'id': a.pk,
                'titulo': a.titulo,
                'descripcion': a.descripcion,
                'fecha_inicio': a.fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
                'fecha_fin': a.fecha_fin.strftime('%Y-%m-%dT%H:%M') if a.fecha_fin else None,
                'lugar': a.lugar,
                'dia': a.fecha_inicio.day,
            }
            for a in actividades
        ],
    }
    return JsonResponse(data)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

_MESES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}


def _get_actividades(year, month):
    return list(
        Actividad.objects.filter(
            activo=True,
            fecha_inicio__year=year,
            fecha_inicio__month=month,
        ).order_by('fecha_inicio')
    )


def _build_semanas(year, month, actividades):
    """
    Construye una lista de semanas, cada una con 7 días.
    Cada día es un dict: {'numero': int|None, 'actividades': [...]}.
    Días None = padding del mes anterior/posterior.
    """
    actividades_por_dia = {}
    for a in actividades:
        dia = a.fecha_inicio.day
        actividades_por_dia.setdefault(dia, []).append(a)

    cal = calendar.monthcalendar(year, month)  # semanas con 0 = día fuera del mes
    semanas = []
    for semana_raw in cal:
        semana = []
        for dia_num in semana_raw:
            if dia_num == 0:
                semana.append({'numero': None, 'actividades': []})
            else:
                semana.append({
                    'numero': dia_num,
                    'actividades': actividades_por_dia.get(dia_num, []),
                })
        semanas.append(semana)
    return semanas


def _prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1
