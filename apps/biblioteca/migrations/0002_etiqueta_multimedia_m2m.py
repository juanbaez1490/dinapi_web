from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0001_initial'),
    ]

    operations = [
        # 1. EtiquetaBiblioteca
        migrations.CreateModel(
            name='EtiquetaBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Etiqueta',
                'verbose_name_plural': 'Etiquetas',
                'ordering': ['nombre'],
            },
        ),
        # 2. VideoBiblioteca
        migrations.CreateModel(
            name='VideoBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=500, help_text='URL de embed o enlace directo al video.')),
                ('descripcion', models.TextField(blank=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Video',
                'verbose_name_plural': 'Videos',
                'ordering': ['orden', 'titulo'],
            },
        ),
        # 3. ImagenBiblioteca
        migrations.CreateModel(
            name='ImagenBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, max_length=255)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='biblioteca/imagenes/%Y/%m/')),
                ('url', models.URLField(blank=True, max_length=500, help_text='URL externa si la imagen no esta subida.')),
                ('descripcion', models.TextField(blank=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Imagen',
                'verbose_name_plural': 'Imagenes',
                'ordering': ['orden', 'titulo'],
            },
        ),
        # 4. DocumentoBiblioteca
        migrations.CreateModel(
            name='DocumentoBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('archivo', models.FileField(blank=True, null=True, upload_to='biblioteca/documentos/%Y/%m/')),
                ('url', models.URLField(blank=True, max_length=500, help_text='URL externa si el archivo no esta subido.')),
                ('descripcion', models.TextField(blank=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Documento',
                'verbose_name_plural': 'Documentos',
                'ordering': ['orden', 'titulo'],
            },
        ),
        # 5. M2M: Biblioteca.videos
        migrations.AddField(
            model_name='biblioteca',
            name='videos',
            field=models.ManyToManyField(
                blank=True,
                related_name='bibliotecas',
                to='biblioteca.videobiblioteca',
                verbose_name='Videos',
            ),
        ),
        # 6. M2M: Biblioteca.imagenes
        migrations.AddField(
            model_name='biblioteca',
            name='imagenes',
            field=models.ManyToManyField(
                blank=True,
                related_name='bibliotecas',
                to='biblioteca.imagenbiblioteca',
                verbose_name='Imagenes',
            ),
        ),
        # 7. M2M: Biblioteca.documentos
        migrations.AddField(
            model_name='biblioteca',
            name='documentos',
            field=models.ManyToManyField(
                blank=True,
                related_name='bibliotecas',
                to='biblioteca.documentobiblioteca',
                verbose_name='Documentos',
            ),
        ),
        # 8. M2M: Biblioteca.etiquetas
        migrations.AddField(
            model_name='biblioteca',
            name='etiquetas',
            field=models.ManyToManyField(
                blank=True,
                related_name='bibliotecas',
                to='biblioteca.etiquetabiblioteca',
                verbose_name='Etiquetas',
            ),
        ),
    ]
