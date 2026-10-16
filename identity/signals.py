"""Crea ProfileAdditionalInfo al dar de alta un usuario.

La señal no vuelve a guardar User, así que no se re-dispara.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from identity.models import ProfileAdditionalInfo


def ensure_user_profile(user):
    return ProfileAdditionalInfo.objects.get_or_create(user=user)


@receiver(post_save, sender=User)
def create_profile_on_user_created(sender, instance, created, **kwargs):
    if created:
        ensure_user_profile(instance)
