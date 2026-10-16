"""Envío de correo del sitio.

Contacto y registro comparten el mismo fallo controlado: si el SMTP
no está configurado o rechaza el mensaje, la vista sigue respondiendo.
"""

from smtplib import SMTPException

from django.conf import settings
from django.core.mail import BadHeaderError, send_mail


def send_project_mail(subject, message, recipient_list):
    """Envía un correo con el remitente del proyecto.

    Devuelve True si salió. False si el servidor no está disponible
    o rechazó cabeceras o la conexión.
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
    except (SMTPException, OSError, BadHeaderError):
        return False
    return True
