"""Carrusel de Investigación: lo publicado y su borrador.

La portada solo lee el modelo Carrusel. El borrador se previsualiza aparte
y pasa a la portada al publicar. Descartarlo no toca lo publicado.

Siguiente paso del panel: crear secciones nuevas. Este módulo no lo hace.
"""

import os

from django.core.files.base import ContentFile
from django.db import transaction

from investigacion.models import Carrusel, CarruselBorrador

CAMPOS_TEXTO = ('titulo', 'texto1', 'texto2', 'texto3')
CAMPOS_IMAGEN = ('imagen1', 'imagen2', 'imagen3')


def imagen_disponible(campo):
    """True solo si el archivo está guardado y sigue en disco."""
    nombre = getattr(campo, 'name', '') or ''
    if not nombre:
        return False
    try:
        return campo.storage.exists(nombre)
    except (OSError, ValueError):
        return False


def diapositivas_publicas(carrusel):
    """Diapositivas que se pueden pintar. Sin archivo, no entran."""
    if carrusel is None:
        return []

    pares = (
        (carrusel.imagen1, carrusel.texto1),
        (carrusel.imagen2, carrusel.texto2),
        (carrusel.imagen3, carrusel.texto3),
    )
    diapositivas = []
    for imagen, texto in pares:
        if not imagen_disponible(imagen):
            continue
        texto = (texto or '').strip()
        diapositivas.append({
            'url': imagen.url,
            'texto': texto,
            'alt': texto or 'Imagen de investigación del laboratorio',
        })

    if diapositivas:
        diapositivas[0]['titulo'] = (carrusel.titulo or '').strip()
    return diapositivas


def borrador_actual():
    return CarruselBorrador.objects.first()


def publicado_actual():
    return Carrusel.objects.first()


def url_imagen(borrador, publicado, campo):
    """La miniatura del editor: primero el borrador, si no lo publicado."""
    for fuente in (borrador, publicado):
        if fuente is None:
            continue
        archivo = getattr(fuente, campo)
        if imagen_disponible(archivo):
            return archivo.url
    return ''


def guardar_borrador(datos, borrador, publicado):
    """Guarda el borrador. Si no hay foto nueva, copia la ya publicada."""
    borrador = borrador or CarruselBorrador()
    for campo in CAMPOS_TEXTO:
        setattr(borrador, campo, datos.get(campo) or '')

    anteriores = []
    for campo in CAMPOS_IMAGEN:
        subida = datos.get(campo)
        if subida:
            anteriores.extend(_reemplazar(borrador, campo, subida.name, subida))
        elif not imagen_disponible(getattr(borrador, campo)):
            leido = _leer(getattr(publicado, campo) if publicado else None)
            if leido is not None:
                _reemplazar(borrador, campo, leido[0], ContentFile(leido[1]))

    for campo in CAMPOS_IMAGEN:
        if not imagen_disponible(getattr(borrador, campo)):
            raise ValueError('El borrador no tiene todas las imágenes.')

    borrador.save()
    _borrar_archivos(borrador.imagen1.storage, anteriores)
    return borrador


def publicar_borrador(borrador):
    """Copia el borrador a lo que ve el visitante y luego lo elimina.

    Las fotos se copian a archivos nuevos. Los archivos viejos se borran
    solo después de guardar, y nunca si el carrusel publicado aún los usa.
    """
    leidos = []
    for campo in CAMPOS_IMAGEN:
        leido = _leer(getattr(borrador, campo))
        if leido is None:
            raise ValueError('El borrador no tiene todas las imágenes.')
        leidos.append((campo, leido))

    nombres_borrador = _nombres_imagen(borrador)
    storage = borrador.imagen1.storage

    with transaction.atomic():
        publicado = publicado_actual() or Carrusel()
        for campo in CAMPOS_TEXTO:
            setattr(publicado, campo, getattr(borrador, campo))

        anteriores = []
        for campo, (nombre, contenido) in leidos:
            anteriores.extend(
                _reemplazar(publicado, campo, nombre, ContentFile(contenido))
            )
        publicado.save()
        borrador.delete()

    protegidos = _nombres_imagen(publicado)
    _borrar_archivos(storage, [n for n in anteriores if n not in protegidos])
    _borrar_archivos(storage, [n for n in nombres_borrador if n not in protegidos])
    return publicado


def descartar_borrador(borrador):
    """Borra el borrador y sus archivos. No modifica el carrusel publicado."""
    if borrador is None:
        return
    storage = borrador.imagen1.storage
    nombres = _nombres_imagen(borrador)
    borrador.delete()
    protegidos = _nombres_imagen(publicado_actual())
    _borrar_archivos(storage, [n for n in nombres if n not in protegidos])


def _nombres_imagen(instancia):
    if instancia is None:
        return []
    nombres = []
    for campo in CAMPOS_IMAGEN:
        archivo = getattr(instancia, campo, None)
        if archivo and archivo.name:
            nombres.append(archivo.name)
    return nombres


def _leer(campo):
    if not imagen_disponible(campo):
        return None
    nombre = os.path.basename(campo.name)
    with campo.open('rb') as archivo:
        return nombre, archivo.read()


def _reemplazar(instancia, nombre_campo, nombre_archivo, contenido):
    """Escribe el archivo nuevo y devuelve el nombre anterior, si cambió."""
    campo = getattr(instancia, nombre_campo)
    anterior = campo.name
    campo.save(nombre_archivo, contenido, save=False)
    if anterior and anterior != campo.name:
        return [anterior]
    return []


def _borrar_archivos(storage, nombres):
    for nombre in nombres:
        if nombre:
            storage.delete(nombre)
