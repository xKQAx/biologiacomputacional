"""Copias de lo que se publicó.

No es otro borrador: cada Publicar guarda las filas que quedaron publicadas.
Restaurar las copia al estado borrador. La página pública sigue igual hasta
un Publicar nuevo. Descartar no borra estas copias.
"""

import re

from django.db import transaction
from django.utils import timezone

from paginas.models import BloquePortada, HistorialPagina

_CLAVE = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
_MAX_ENLACE = 500


def archivar(pagina, usuario):
    """Guarda quién publicó, cuándo y el contenido que quedó visible."""
    filas = BloquePortada.objects.filter(
        pagina=pagina, estado=BloquePortada.Estado.PUBLICADO,
    ).order_by('orden', 'clave')
    HistorialPagina.objects.create(
        pagina=pagina,
        autor=usuario if getattr(usuario, 'is_authenticated', False) else None,
        contenido=[
            {
                'clave': fila.clave,
                'texto': fila.texto,
                'enlace': fila.enlace,
                'orden': fila.orden,
            }
            for fila in filas
        ],
    )


def restaurar(pagina, historial_id):
    """Copia esa publicación al borrador. No toca lo publicado ni el historial."""
    historial = HistorialPagina.objects.filter(pagina=pagina, pk=historial_id).first()
    if historial is None:
        return False
    filas = _filas_validas(historial.contenido)
    if filas is None:
        return False
    from paginas.imagenes import enlaces_subidos, olvidar

    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    with transaction.atomic():
        BloquePortada.objects.filter(
            pagina=pagina, estado=BloquePortada.Estado.BORRADOR,
        ).delete()
        BloquePortada.objects.bulk_create([
            BloquePortada(
                pagina=pagina,
                clave=fila['clave'],
                texto=fila['texto'],
                enlace=fila['enlace'],
                orden=fila['orden'],
                estado=BloquePortada.Estado.BORRADOR,
            )
            for fila in filas
        ])
    olvidar(anteriores)
    return True


def listar(pagina, limite=30):
    """Las copias de esta página, de la más reciente a la más antigua."""
    consulta = HistorialPagina.objects.filter(pagina=pagina).select_related('autor')
    publicaciones = []
    for fila in consulta[:limite]:
        publicaciones.append({
            'id': fila.pk,
            'cuando': timezone.localtime(fila.fecha).strftime('%d/%m/%Y %H:%M'),
            'autor': _autor(fila.autor),
        })
    return publicaciones


def enlaces_guardados():
    """Direcciones que una copia publicada todavía menciona."""
    urls = set()
    for contenido in HistorialPagina.objects.values_list('contenido', flat=True):
        if not isinstance(contenido, list):
            continue
        for fila in contenido:
            enlace = fila.get('enlace') if isinstance(fila, dict) else None
            if isinstance(enlace, str) and enlace:
                urls.add(enlace)
    return urls


def _autor(usuario):
    if usuario is None:
        return 'Alguien del equipo'
    return usuario.get_full_name() or usuario.get_username()


def _filas_validas(contenido):
    if not isinstance(contenido, list) or not contenido:
        return None
    vistas = set()
    filas = []
    for item in contenido:
        if not isinstance(item, dict):
            return None
        clave = item.get('clave')
        texto = item.get('texto')
        enlace = item.get('enlace', '')
        orden = item.get('orden', 0)
        if not isinstance(clave, str) or _CLAVE.fullmatch(clave) is None or clave in vistas:
            return None
        if not isinstance(texto, str) or not isinstance(enlace, str) or len(enlace) > _MAX_ENLACE:
            return None
        if isinstance(orden, bool) or not isinstance(orden, int) or orden < 0:
            return None
        vistas.add(clave)
        filas.append({
            'clave': clave,
            'texto': texto,
            'enlace': enlace,
            'orden': orden,
        })
    return filas
