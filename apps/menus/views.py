from django.shortcuts import render
from .models import MenuDerecho, Popup


def preview(request):
	padres = MenuDerecho.objects.filter(padre=True)
	hijos = MenuDerecho.objects.filter(hijo=True)
	enlaces_simples = MenuDerecho.objects.filter(padre=False, hijo=False)
	popup_activo = Popup.objects.filter(activo=True).first()

	return render(
		request,
		'menus/preview.html',
		{
			'padres': padres,
			'hijos': hijos,
			'enlaces_simples': enlaces_simples,
			'popup_activo': popup_activo,
		},
	)
