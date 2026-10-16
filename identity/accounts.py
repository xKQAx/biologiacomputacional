"""Consultas de cuenta que comparten el registro y el inicio de sesión.

Así el aviso de «ya existe» y el login usan la misma regla,
sin repetir el filtro en cada vista.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

ACTIVATION_RESEND_SESSION_KEY = "activation_resend_user_id"


def normalize_username(value):
    return (value or "").strip()


def normalize_email(value):
    return (value or "").strip().lower()


def username_taken(username):
    username = normalize_username(username)
    if not username:
        return False
    return User.objects.filter(username__iexact=username).exists()


def email_taken(email):
    email = normalize_email(email)
    if not email:
        return False
    return User.objects.filter(email__iexact=email).exists()


def user_for_login(identifier):
    """Resuelve con qué cuenta entrar.

    Devuelve (usuario, código). El código es «ambiguous» cuando el correo
    pertenece a más de una cuenta. Si no hay coincidencia, el usuario es
    None y el login muestra el mismo mensaje que una contraseña incorrecta.
    """
    identifier = normalize_username(identifier)
    if not identifier:
        return None, None

    by_name = list(User.objects.filter(username__iexact=identifier)[:2])
    if len(by_name) == 1:
        return by_name[0], None
    if len(by_name) > 1:
        return None, "ambiguous"

    if "@" not in identifier:
        return None, None

    by_email = list(User.objects.filter(email__iexact=identifier)[:2])
    if len(by_email) == 1:
        return by_email[0], None
    if len(by_email) > 1:
        return None, "ambiguous"
    return None, None
