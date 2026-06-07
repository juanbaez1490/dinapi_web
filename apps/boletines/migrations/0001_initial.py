from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PeriodoBoletin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField(unique=True)),
                ('titulo', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('tipo', models.CharField(choices=[('general', 'General (Patentes / Diseño Industrial)'), ('marca', 'Marca')], max_length=20)),
                ('padre_legacy_id', models.PositiveIntegerField(blank=True, help_text='ID del SiteTree padre (BoletinPage o BoletinMarcaPage)', null=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('legacy_created', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Periodo de Boletin',
                'verbose_name_plural': 'Periodos de Boletines',
                'ordering': ['-legacy_created', '-legacy_id'],
            },
        ),
        migrations.CreateModel(
            name='Boletin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legacy_id', models.PositiveIntegerField()),
                ('tipo', models.CharField(
                    choices=[
                        ('general', 'General (Patentes / Diseño Industrial)'),
                        ('acto_juridico', 'Acto Juridico'),
                        ('logotipo', 'Logotipo de Marca'),
                        ('marcas_documentos', 'Marcas y Documentos'),
                        ('movimiento_admin', 'Movimiento Administrativo'),
                    ],
                    max_length=30,
                )),
                ('titulo', models.CharField(max_length=255)),
                ('fecha', models.DateField(blank=True, null=True)),
                ('pdf', models.FileField(blank=True, null=True, upload_to='boletines/pdf/')),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='boletines/imagenes/')),
                ('legacy_created', models.DateTimeField(blank=True, null=True)),
                ('periodo', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='boletines',
                    to='boletines.periodoboletin',
                )),
            ],
            options={
                'verbose_name': 'Boletin',
                'verbose_name_plural': 'Boletines',
                'ordering': ['-fecha', '-legacy_id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='boletin',
            unique_together={('legacy_id', 'tipo')},
        ),
    ]
