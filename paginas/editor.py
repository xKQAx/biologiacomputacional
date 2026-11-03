"""Pantalla del editor de páginas, dentro del admin.

Inicio, Investigación, Profesionales, Servicios, Bases de datos y Contacto
comparten esta pantalla. Cada una guarda su propio borrador.
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
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
from paginas.piezas import (
    es_estructural,
    mutar,
    pendientes_de_imagen,
    tipos_editor,
    tipos_internos,
)
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
    accion = request.POST.get('accion') or ''
    destino = definicion.url_editor()
    if accion == 'descartar':
        descartar_borrador(definicion.slug)
        messages.success(request, definicion.aviso_descartado)
        return redirect(destino)
    estructural = definicion.permite_piezas and es_estructural(accion)
    vivo = _pedido_vivo(request)
    if accion in ('guardar', 'publicar') or estructural:
        formulario = leer_valores(request.POST, request.FILES, definicion.slug)
        if formulario.errores:
            if vivo:
                return _json_aviso(formulario.errores[0])
            for error in formulario.errores:
                messages.error(request, error)
            return _pintar(
                request,
                definicion,
                formulario.valores,
                formulario.orden,
                pendiente=True,
                errores_campo=formulario.por_campo,
                composicion=formulario.composicion,
            )
        valores = formulario.valores
        orden = formulario.orden
        comp = formulario.composicion
        if estructural:
            comp_antes = comp
            comp, orden, valores, error = mutar(
                comp, orden, valores, accion, request.POST.get('tipo_pieza'),
            )
            if error:
                if vivo:
                    return _json_aviso(error)
                messages.error(request, error)
                return _pintar(
                    request, definicion, valores, orden,
                    pendiente=True, composicion=comp,
                )
            guardar_borrador(valores, orden, formulario.imagenes, definicion.slug, comp)
            if vivo:
                return _respuesta_viva(
                    request, definicion, valores, orden, comp, accion, comp_antes,
                )
            messages.success(request, _aviso_estructura(accion))
            return redirect(destino)
        if accion == 'publicar' and definicion.permite_piezas:
            pendientes = pendientes_de_imagen(comp, valores, formulario.imagenes)
            if pendientes:
                errores = dict(formulario.por_campo)
                for clave, mensaje in pendientes:
                    messages.error(request, mensaje)
                    errores.setdefault(clave, {})
                    errores[clave]['imagen'] = mensaje
                return _pintar(
                    request, definicion, valores, orden,
                    pendiente=True, errores_campo=errores, composicion=comp,
                )
        if accion == 'guardar':
            guardar_borrador(valores, orden, formulario.imagenes, definicion.slug, comp)
            messages.success(request, definicion.aviso_guardado)
        else:
            publicar(
                valores, orden, formulario.imagenes, definicion.slug, comp, request.user,
            )
            messages.success(request, definicion.aviso_publicado)
        return redirect(destino)
    if accion.startswith('restaurar:'):
        from paginas.historial import restaurar

        bruto = accion.split(':', 1)[1]
        if bruto.isdigit() and restaurar(definicion.slug, int(bruto)):
            messages.success(
                request,
                'Versión copiada al borrador. La página pública no cambió.',
            )
        else:
            messages.error(request, 'No se encontró esa publicación.')
        return redirect(destino)
    messages.error(request, 'No se reconoció la acción.')
    return redirect(destino)


def _pedido_vivo(request):
    """El editor pide JSON para no reemplazar la página ni perder el lugar."""
    return request.headers.get('X-Editor-Vivo') == '1'


def _json_aviso(aviso):
    respuesta = JsonResponse({'ok': False, 'aviso': aviso})
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


def _aviso_estructura(accion):
    if accion == 'agregar':
        return 'Sección agregada al borrador. La página pública no cambió.'
    if accion.startswith('ocultar:'):
        return 'Sección ocultada en el borrador. La página pública no cambió.'
    if accion.startswith('mostrar:'):
        return 'La sección vuelve a verse en el borrador. La página pública no cambió.'
    if accion.startswith('pieza-agregar:'):
        return 'Pieza agregada al borrador. La página pública no cambió.'
    if accion.startswith('pieza-quitar:'):
        return 'Pieza quitada del borrador. La página pública no cambió.'
    if accion.startswith('columnas:'):
        return 'Distribución guardada en el borrador. La página pública no cambió.'
    if accion.startswith('dia-agregar:'):
        return 'Diapositiva agregada al borrador. La página pública no cambió.'
    if accion.startswith('dia-quitar:'):
        return 'Diapositiva quitada del borrador. La página pública no cambió.'
    if accion.startswith(('dia-subir:', 'dia-bajar:')):
        return 'Orden de las diapositivas guardado en el borrador. La página pública no cambió.'
    return 'Sección quitada del borrador. La página pública no cambió.'


def _respuesta_viva(request, definicion, valores, orden, comp, accion, comp_antes):
    """Fragmentos del índice, del inspector y del lienzo. No es la página del editor."""
    seccion_id = _id_de_accion(accion, comp_antes, comp)
    quitar = accion.startswith('quitar:')
    pieza_abierta = _pieza_elegida(accion, comp)
    grupos = grupos_editor(valores, orden, None, definicion.slug, comp)
    grupo = next((item for item in grupos if item['id'] == seccion_id), None)
    html_item = ''
    html_campos = ''
    if grupo is not None and not quitar:
        html_item = render_to_string(
            'admin/paginas/editor_seccion_item.html',
            {'grupo': grupo, 'permite_piezas': definicion.permite_piezas},
            request=request,
        )
        html_campos = render_to_string(
            'admin/paginas/editor_inspector.html',
            {
                'grupo': grupo,
                'grupo_inicial': seccion_id,
                'tipos_internos': tipos_internos(),
                'pieza_abierta': pieza_abierta or '',
            },
            request=request,
        )
    datos = {
        'ok': True,
        'aviso': _aviso_estructura(accion),
        'id': seccion_id,
        'seleccionar': seccion_id if accion == 'agregar' else '',
        'quitar': quitar,
        'oculta': _esta_oculta(comp, seccion_id),
        'orden': list(orden),
        'html_item': html_item,
        'html_campos': html_campos,
        'html_lienzo': '' if quitar else _html_lienzo(request, definicion, seccion_id),
        'estado': estado_guardado(definicion.slug),
    }
    # Vacío al quitar una pieza: el inspector vuelve al contenido de la sección.
    if pieza_abierta is not None:
        datos['pieza'] = pieza_abierta
    respuesta = JsonResponse(datos)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


def _id_de_accion(accion, comp_antes, comp):
    if accion == 'agregar':
        conocidos = {pieza.id for pieza in comp_antes.piezas}
        for pieza in comp.piezas:
            if pieza.id not in conocidos:
                return pieza.id
        return ''
    partes = accion.split(':')
    return partes[1] if len(partes) > 1 else ''


def _pieza_elegida(accion, comp):
    """Id de la pieza interna que el inspector debe abrir. None si la acción no la toca."""
    if accion.startswith('pieza-quitar:'):
        return ''
    if not accion.startswith('pieza-agregar:'):
        return None
    partes = accion.split(':')
    if len(partes) < 2:
        return ''
    pieza = comp.por_id(partes[1])
    if pieza is not None and pieza.bloques:
        return pieza.bloques[-1].id
    return ''


def _esta_oculta(comp, seccion_id):
    if seccion_id in comp.ocultas:
        return True
    pieza = comp.por_id(seccion_id)
    if pieza is not None:
        return not pieza.visible
    return False


def _html_lienzo(request, definicion, seccion_id):
    contexto = contexto_lienzo(definicion.slug, request)
    for seccion in contexto['secciones']:
        if seccion.id != seccion_id:
            continue
        return render_to_string(
            seccion.plantilla,
            {**contexto, 'pieza': seccion},
            request=request,
        )
    return ''


def _pintar(
    request, definicion, valores=None, orden=None, pendiente=False,
    errores_campo=None, composicion=None,
):
    if orden is None:
        orden = list(resolver_orden(preferir_borrador=True, pagina=definicion.slug))
    grupos = grupos_editor(
        valores, orden, errores_campo, definicion.slug, composicion,
    )
    grupo_inicial = _grupo_abierto(definicion, errores_campo, orden)
    enlace = None
    if definicion.enlace_relacionado:
        enlace = {
            'url': reverse(definicion.enlace_relacionado['nombre']),
            'texto': definicion.enlace_relacionado['texto'],
            'nota': definicion.enlace_relacionado['nota'],
        }
    from paginas.historial import listar

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
        'grupo_inicial_nombre': _nombre_grupo(definicion, grupos, grupo_inicial),
        'permite_piezas': definicion.permite_piezas,
        'tipos_pieza': tipos_editor() if definicion.permite_piezas else (),
        'tipos_internos': tipos_internos() if definicion.permite_piezas else (),
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
        'publicaciones': listar(definicion.slug),
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


def _nombre_grupo(definicion, grupos, grupo_id):
    for grupo in grupos:
        if grupo['id'] == grupo_id:
            return grupo['nombre']
    return definicion.nombres.get(grupo_id, 'Propiedades')


def _exigir_staff(request):
    usuario = request.user
    if not usuario.is_authenticated or not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied
