"""Pantalla del editor de inicio, dentro del admin."""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from paginas.catalogo import NOMBRES_GRUPO
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


def editor_inicio(request):
    _exigir_staff(request)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'descartar':
            descartar_borrador()
            messages.success(
                request,
                'Borrador descartado. La portada publicada sigue igual.',
            )
            return redirect('admin:pagina_inicio')
        if accion in ('guardar', 'publicar'):
            formulario = leer_valores(request.POST, request.FILES)
            if formulario.errores:
                for error in formulario.errores:
                    messages.error(request, error)
                return _pintar(
                    request,
                    formulario.valores,
                    formulario.orden,
                    pendiente=True,
                    errores_campo=formulario.por_campo,
                )
            if accion == 'guardar':
                guardar_borrador(formulario.valores, formulario.orden, formulario.imagenes)
                messages.success(
                    request,
                    'Borrador guardado. La portada pública no cambió.',
                )
            else:
                publicar(formulario.valores, formulario.orden, formulario.imagenes)
                messages.success(
                    request,
                    'Página de inicio publicada. Los visitantes ya ven estos cambios.',
                )
            return redirect('admin:pagina_inicio')
        messages.error(request, 'No se reconoció la acción.')
        return redirect('admin:pagina_inicio')

    return _pintar(request)


def _pintar(request, valores=None, orden=None, pendiente=False, errores_campo=None):
    if orden is None:
        orden = resolver_orden(preferir_borrador=True)
    grupo_inicial = primer_grupo_con_error(errores_campo) or orden[0]
    context = admin.site.each_context(request)
    context.update({
        'title': 'Editar página de inicio',
        'grupos': grupos_editor(valores, orden, errores_campo),
        'hay_borrador': hay_borrador(),
        'lienzo_url': reverse('admin:pagina_inicio_lienzo'),
        'pendiente': pendiente,
        'orden_secciones': ','.join(orden),
        'grupo_inicial': grupo_inicial,
        'grupo_inicial_nombre': NOMBRES_GRUPO[grupo_inicial],
        'estado_guardado': estado_guardado(),
        'error_orden': (errores_campo or {}).get('orden', ''),
        'max_imagen': MAX_IMAGEN,
    })
    respuesta = render(request, 'admin/paginas/editor_inicio.html', context)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


@xframe_options_sameorigin
def lienzo_inicio(request):
    """Inicio real con el borrador. Solo se abre dentro del editor."""
    _exigir_staff(request)
    respuesta = render(request, 'inicio.html', contexto_lienzo())
    respuesta['Cache-Control'] = 'no-store'
    respuesta['X-Robots-Tag'] = 'noindex, nofollow'
    return respuesta


def _exigir_staff(request):
    usuario = request.user
    if not usuario.is_authenticated or not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied
