# Generated manually for Biblioteca migration from SilverStripe

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CategoriaBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255, unique=True)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('color', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'verbose_name': 'Categoria de Biblioteca',
                'verbose_name_plural': 'Categorias de Biblioteca',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Biblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('descripcion', models.TextField(blank=True)),
                ('descripcion_videos', models.CharField(blank=True, max_length=500)),
                ('descripcion_imagenes', models.CharField(blank=True, max_length=500)),
                ('descripcion_documentos', models.CharField(blank=True, max_length=500)),
                ('enlaces_referencias', models.TextField(blank=True)),
                ('imagen_principal', models.ImageField(blank=True, null=True, upload_to='biblioteca/imagenes-principales/')),
                ('fecha_ordenamiento', models.DateField(blank=True, null=True)),
                ('ocultar', models.BooleanField(default=False)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='biblioteca.categoriabiblioteca')),
            ],
            options={
                'verbose_name': 'Biblioteca',
                'verbose_name_plural': 'Biblioteca',
                'ordering': ['-fecha_ordenamiento', '-fecha_creacion'],
            },
        ),
    ]
