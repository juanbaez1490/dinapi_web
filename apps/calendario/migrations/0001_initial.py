from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Actividad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='Título')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_inicio', models.DateTimeField(verbose_name='Fecha y hora de inicio')),
                ('fecha_fin', models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora de fin')),
                ('lugar', models.CharField(blank=True, max_length=255, verbose_name='Lugar')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Actividad',
                'verbose_name_plural': 'Actividades',
                'ordering': ['fecha_inicio'],
            },
        ),
        migrations.AddIndex(
            model_name='actividad',
            index=models.Index(fields=['fecha_inicio'], name='calendario__fecha_i_idx'),
        ),
        migrations.AddIndex(
            model_name='actividad',
            index=models.Index(fields=['activo'], name='calendario__activo_idx'),
        ),
    ]
