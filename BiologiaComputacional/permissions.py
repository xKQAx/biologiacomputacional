"""Permisos del gestor, compartidos para no repetir la misma comprobación."""

from django.contrib.auth.decorators import user_passes_test


def is_superuser(user):
    return bool(user.is_authenticated and user.is_superuser)


def is_staff_or_superuser(user):
    return bool(user.is_authenticated and (user.is_staff or user.is_superuser))


staff_required = user_passes_test(is_staff_or_superuser)
superuser_required = user_passes_test(is_superuser)
