"""Crea ProfileAdditionalInfo al dar de alta un usuario.

La señal no vuelve a guardar User, así que no se re-dispara.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from identity.accounts import normalize_email
from identity.models import ProfileAdditionalInfo


def ensure_user_profile(user):
    return ProfileAdditionalInfo.objects.get_or_create(user=user)


@receiver(pre_save, sender=User)
def lowercase_user_email(sender, instance, **kwargs):
    # El índice único compara el correo ya en minúsculas.
    instance.email = normalize_email(instance.email)


@receiver(post_save, sender=User)
def create_profile_on_user_created(sender, instance, created, **kwargs):
    if created:
        ensure_user_profile(instance)
