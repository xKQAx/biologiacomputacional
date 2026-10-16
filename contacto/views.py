from BiologiaComputacional.forms import FormularioContacto
from BiologiaComputacional.mail import send_project_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages

# Create your views here.


def contacto(request):
    if request.method == "POST":
        formulario = FormularioContacto(request.POST)
        if formulario.is_valid():
            infForm = formulario.cleaned_data
            message = "Nombre completo: " + infForm['nombres'] + " " + infForm['apellidos'] + "\nTelefono: " + \
                infForm['telefono'] + "\nOpiniones: " + \
                infForm['opiniones'] + "\nCorreo: " + infForm.get('email', '')
            if not send_project_mail(
                'Información de contacto',
                message,
                [settings.CONTACT_EMAIL],
            ):
                messages.error(
                    request,
                    'No se pudo enviar el mensaje: el correo no está configurado o el servidor lo rechazó. Inténtalo más tarde.',
                )
                return render(request, "contacto/contacto.html", {"form": formulario})
            messages.success(request, 'Formulario enviado correctamente')
            return redirect('inicio')
        else:
            messages.error(request, 'Hubo un error en el formulario. Por favor, revisa los campos e inténtalo de nuevo.')
    else:
        formulario = FormularioContacto()
    return render(request, "contacto/contacto.html", {"form": formulario})
