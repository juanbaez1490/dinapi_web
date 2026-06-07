from django.db import migrations, models
import apps.reclamos.models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Reclamo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255, verbose_name='Nombre completo')),
                ('email', models.EmailField(max_length=254, verbose_name='Correo electronico')),
                ('telefono', models.CharField(blank=True, max_length=50, verbose_name='Telefono')),
                ('expediente', models.CharField(blank=True, max_length=255, verbose_name='N. de expediente')),
                ('tema', models.CharField(
                    choices=[
                        ('marcas', 'Marcas'),
                        ('patentes', 'Patentes'),
                        ('dibujos_modelos', 'Dibujos y Modelos Industriales'),
                        ('derecho_autor', 'Derecho de Autor y Derechos Conexos'),
                        ('observancia', 'Observancia'),
                        ('igdo', 'Indicaciones Geograficas y Denominaciones de Origen'),
                        ('conocimientos_trad', 'Conocimientos Tradicionales'),
                        ('gestiones_admin', 'Gestiones Administrativas'),
                        ('mediacion', 'Mediacion y Conciliacion'),
                        ('otro', 'Otro'),
                    ],
                    max_length=50,
                    verbose_name='Tema',
                )),
                ('descripcion', models.TextField(verbose_name='Descripcion del reclamo')),
                ('adjunto', models.FileField(
                    blank=True,
                    help_text='Solo archivos PDF. Maximo recomendado: 10 MB.',
                    null=True,
                    upload_to='reclamos/adjuntos/%Y/%m/',
                    validators=[apps.reclamos.models._validar_pdf],
                    verbose_name='Adjunto (PDF)',
                )),
                ('fecha_envio', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de envio')),
                ('estado', models.CharField(
                    choices=[
                        ('recibido', 'Recibido'),
                        ('en_proceso', 'En proceso'),
                        ('resuelto', 'Resuelto'),
                        ('cerrado', 'Cerrado'),
                    ],
                    default='recibido',
                    max_length=20,
                    verbose_name='Estado',
                )),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Reclamo',
                'verbose_name_plural': 'Reclamos',
                'ordering': ['-fecha_envio'],
            },
        ),
        migrations.AddIndex(
            model_name='reclamo',
            index=models.Index(fields=['-fecha_envio'], name='reclamos_re_fecha_e_idx'),
        ),
        migrations.AddIndex(
            model_name='reclamo',
            index=models.Index(fields=['estado'], name='reclamos_re_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='reclamo',
            index=models.Index(fields=['tema'], name='reclamos_re_tema_idx'),
        ),
    ]
