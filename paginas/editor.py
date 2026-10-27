"""Pantalla del editor de páginas, dentro del admin.

Inicio, Investigación, Profesionales, Servicios, Bases de datos y Contacto
comparten esta pantalla. Cada una guarda su propio borrador.
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from paginas.contenido import (
    contexto_lienzo,
    descartar_borrador,
    estado_guardado,
    grupos_editor,
    guardar_borrador,
    hay_borrador,
    leer_valores,
    primer_grupo_con_error,
    publicar,
    resolver_orden,
)
from paginas.imagenes import MAX_IMAGEN
from paginas.registro import obtener


def editor_inicio(request):
    return editor_pagina(request, 'inicio')


def editor_pagina(request, pagina):
    definicion = _definicion(pagina)
    _exigir_staff(request)
    if request.method == 'POST':
        return _responder(request, definicion)
    return _pintar(request, definicion)


def _responder(request, definicion):
    accion = request.POST.get('accion')
    destino = definicion.url_editor()
    if accion == 'descartar':
        descartar_borrador(definicion.slug)
        messages.success(request, definicion.aviso_descartado)
        return redirect(destino)
    if accion in ('guardar', 'publicar'):
        formulario = leer_valores(request.POST, request.FILES, definicion.slug)
        if formulario.errores:
            for error in formulario.errores:
                messages.error(request, error)
            return _pintar(
                request,
                definicion,
                formulario.valores,
                formulario.orden,
                pendiente=True,
                errores_campo=formulario.por_campo,
            )
        if accion == 'guardar':
            guardar_borrador(
                formulario.valores, formulario.orden, formulario.imagenes, definicion.slug,
            )
            messages.success(request, definicion.aviso_guardado)
        else:
            publicar(
                formulario.valores, formulario.orden, formulario.imagenes, definicion.slug,
            )
            messages.success(request, definicion.aviso_publicado)
        return redirect(destino)
    messages.error(request, 'No se reconoció la acción.')
    return redirect(destino)


def _pintar(request, definicion, valores=None, orden=None, pendiente=False, errores_campo=None):
    if orden is None:
        orden = list(resolver_orden(preferir_borrador=True, pagina=definicion.slug))
    grupos = grupos_editor(valores, orden, errores_campo, definicion.slug)
    grupo_inicial = _grupo_abierto(definicion, errores_campo, orden)
    enlace = None
    if definicion.enlace_relacionado:
        enlace = {
            'url': reverse(definicion.enlace_relacionado['nombre']),
            'texto': definicion.enlace_relacionado['texto'],
            'nota': definicion.enlace_relacionado['nota'],
        }
    context = admin.site.each_context(request)
    context.update({
        'title': definicion.titulo,
        'nombre': definicion.nombre,
        'grupos': grupos,
        'hay_borrador': hay_borrador(definicion.slug),
        'lienzo_url': definicion.url_lienzo(),
        'editor_url': definicion.url_editor(),
        'pendiente': pendiente,
        'orden_secciones': ','.join(orden),
        'grupo_inicial': grupo_inicial,
        'grupo_inicial_nombre': definicion.nombres[grupo_inicial],
        'estado_guardado': estado_guardado(definicion.slug),
        'error_orden': (errores_campo or {}).get('orden', ''),
        'max_imagen': MAX_IMAGEN,
        'hay_orden': bool(definicion.secciones),
        'hay_vistas': definicion.hay_vistas,
        'tiene_lista': any(grupo['zona'] in ('antes', 'lista') for grupo in grupos),
        'tiene_despues': any(grupo['zona'] == 'despues' for grupo in grupos),
        'ayuda': definicion.ayuda,
        'estado_borrador': definicion.estado_borrador,
        'estado_limpio': definicion.estado_limpio,
        'enlace_relacionado': enlace,
    })
    respuesta = render(request, 'admin/paginas/editor_inicio.html', context)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


@xframe_options_sameorigin
def lienzo_inicio(request):
    return lienzo_pagina(request, 'inicio')


@xframe_options_sameorigin
def lienzo_pagina(request, pagina):
    """La plantilla real con el borrador de esa página. Solo se abre dentro del editor."""
    definicion = _definicion(pagina)
    _exigir_staff(request)
    respuesta = render(
        request,
        definicion.plantilla,
        contexto_lienzo(definicion.slug, request),
    )
    respuesta['Cache-Control'] = 'no-store'
    respuesta['X-Robots-Tag'] = 'noindex, nofollow'
    return respuesta


def _definicion(pagina):
    definicion = obtener(pagina)
    if definicion is None:
        raise Http404
    return definicion


def _grupo_abierto(definicion, errores, orden):
    encontrado = primer_grupo_con_error(errores, definicion.slug)
    if encontrado:
        return encontrado
    if orden:
        return orden[0]
    return definicion.grupos[0][0]


def _exigir_staff(request):
    usuario = request.user
    if not usuario.is_authenticated or not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied
