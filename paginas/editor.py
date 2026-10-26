"""Pantalla del editor de inicio, dentro del admin."""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from paginas.contenido import (
    contexto_lienzo,
    descartar_borrador,
    grupos_editor,
    guardar_borrador,
    hay_borrador,
    leer_valores,
    publicar,
)


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
            valores, errores = leer_valores(request.POST)
            if errores:
                for error in errores:
                    messages.error(request, error)
                return _pintar(request, valores, pendiente=True)
            if accion == 'guardar':
                guardar_borrador(valores)
                messages.success(
                    request,
                    'Borrador guardado. La portada pública no cambió.',
                )
            else:
                publicar(valores)
                messages.success(request, 'Página de inicio publicada.')
            return redirect('admin:pagina_inicio')
        messages.error(request, 'No se reconoció la acción.')
        return redirect('admin:pagina_inicio')

    return _pintar(request)


def _pintar(request, valores=None, pendiente=False):
    context = admin.site.each_context(request)
    context.update({
        'title': 'Editar página de inicio',
        'grupos': grupos_editor(valores),
        'hay_borrador': hay_borrador(),
        'lienzo_url': reverse('admin:pagina_inicio_lienzo'),
        'pendiente': pendiente,
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
