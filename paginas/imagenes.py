"""Archivos de las fotos de la portada.

La dirección nueva se guarda en el bloque (borrador o publicado). La portada
pública solo la muestra cuando el bloque publicado apunta a ella.
"""

import re
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image, UnidentifiedImageError

# Una imagen enorme declarada en pocos bytes no debe tumbar el editor.
_ERRORES_IMAGEN = (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError)

MAX_IMAGEN = 2 * 1024 * 1024
MENSAJE_TIPO = 'el archivo no es una imagen JPG, PNG, GIF o WEBP.'
MENSAJE_PESO = 'la imagen pesa más de 2 MB. Elige un archivo más liviano.'

_FORMATOS = {
    'JPEG': '.jpg',
    'PNG': '.png',
    'GIF': '.gif',
    'WEBP': '.webp',
}
_NOMBRE = re.compile(r'^portada/[0-9a-f]{32}\.(jpg|png|gif|webp)$')


def archivo_util(archivo):
    """Un input vacío no es un cambio: se conserva la imagen que ya había."""
    return archivo is not None and getattr(archivo, 'size', 0) > 0


def validar_subida(archivo):
    """None si se puede guardar; si no, la frase que va junto al campo."""
    if archivo.size > MAX_IMAGEN:
        return MENSAJE_PESO
    if _formato(archivo) is None:
        return MENSAJE_TIPO
    return None


def almacenar(archivo):
    """Copia el archivo ya validado y devuelve su dirección dentro del sitio."""
    formato = _formato(archivo)
    if formato is None:
        raise ValueError('La imagen no superó la validación.')
    nombre = f'portada/{uuid.uuid4().hex}{_FORMATOS[formato]}'
    archivo.seek(0)
    ruta = default_storage.save(nombre, archivo)
    return default_storage.url(ruta)


def enlaces_subidos(estado):
    """Direcciones de fotos subidas en ese estado. Las de fábrica no entran."""
    from paginas.models import BloquePortada

    return [
        enlace
        for enlace in BloquePortada.objects.filter(estado=estado).values_list('enlace', flat=True)
        if _ruta_propia(enlace) is not None
    ]


def olvidar(urls):
    """Borra fotos subidas que ya no usa ningún bloque. No toca estáticos ni URLs externas."""
    if not urls:
        return
    from paginas.models import BloquePortada

    en_uso = set(BloquePortada.objects.values_list('enlace', flat=True))
    for url in urls:
        if url in en_uso:
            continue
        ruta = _ruta_propia(url)
        if ruta is not None and ruta.is_file():
            ruta.unlink()


def _formato(archivo):
    archivo.seek(0)
    formato = None
    try:
        with Image.open(archivo) as imagen:
            # verify no deja la imagen reutilizable; solo nos importa el formato.
            imagen.verify()
            formato = imagen.format
    except _ERRORES_IMAGEN:
        formato = None
    finally:
        archivo.seek(0)
    if formato not in _FORMATOS:
        return None
    return formato


def _ruta_propia(url):
    if not isinstance(url, str) or not url.startswith(settings.MEDIA_URL):
        return None
    relativo = url[len(settings.MEDIA_URL):].split('?', 1)[0].lstrip('/')
    if _NOMBRE.fullmatch(relativo) is None:
        return None
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / relativo).resolve()
    try:
        ruta.relative_to((raiz / 'portada').resolve())
    except ValueError:
        return None
    return ruta
