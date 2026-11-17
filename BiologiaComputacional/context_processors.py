from django.conf import settings


def contacto_publico(_request):
    """Expone el único dato público de contacto confirmado por el laboratorio."""
    return {'contact_email': settings.CONTACT_EMAIL}
