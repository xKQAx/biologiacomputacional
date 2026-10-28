"""Lectura de los mensajes en el panel.

Misma idea que las cuentas: pantallas propias del admin, no el
listado genérico de Añadir/Modificar. Abrir un mensaje lo marca leído.
"""

from django.contrib import admin
from django.shortcuts import get_object_or_404, render

from contacto.models import MensajeContacto


def _render(request, plantilla, contexto):
    datos = admin.site.each_context(request)
    datos.update(contexto)
    return render(request, plantilla, datos)


def lista_mensajes(request):
    return _render(request, 'admin/mensajes/lista.html', {
        'title': 'Mensajes de contacto',
        'mensajes': MensajeContacto.objects.all(),
    })


def detalle_mensaje(request, pk):
    mensaje = get_object_or_404(MensajeContacto, pk=pk)
    mensaje.marcar_leido()
    return _render(request, 'admin/mensajes/detalle.html', {
        'title': mensaje.nombre_completo or 'Mensaje',
        'mensaje': mensaje,
    })
