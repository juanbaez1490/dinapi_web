from django.db import models


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
