from django.db import models


class TarjetaPage(models.Model):
	legacy_id = models.PositiveIntegerField(unique=True)
	titulo = models.CharField(max_length=255, blank=True)
	imagen = models.ImageField(upload_to='tarjetas/paginas/', null=True, blank=True)

	class Meta:
		verbose_name = 'Pagina de Tarjetas'
		verbose_name_plural = 'Paginas de Tarjetas'
		ordering = ['legacy_id']

	def __str__(self):
		return self.titulo or f'TarjetaPage #{self.legacy_id}'


class Tarjeta(models.Model):
	legacy_id = models.PositiveIntegerField(unique=True)
	pagina = models.ForeignKey(
		TarjetaPage,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='tarjetas',
	)
	titulo = models.CharField(max_length=255)
	subtitulo = models.CharField(max_length=255, blank=True)
	link_interno = models.PositiveIntegerField(null=True, blank=True)
	link_interno_url = models.CharField(max_length=500, blank=True)
	link_externo = models.CharField(max_length=500, blank=True)
	fecha = models.DateField(null=True, blank=True)
	imagen = models.ImageField(upload_to='tarjetas/imagenes/', null=True, blank=True)

	class Meta:
		verbose_name = 'Tarjeta'
		verbose_name_plural = 'Tarjetas'
		ordering = ['-fecha', '-legacy_id']

	def __str__(self):
		return self.titulo

	@property
	def enlace_resuelto(self):
		if self.link_externo:
			return self.link_externo
		return self.link_interno_url


class AcordeonPage(models.Model):
	legacy_id = models.PositiveIntegerField(unique=True)
	titulo_padre = models.CharField(max_length=350, blank=True)
	titulo_anexo = models.CharField(max_length=350, blank=True)
	contenido_superior = models.TextField(blank=True)
	contenido_inferior = models.TextField(blank=True)
	imagen = models.ImageField(upload_to='acordeon/imagenes-pagina/', null=True, blank=True)
	anexo = models.FileField(upload_to='acordeon/archivos-anexos/', null=True, blank=True)

	class Meta:
		verbose_name = 'Pagina de Acordeon'
		verbose_name_plural = 'Paginas de Acordeon'
		ordering = ['legacy_id']

	def __str__(self):
		return self.titulo_padre or f'AcordeonPage #{self.legacy_id}'


class AcordeonItem(models.Model):
	legacy_id = models.PositiveIntegerField(unique=True)
	pagina = models.ForeignKey(
		AcordeonPage,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='desplegables',
	)
	titulo = models.CharField(max_length=350)
	contenido = models.TextField(blank=True)
	titulo_adjunto = models.CharField(max_length=350, blank=True)
	adjunto = models.FileField(upload_to='acordeon/archivos-adjuntos/', null=True, blank=True)
	fecha_ordenamiento = models.DateField(null=True, blank=True)

	class Meta:
		verbose_name = 'Item de Acordeon'
		verbose_name_plural = 'Items de Acordeon'
		ordering = ['-fecha_ordenamiento', '-legacy_id']

	def __str__(self):
		return self.titulo
