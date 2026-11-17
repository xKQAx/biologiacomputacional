from pathlib import Path

from django.core.management import BaseCommand, CommandError

from paginas.management.commands.backup_lab import verificar_archivo


class Command(BaseCommand):
    help = 'Verifica integridad y rutas de un respaldo sin extraerlo ni restaurarlo.'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', required=True, help='Archivo ZIP que se validará.')

    def handle(self, *args, **options):
        ruta = Path(options['archivo']).expanduser()
        try:
            manifiesto = verificar_archivo(ruta)
        except ValueError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(
            f"Respaldo válido: motor {manifiesto['database_vendor']}, "
            f"{len(manifiesto['members'])} archivos verificados."
        ))
