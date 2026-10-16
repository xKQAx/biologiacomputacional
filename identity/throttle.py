"""Límite de intentos de login, sin dependencias fuera de Django.

La clave junta el texto escrito y la IP. Un acierto borra el contador.
La caché de pruebas puede usar otro LOCATION para no mezclar procesos.
"""

from django.core.cache import cache

from identity.accounts import normalize_username

LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60
LOCKOUT_MESSAGE = "Demasiados intentos. Espera 15 minutos e inténtalo de nuevo."


def client_ip(request):
    # REMOTE_ADDR no se puede falsificar desde el formulario, a diferencia
    # de X-Forwarded-For.
    if request is None:
        return ""
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _key(identifier, ip):
    ident = normalize_username(identifier).lower()
    return f"identity-login-fail:{ident}:{ip or ''}"


def is_locked(identifier, ip):
    if not normalize_username(identifier):
        return False
    try:
        failures = int(cache.get(_key(identifier, ip), 0) or 0)
    except (TypeError, ValueError):
        return False
    return failures >= LOGIN_FAILURE_LIMIT


def register_failure(identifier, ip):
    if not normalize_username(identifier):
        return 0
    key = _key(identifier, ip)
    try:
        failures = int(cache.get(key, 0) or 0) + 1
    except (TypeError, ValueError):
        failures = 1
    cache.set(key, failures, LOGIN_LOCKOUT_SECONDS)
    return failures


def clear_failures(identifier, ip):
    if normalize_username(identifier):
        cache.delete(_key(identifier, ip))
