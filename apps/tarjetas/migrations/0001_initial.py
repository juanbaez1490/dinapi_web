from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AcordeonPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo_padre', models.CharField(blank=True, max_length=350)),
                ('titulo_anexo', models.CharField(blank=True, max_length=350)),
                ('contenido_superior', models.TextField(blank=True)),
                ('contenido_inferior', models.TextField(blank=True)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='acordeon/imagenes-pagina/')),
                ('anexo', models.FileField(blank=True, null=True, upload_to='acordeon/archivos-anexos/')),
            ],
            options={
                'verbose_name': 'Pagina de Acordeon',
                'verbose_name_plural': 'Paginas de Acordeon',
                'ordering': ['legacy_id'],
            },
        ),
        migrations.CreateModel(
            name='TarjetaPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo', models.CharField(blank=True, max_length=255)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='tarjetas/paginas/')),
            ],
            options={
                'verbose_name': 'Pagina de Tarjetas',
                'verbose_name_plural': 'Paginas de Tarjetas',
                'ordering': ['legacy_id'],
            },
        ),
        migrations.CreateModel(
            name='AcordeonItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo', models.CharField(max_length=350)),
                ('contenido', models.TextField(blank=True)),
                ('titulo_adjunto', models.CharField(blank=True, max_length=350)),
                ('adjunto', models.FileField(blank=True, null=True, upload_to='acordeon/archivos-adjuntos/')),
                ('fecha_ordenamiento', models.DateField(blank=True, null=True)),
                ('pagina', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='desplegables', to='tarjetas.acordeonpage')),
            ],
            options={
                'verbose_name': 'Item de Acordeon',
                'verbose_name_plural': 'Items de Acordeon',
                'ordering': ['-fecha_ordenamiento', '-legacy_id'],
            },
        ),
        migrations.CreateModel(
            name='Tarjeta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo', models.CharField(max_length=255)),
                ('subtitulo', models.CharField(blank=True, max_length=255)),
                ('link_interno', models.PositiveIntegerField(blank=True, null=True)),
                ('link_interno_url', models.CharField(blank=True, max_length=500)),
                ('link_externo', models.CharField(blank=True, max_length=500)),
                ('fecha', models.DateField(blank=True, null=True)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='tarjetas/imagenes/')),
                ('pagina', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tarjetas', to='tarjetas.tarjetapage')),
            ],
            options={
                'verbose_name': 'Tarjeta',
                'verbose_name_plural': 'Tarjetas',
                'ordering': ['-fecha', '-legacy_id'],
            },
        ),
    ]
