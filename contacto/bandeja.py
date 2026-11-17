"""Lectura de los mensajes en el panel.

Misma idea que las cuentas: pantallas propias del admin, no el
listado genérico de Añadir/Modificar. Abrir un mensaje lo marca leído.
"""

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contacto.forms import SeguimientoMensajeForm
from contacto.models import MensajeContacto


def _render(request, plantilla, contexto, status=200):
    datos = admin.site.each_context(request)
    datos.update(contexto)
    return render(request, plantilla, datos, status=status)


def lista_mensajes(request):
    estado = request.GET.get('estado', '')
    mensajes = MensajeContacto.objects.select_related('asignado_a').all()
    if estado in MensajeContacto.Estado.values:
        mensajes = mensajes.filter(estado=estado)
    return _render(request, 'admin/mensajes/lista.html', {
        'title': 'Mensajes de contacto',
        'mensajes': mensajes,
        'estado_seleccionado': estado,
        'estados': MensajeContacto.Estado.choices,
    })


def detalle_mensaje(request, pk):
    mensaje = get_object_or_404(
        MensajeContacto.objects.select_related('asignado_a'), pk=pk,
    )
    mensaje.marcar_leido()
    return _render(request, 'admin/mensajes/detalle.html', {
        'title': mensaje.nombre_completo or 'Mensaje',
        'mensaje': mensaje,
        'seguimiento_form': SeguimientoMensajeForm(mensaje=mensaje),
    })


@require_POST
def actualizar_seguimiento(request, pk):
    mensaje = get_object_or_404(MensajeContacto, pk=pk)
    formulario = SeguimientoMensajeForm(request.POST)
    if formulario.is_valid():
        mensaje.estado = formulario.cleaned_data['estado']
        mensaje.asignado_a = formulario.cleaned_data['asignado_a']
        mensaje.save(update_fields=['estado', 'asignado_a'])
        messages.success(request, 'Seguimiento actualizado.')
        return redirect('admin:mensajes_detalle', pk=mensaje.pk)

    mensaje.marcar_leido()
    return _render(request, 'admin/mensajes/detalle.html', {
        'title': mensaje.nombre_completo or 'Mensaje',
        'mensaje': mensaje,
        'seguimiento_form': formulario,
    }, status=400)
