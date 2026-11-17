import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TransactionTestCase, override_settings


class BackupLaboratorioTests(TransactionTestCase):
    def test_copia_sqlite_medios_y_manifiesto_con_hashes(self):
        with tempfile.TemporaryDirectory() as temporal:
            temporal = Path(temporal)
            medios = temporal / 'medios'
            medios.mkdir()
            (medios / 'foto.txt').write_bytes(b'archivo de prueba')
            salida = temporal / 'respaldos'

            with override_settings(MEDIA_ROOT=medios):
                call_command('backup_lab', destino=str(salida))

            archivos = list(salida.glob('biocom-*.zip'))
            self.assertEqual(len(archivos), 1)
            with zipfile.ZipFile(archivos[0]) as respaldo:
                manifiesto = json.loads(respaldo.read('manifest.json'))
                self.assertEqual(manifiesto['format'], 'biocom-backup-v1')
                self.assertEqual(manifiesto['database_vendor'], 'sqlite')
                self.assertIn('database/db.sqlite3', respaldo.namelist())
                self.assertEqual(
                    respaldo.read('media/foto.txt'), b'archivo de prueba',
                )
                for miembro in manifiesto['members']:
                    contenido = respaldo.read(miembro['path'])
                    self.assertEqual(len(contenido), miembro['size_bytes'])
                    self.assertEqual(
                        hashlib.sha256(contenido).hexdigest(), miembro['sha256'],
                    )
            call_command('verificar_respaldo_laboratorio', archivo=str(archivos[0]))

    def test_rechaza_guardar_dentro_del_proyecto(self):
        with self.assertRaisesMessage(CommandError, 'El destino debe estar fuera'):
            call_command(
                'backup_lab',
                destino=str(Path(settings.BASE_DIR) / 'respaldo-prueba'),
            )
