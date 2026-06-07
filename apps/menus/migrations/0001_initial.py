from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='MenuDerecho',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.IntegerField(blank=True, null=True, unique=True)),
                ('titulo', models.CharField(max_length=255)),
                ('link_interno', models.IntegerField(default=0)),
                ('link_interno_url', models.CharField(blank=True, max_length=255)),
                ('link_externo', models.CharField(blank=True, max_length=255)),
                ('destacado', models.BooleanField(default=False)),
                ('padre', models.BooleanField(default=False)),
                ('hijo', models.BooleanField(default=False)),
                ('fecha_ordenamiento', models.DateField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Menu derecho',
                'verbose_name_plural': 'Items menu derecho',
                'ordering': ['-fecha_ordenamiento', '-creado_en'],
            },
        ),
        migrations.CreateModel(
            name='Popup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.IntegerField(blank=True, null=True, unique=True)),
                ('titulo', models.CharField(blank=True, max_length=255)),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('url_video', models.CharField(blank=True, max_length=255)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='imagenes-popup/')),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Popup',
                'verbose_name_plural': 'Popups',
                'ordering': ['-actualizado_en', '-creado_en'],
            },
        ),
    ]
