"""Entrega del formulario de contacto.

El visitante sigue viendo el aviso de siempre. El personal, además,
tiene una copia en el panel: se guarda antes de hablar con el correo,
porque un fallo de SMTP no debe llevarse el texto.
"""

from django.conf import settings

from BiologiaComputacional.mail import send_project_mail
from contacto.models import MensajeContacto


def texto_correo(datos):
    """Mismo cuerpo que ya salía hacia el buzón del laboratorio."""
    return (
        'Nombre completo: ' + datos['nombres'] + ' ' + datos['apellidos']
        + '\nTelefono: ' + datos['telefono']
        + '\nOpiniones: ' + datos['opiniones']
        + '\nCorreo: ' + datos.get('email', '')
    )


def entregar_mensaje(datos):
    """Persiste el mensaje y luego intenta el correo.

    Devuelve True si el correo salió. False deja el aviso de error
    en la vista, pero el registro ya está guardado.
    """
    MensajeContacto.objects.create(
        nombres=datos['nombres'],
        apellidos=datos['apellidos'],
        email=datos['email'],
        telefono=datos['telefono'],
        opiniones=datos['opiniones'],
    )
    return send_project_mail(
        'Información de contacto',
        texto_correo(datos),
        [settings.CONTACT_EMAIL],
    )
