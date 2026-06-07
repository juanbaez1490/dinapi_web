from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_siteconfig_url_campos_temaeje'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarouselItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Título')),
                ('subtitulo', models.CharField(blank=True, max_length=500, verbose_name='Subtítulo')),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='home/carousel/%Y/%m/', verbose_name='Imagen de fondo')),
                ('url', models.URLField(blank=True, max_length=500, verbose_name='URL del botón CTA')),
                ('texto_boton', models.CharField(blank=True, default='Ver más', max_length=100, verbose_name='Texto del botón')),
                ('activo', models.BooleanField(default=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Slide del Carousel',
                'verbose_name_plural': 'Carousel (slides)',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Anuncio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Título')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='home/anuncios/%Y/%m/', verbose_name='Imagen')),
                ('url', models.URLField(blank=True, max_length=500, verbose_name='URL (CTA)')),
                ('fecha_inicio', models.DateField(blank=True, help_text='Dejar vacío = siempre visible.', null=True, verbose_name='Visible desde')),
                ('fecha_fin', models.DateField(blank=True, help_text='Dejar vacío = sin vencimiento.', null=True, verbose_name='Visible hasta')),
                ('activo', models.BooleanField(default=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Anuncio',
                'verbose_name_plural': 'Anuncios',
                'ordering': ['orden', '-fecha_inicio', 'id'],
            },
        ),
        migrations.CreateModel(
            name='EnlaceInteres',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Título')),
                ('descripcion', models.CharField(blank=True, max_length=500, verbose_name='Descripción corta')),
                ('url', models.URLField(max_length=500, verbose_name='URL')),
                ('icono', models.CharField(blank=True, help_text='Clase CSS Bootstrap Icons, p. ej. bi-shield-check', max_length=100, verbose_name='Clase de ícono')),
                ('activo', models.BooleanField(default=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Enlace de Interés',
                'verbose_name_plural': 'Enlaces de Interés',
                'ordering': ['orden', 'id'],
            },
        ),
    ]
