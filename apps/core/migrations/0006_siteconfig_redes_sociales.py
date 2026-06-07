from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_anuncio_carouselitem_enlaceinteres'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfig',
            name='url_facebook',
            field=models.URLField(blank=True, default='', max_length=300, verbose_name='Facebook'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='url_instagram',
            field=models.URLField(blank=True, default='', max_length=300, verbose_name='Instagram'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='url_youtube',
            field=models.URLField(blank=True, default='', max_length=300, verbose_name='YouTube'),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='url_twitter',
            field=models.URLField(blank=True, default='', max_length=300, verbose_name='X / Twitter'),
        ),
    ]
