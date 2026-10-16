from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from identity.signals import ensure_user_profile


class Command(BaseCommand):
    help = 'Crea ProfileAdditionalInfo para usuarios que aún no tienen uno'

    def handle(self, *args, **options):
        created_count = 0
        for user in User.objects.all():
            _profile, created = ensure_user_profile(user)
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f'Perfiles creados: {created_count}'
        ))
