from django.db import models


class MenuPrincipal(models.Model):
	"""
	Items del navbar principal (lado izquierdo).
	A diferencia del menu auto-construido desde core.Pagina jerarquica, este es
	un menu CURADO que reproduce exactamente la estructura del legacy DINAPI.

	Estructura: items con padre opcional (FK self). Si padre IS NULL es item
	de primer nivel. Si tiene padre, aparece como sub-item del desplegable.

	URLs: se resuelven en orden:
	  1. Si link_externo esta seteado -> usarlo.
	  2. Si pagina_destino_legacy_id apunta a una Pagina activa -> resolver.
	  3. Si link_interno_url esta seteado -> usarlo tal cual.
	  4. Fallback: '#'.
	"""
	titulo = models.CharField(max_length=255)
	padre = models.ForeignKey(
		'self', null=True, blank=True,
		on_delete=models.CASCADE, related_name='hijos',
		help_text='Si tiene padre, este item aparece como sub-item del desplegable.',
	)
	orden = models.PositiveIntegerField(
		default=0, help_text='Menor numero = aparece primero.',
	)
	pagina_destino_legacy_id = models.PositiveIntegerField(
		null=True, blank=True,
		help_text='legacy_id de la Pagina destino (resuelve la URL dinamicamente).',
	)
	link_interno_url = models.CharField(
		max_length=500, blank=True, default='',
		help_text='URL interna explicita (alternativa a pagina_destino_legacy_id).',
	)
	link_externo = models.CharField(
		max_length=500, blank=True, default='',
		help_text='URL externa absoluta. Si esta poblada, prevalece sobre las internas.',
	)
	target_blank = models.BooleanField(
		default=False,
		help_text='Abrir en pestana nueva. Recomendado para link externo.',
	)
	activo = models.BooleanField(default=True)

	class Meta:
		verbose_name = 'Item del menu principal'
		verbose_name_plural = 'Menu principal (curado)'
		ordering = ['orden', 'id']

	def __str__(self):
		prefijo = '  └ ' if self.padre_id else ''
		return f'{prefijo}{self.titulo}'


class MenuDerecho(models.Model):
	"""Equivalente Django de MenuDerecho en SilverStripe."""

	legacy_id = models.IntegerField(unique=True, null=True, blank=True)
	titulo = models.CharField(max_length=255)
	link_interno = models.IntegerField(default=0)
	link_interno_url = models.CharField(max_length=255, blank=True)
	link_externo = models.CharField(max_length=255, blank=True)
	destacado = models.BooleanField(default=False)
	padre = models.BooleanField(default=False)
	hijo = models.BooleanField(default=False)
	fecha_ordenamiento = models.DateField(null=True, blank=True)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Menu derecho'
		verbose_name_plural = 'Items menu derecho'
		ordering = ['-fecha_ordenamiento', '-creado_en']

	def __str__(self):
		return self.titulo

	@property
	def url_resuelta(self) -> str:
		if self.link_externo:
			return self.link_externo
		return self.link_interno_url or '#'


class Popup(models.Model):
	"""Popup informativo que puede mostrarse en la navegacion global."""

	legacy_id = models.IntegerField(unique=True, null=True, blank=True)
	titulo = models.CharField(max_length=255, blank=True)
	descripcion = models.CharField(max_length=255, blank=True)
	url_video = models.CharField(max_length=255, blank=True)
	imagen = models.ImageField(upload_to='imagenes-popup/', null=True, blank=True)
	activo = models.BooleanField(default=True)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'Popup'
		verbose_name_plural = 'Popups'
		ordering = ['-actualizado_en', '-creado_en']

	def __str__(self):
		return self.titulo or f'Popup #{self.pk}'
