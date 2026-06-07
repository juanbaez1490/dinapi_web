# Generated manually for SilverStripe page-type migration base

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pagina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('contenido', models.TextField(blank=True)),
                ('descripcion', models.CharField(blank=True, help_text='Para SEO', max_length=500)),
                ('imagen_principal', models.ImageField(blank=True, null=True, upload_to='paginas/')),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('fecha_publicacion', models.DateTimeField(blank=True, null=True)),
                ('tipo', models.CharField(choices=[('HomePage', 'Home'), ('GeneralPage', 'General'), ('InstitucionalPage', 'Institucional'), ('ContactPage', 'Contacto'), ('NoticiaPage', 'Noticias'), ('RevistaPage', 'Revista'), ('BibliotecaPage', 'Biblioteca'), ('ConcursosPage', 'Concursos'), ('ReclamosPage', 'Reclamos'), ('ArchivoPage', 'Archivos'), ('AcordeonPage', 'Acordeon'), ('TarjetaPage', 'Tarjetas'), ('TarjetaSimplePage', 'Tarjetas Simples'), ('CalendarioPage', 'Calendario'), ('BoletinPage', 'Boletin'), ('BoletinMarcaPage', 'Boletin Marca'), ('ProtegeLoTuyoPage', 'Protege lo Tuyo'), ('DiaPIPage', 'Dia PI'), ('CodepiNoticiaPage', 'Codepi Noticias'), ('GestorEnlacesPage', 'Gestor de Enlaces')], default='GeneralPage', max_length=80)),
                ('subtitulo', models.CharField(blank=True, max_length=255)),
                ('mostrar_en_menu', models.BooleanField(default=True)),
                ('orden_menu', models.PositiveIntegerField(default=0)),
                ('plantilla_personalizada', models.CharField(blank=True, help_text='Ruta de plantilla opcional, por ejemplo: core/home.html', max_length=255)),
            ],
            options={
                'verbose_name': 'Pagina',
                'verbose_name_plural': 'Paginas',
                'ordering': ['orden_menu', 'titulo'],
            },
        ),
    ]
