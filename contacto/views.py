from BiologiaComputacional.forms import FormularioContacto
from contacto.antispam import permitir_envio, VENTANA_CONTACTO_SEGUNDOS
from contacto.envio import entregar_mensaje
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from paginas.contenido import contexto_publico

# Create your views here.


def _pintar(request, formulario, status=200):
    contexto = contexto_publico('contacto', request)
    contexto['form'] = formulario
    return render(request, "contacto/contacto.html", contexto, status=status)


def contacto(request):
    if request.method != "POST":
        return _pintar(request, FormularioContacto())

    # Trampa para bots: aceptar en silencio el envío sin guardar ni mandar correo.
    if (request.POST.get('website') or '').strip():
        return HttpResponse(status=204)

    formulario = FormularioContacto(request.POST)
    if not formulario.is_valid():
        # Formulario ligado: lo escrito se conserva y cada campo muestra su error.
        return _pintar(request, formulario)

    if not permitir_envio(request):
        messages.error(
            request,
            'Llegaste al límite de envíos por ahora. Espera unos minutos e inténtalo de nuevo.',
        )
        response = _pintar(request, FormularioContacto(), status=429)
        response['Retry-After'] = str(VENTANA_CONTACTO_SEGUNDOS)
        return response

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
