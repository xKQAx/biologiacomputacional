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


# Tope bajo: basta para detectar un correo repetido sin recorrer toda la tabla.
_LOGIN_MATCH_LIMIT = 5


def login_candidates(identifier):
    """Cuentas que podrían corresponder al texto escrito en el login.

    Primero el nombre de usuario, también si parece un correo. El correo
    solo se usa cuando ninguna cuenta se llama así.
    """
    identifier = normalize_username(identifier)
    if not identifier:
        return []

    by_name = list(
        User.objects.filter(username__iexact=identifier)[:_LOGIN_MATCH_LIMIT]
    )
    if by_name:
        return by_name
    if "@" not in identifier:
        return []
    return list(User.objects.filter(email__iexact=identifier)[:_LOGIN_MATCH_LIMIT])


def user_for_login(identifier):
    """Resuelve con qué cuenta entrar.

    Devuelve (usuario, código). El código es «ambiguous» cuando hay más de
    una coincidencia. Si no hay ninguna, el usuario es None y el login muestra
    el mismo mensaje que una contraseña incorrecta.
    """
    matches = login_candidates(identifier)
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, "ambiguous"
    return None, None
