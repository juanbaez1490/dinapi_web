"""
Migración 0004: agrega url_horarios y url_consultas a SiteConfig, y crea el modelo TemaEje.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_pagina_legacy_id_pagina_parent_legacy_id_and_more'),
    ]

    operations = [
        # ── SiteConfig: nuevos campos de URL ─────────────────────────────────
        migrations.AddField(
            model_name='siteconfig',
            name='url_horarios',
            field=models.URLField(
                blank=True,
                default='',
                help_text='URL de la página de horarios de atención (puede ser interna o externa).',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='url_consultas',
            field=models.URLField(
                blank=True,
                default='',
                help_text='URL del formulario de consultas/reclamos. Si se deja vacío se usa la vista interna.',
                max_length=500,
            ),
        ),

        # ── TemaEje ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='TemaEje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('eje', models.PositiveSmallIntegerField(
                    choices=[(1, 'Propiedad Industrial'), (2, 'Derecho de Autor y Derechos Conexos'), (3, 'Observancia')],
                )),
                ('url_externa', models.URLField(
                    blank=True,
                    default='',
                    help_text='URL externa de respaldo si no hay página interna asignada.',
                    max_length=500,
                )),
                ('legacy_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('pagina', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='temas_eje',
                    to='core.pagina',
                    help_text='Página interna a la que apunta este ítem.',
                )),
            ],
            options={
                'verbose_name': 'Tema Eje',
                'verbose_name_plural': 'Temas Eje',
                'ordering': ['eje', 'orden', 'nombre'],
            },
        ),
    ]
