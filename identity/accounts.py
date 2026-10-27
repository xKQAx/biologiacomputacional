"""Consultas de cuenta que comparten el registro y el inicio de sesión.

Así el aviso de «ya existe» y el login usan la misma regla,
sin repetir el filtro en cada vista.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

ACTIVATION_RESEND_SESSION_KEY = "activation_resend_user_id"
PASSWORD_RESET_UID_SESSION_KEY = "password_reset_uid"
PASSWORD_RESET_TOKEN_SESSION_KEY = "password_reset_token"


def normalize_username(value):
    return (value or "").strip()


def normalize_email(value):
    return (value or "").strip().lower()


def username_taken(username, exclude_pk=None):
    """True si otra cuenta ya usa ese nombre, sin distinguir mayúsculas."""
    username = normalize_username(username)
    if not username:
        return False
    matches = User.objects.filter(username__iexact=username)
    if exclude_pk:
        matches = matches.exclude(pk=exclude_pk)
    return matches.exists()


def email_taken(email, exclude_pk=None):
    """True si otra cuenta ya usa ese correo, sin distinguir mayúsculas."""
    email = normalize_email(email)
    if not email:
        return False
    matches = User.objects.filter(email__iexact=email)
    if exclude_pk:
        matches = matches.exclude(pk=exclude_pk)
    return matches.exists()


def accounts_for_email(email, limit=2):
    """Como mucho `limit` cuentas con ese correo.

    El índice único impide duplicados nuevos. El tope evita recorrer la
    tabla si quedara algún dato viejo.
    """
    email = normalize_email(email)
    if not email:
        return []
    return list(User.objects.filter(email__iexact=email).order_by("id")[:limit])


def account_for_email(email):
    """La única cuenta de ese correo, o None si no hay una sola."""
    matches = accounts_for_email(email)
    if len(matches) != 1:
        return None
    return matches[0]


def login_candidates(identifier):
    """Cuentas que podrían corresponder al texto escrito en el login.

    Primero el nombre de usuario, también si parece un correo. El correo
    solo se usa cuando ninguna cuenta se llama así.
    """
    identifier = normalize_username(identifier)
    if not identifier:
        return []

    by_name = User.objects.filter(username__iexact=identifier).first()
    if by_name is not None:
        return [by_name]
    if "@" not in identifier:
        return []
    # Si hubiera dos cuentas viejas con el mismo correo, no elegimos una.
    account = account_for_email(identifier)
    return [account] if account is not None else []


def user_for_login(identifier):
    """Resuelve con qué cuenta entrar.

    Devuelve (usuario, None). Si no hay una sola coincidencia, el usuario es
    None y el login muestra el mismo mensaje que una contraseña incorrecta.
    """
    matches = login_candidates(identifier)
    if len(matches) == 1:
        return matches[0], None
    return None, None
