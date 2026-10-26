"""Siembra lo publicado con los textos que ya muestra la portada."""

from django.db import migrations


def sembrar(apps, schema_editor):
    Bloque = apps.get_model('paginas', 'BloquePortada')
    # El catálogo es la copia de la plantilla. Se lee al migrar para no
    # duplicar los textos en este archivo.
    from paginas.catalogo import CATALOGO, enlace_predeterminado

    for definicion in CATALOGO:
        Bloque.objects.update_or_create(
            clave=definicion.clave,
            estado='publicado',
            defaults={
                'texto': definicion.texto,
                'enlace': enlace_predeterminado(definicion),
                'orden': definicion.orden,
            },
        )


def quitar(apps, schema_editor):
    Bloque = apps.get_model('paginas', 'BloquePortada')
    Bloque.objects.filter(estado='publicado').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('paginas', '0001_bloques_portada'),
    ]

    operations = [
        migrations.RunPython(sembrar, quitar),
    ]
