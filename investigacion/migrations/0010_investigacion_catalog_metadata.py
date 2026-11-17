import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investigacion', '0009_carrusel_borrador'),
    ]

    operations = [
        migrations.AddField(
            model_name='investigacion',
            name='anio',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1900),
                    django.core.validators.MaxValueValidator(2100),
                ],
                verbose_name='Año',
            ),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='organismo',
            field=models.CharField(blank=True, max_length=120, verbose_name='Organismo o sistema biológico'),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='metodos',
            field=models.CharField(blank=True, max_length=180, verbose_name='Métodos o técnicas'),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='palabras_clave',
            field=models.CharField(blank=True, max_length=250, verbose_name='Palabras clave'),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='publicacion_url',
            field=models.URLField(blank=True, verbose_name='Publicación'),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='datos_url',
            field=models.URLField(blank=True, verbose_name='Datos'),
        ),
        migrations.AddField(
            model_name='investigacion',
            name='codigo_url',
            field=models.URLField(blank=True, verbose_name='Código'),
        ),
    ]
