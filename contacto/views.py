from BiologiaComputacional.forms import FormularioContacto
from contacto.envio import entregar_mensaje
from django.shortcuts import render, redirect
from django.contrib import messages
from paginas.contenido import contexto_publico

# Create your views here.


def _pintar(request, formulario):
    contexto = contexto_publico('contacto', request)
    contexto['form'] = formulario
    return render(request, "contacto/contacto.html", contexto)


def contacto(request):
    if request.method != "POST":
        return _pintar(request, FormularioContacto())

    formulario = FormularioContacto(request.POST)
    if not formulario.is_valid():
        # Formulario ligado: lo escrito se conserva y cada campo muestra su error.
        return _pintar(request, formulario)

    infForm = formulario.cleaned_data
    # Guardar va dentro de entregar_mensaje, antes del correo.
    if not entregar_mensaje(infForm):
        messages.error(
            request,
            'No se pudo enviar el mensaje: el correo no está configurado o el servidor lo rechazó. Inténtalo más tarde.',
        )
        return _pintar(request, formulario)
    # Post/Redirect/Get: el aviso queda en la sesión y lo pinta el inicio.
    messages.success(request, 'Tu mensaje se envió correctamente.')
    return redirect('inicio')
