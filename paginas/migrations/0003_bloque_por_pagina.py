from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paginas', '0002_sembrar_portada'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloqueportada',
            name='pagina',
            field=models.SlugField(default='inicio', max_length=40),
        ),
        migrations.RemoveConstraint(
            model_name='bloqueportada',
            name='paginas_bloque_clave_estado',
        ),
        migrations.AddConstraint(
            model_name='bloqueportada',
            constraint=models.UniqueConstraint(
                fields=('pagina', 'clave', 'estado'),
                name='paginas_bloque_pagina_clave_estado',
            ),
        ),
    ]
