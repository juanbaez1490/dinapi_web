# Generated manually for SilverStripe migration support.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Concurso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('pagina_legacy_id', models.PositiveIntegerField(blank=True, null=True)),
                ('fecha', models.DateField(blank=True, null=True)),
                ('enlace', models.CharField(blank=True, max_length=1000)),
                ('imagen_corta', models.ImageField(blank=True, null=True, upload_to='concursos/miniaturas/')),
                ('imagen_completa', models.ImageField(blank=True, null=True, upload_to='concursos/detalle/')),
                ('legacy_created', models.DateTimeField(blank=True, null=True)),
                ('legacy_last_edited', models.DateTimeField(blank=True, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Concurso',
                'verbose_name_plural': 'Concursos',
                'ordering': ['-fecha', '-legacy_id'],
            },
        ),
    ]
