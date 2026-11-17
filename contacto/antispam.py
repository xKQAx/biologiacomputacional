"""Límite de frecuencia para envíos válidos del formulario público."""

import hashlib
import hmac
import logging

from django.conf import settings
from django.core.cache import cache

from identity.throttle import client_ip

logger = logging.getLogger(__name__)

INTENTOS_CONTACTO_MAXIMOS = 8
VENTANA_CONTACTO_SEGUNDOS = 10 * 60


def permitir_envio(request):
    """Permite hasta ocho mensajes válidos por IP cada diez minutos."""
    ip = client_ip(request) or 'desconocida'
    huella = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        ip.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    clave = f'contacto-envios:{huella}'

    try:
        if cache.add(clave, 1, timeout=VENTANA_CONTACTO_SEGUNDOS):
            intentos = 1
        else:
            try:
                intentos = cache.incr(clave)
            except ValueError:
                # La clave pudo vencer entre add() e incr().
                cache.set(clave, 1, timeout=VENTANA_CONTACTO_SEGUNDOS)
                intentos = 1
    except Exception:
        # Un fallo de caché no bloquea el contacto; se deja registro operativo.
        logger.exception('No se pudo aplicar el límite del formulario de contacto.')
        return True

    return intentos <= INTENTOS_CONTACTO_MAXIMOS
