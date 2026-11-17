"""Crea un archivo con copia de la base de datos y los medios del laboratorio."""

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction
from django.utils import timezone


CHUNK_SIZE = 1024 * 1024
FORMATO = 'biocom-backup-v1'


class Command(BaseCommand):
    help = 'Respalda la base de datos y los archivos de medios en un ZIP.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--destino',
            default=str(Path(settings.BASE_DIR).parent / 'respaldos'),
            help='Carpeta externa al proyecto donde guardar el ZIP.',
        )

    def handle(self, *args, **options):
        destino = Path(options['destino']).expanduser().resolve()
        raiz_proyecto = Path(settings.BASE_DIR).resolve()
        raiz_medios = Path(settings.MEDIA_ROOT).resolve()
        if _dentro_de(destino, raiz_proyecto):
            raise CommandError(
                'El destino debe estar fuera del repositorio para evitar incluir datos privados en Git.'
            )
        if _dentro_de(destino, raiz_medios):
            raise CommandError('El destino no puede estar dentro de MEDIA_ROOT.')

        destino.mkdir(parents=True, exist_ok=True)
        if not destino.is_dir():
            raise CommandError('El destino debe ser una carpeta.')

        marca_tiempo = timezone.now().strftime('%Y%m%dT%H%M%S%fZ')
        archivo_final = destino / f'biocom-{marca_tiempo}.zip'
        temporal = None
        base_temporal = None
        miembros = []

        try:
            with tempfile.NamedTemporaryFile(
                prefix='.biocom-', suffix='.zip', dir=destino, delete=False,
            ) as temporal_zip:
                temporal = Path(temporal_zip.name)

            with zipfile.ZipFile(
                temporal, mode='w', compression=zipfile.ZIP_DEFLATED,
            ) as archivo_zip:
                if connection.vendor == 'sqlite':
                    base_temporal = _respaldo_sqlite()
                    miembro_db = 'database/db.sqlite3'
                elif connection.vendor == 'postgresql':
                    base_temporal = _respaldo_django()
                    miembro_db = 'database/django-fixture.json'
                else:
                    raise CommandError(
                        f'El motor de base de datos «{connection.vendor}» no está soportado.'
                    )

                miembros.append(_agregar_archivo(
                    archivo_zip, base_temporal, miembro_db,
                ))
                if raiz_medios.exists():
                    for ruta in sorted(raiz_medios.rglob('*')):
                        if ruta.is_symlink() or not ruta.is_file():
                            continue
                        relativo = ruta.relative_to(raiz_medios).as_posix()
                        miembros.append(_agregar_archivo(
                            archivo_zip, ruta, f'media/{relativo}',
                        ))

                manifiesto = {
                    'format': FORMATO,
                    'created_at': timezone.now().isoformat(),
                    'database_vendor': connection.vendor,
                    'database_member': miembro_db,
                    'members': miembros,
                }
                archivo_zip.writestr(
                    'manifest.json',
                    json.dumps(manifiesto, ensure_ascii=False, indent=2).encode('utf-8'),
                )

            try:
                os.chmod(temporal, 0o600)
            except OSError:
                # ACL de Windows u otro sistema que no admita permisos POSIX.
                pass
            os.replace(temporal, archivo_final)
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            raise CommandError(f'No se pudo crear el respaldo: {error}') from error
        finally:
            for ruta in (temporal, base_temporal):
                if ruta is not None:
                    try:
                        ruta.unlink(missing_ok=True)
                    except OSError:
                        pass

        self.stdout.write(self.style.SUCCESS(f'Respaldo creado: {archivo_final}'))


def _dentro_de(ruta, raiz):
    try:
        ruta.relative_to(raiz)
        return True
    except ValueError:
        return False


def _respaldo_sqlite():
    """Usa la API online backup de SQLite para obtener una copia consistente."""
    conexion = connection
    conexion.ensure_connection()
    nombre = None
    try:
        with tempfile.NamedTemporaryFile(prefix='biocom-db-', suffix='.sqlite3', delete=False) as tmp:
            nombre = Path(tmp.name)
        destino = sqlite3.connect(nombre)
        try:
            conexion.connection.backup(destino)
        finally:
            destino.close()
        return nombre
    except Exception:
        if nombre is not None:
            nombre.unlink(missing_ok=True)
        raise


def _respaldo_django():
    """Exporta los modelos con Django para no depender del binario pg_dump."""
    with tempfile.NamedTemporaryFile(
        prefix='biocom-db-', suffix='.json', delete=False,
    ) as tmp:
        nombre = Path(tmp.name)
    try:
        with transaction.atomic(using='default'):
            with connection.cursor() as cursor:
                cursor.execute(
                    'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
                )
            call_command(
                'dumpdata', output=str(nombre), natural_foreign=True,
                natural_primary=True, exclude=['sessions.session'], using='default',
            )
        return nombre
    except Exception:
        nombre.unlink(missing_ok=True)
        raise


def _agregar_archivo(archivo_zip, origen, miembro):
    sha = hashlib.sha256()
    peso = 0
    with Path(origen).open('rb') as fuente, archivo_zip.open(miembro, 'w') as destino:
        while True:
            fragmento = fuente.read(CHUNK_SIZE)
            if not fragmento:
                break
            destino.write(fragmento)
            sha.update(fragmento)
            peso += len(fragmento)
    return {'path': miembro, 'size_bytes': peso, 'sha256': sha.hexdigest()}


def verificar_archivo(ruta):
    """Valida formato, nombres seguros y hashes antes de extraer/restaurar."""
    try:
        with zipfile.ZipFile(ruta, 'r') as archivo_zip:
            nombres = archivo_zip.namelist()
            if len(nombres) != len(set(nombres)) or 'manifest.json' not in nombres:
                raise ValueError('El ZIP no tiene un manifiesto válido o repite archivos.')
            for info in archivo_zip.infolist():
                _validar_nombre(info.filename)
                modo = info.external_attr >> 16
                if stat.S_ISLNK(modo):
                    raise ValueError('El ZIP contiene un enlace simbólico no permitido.')

            manifiesto = json.loads(archivo_zip.read('manifest.json'))
            if not isinstance(manifiesto, dict):
                raise ValueError('El manifiesto debe ser un objeto JSON.')
            if manifiesto.get('format') != FORMATO:
                raise ValueError('La versión del respaldo no es compatible.')
            miembros = manifiesto.get('members')
            if not isinstance(miembros, list):
                raise ValueError('El manifiesto no incluye la lista de archivos.')
            esperados = {'manifest.json'}
            rutas_vistas = set()
            for miembro in miembros:
                if not isinstance(miembro, dict):
                    raise ValueError('El manifiesto tiene una entrada inválida.')
                nombre = miembro.get('path')
                _validar_nombre(nombre)
                if nombre in rutas_vistas or nombre == 'manifest.json':
                    raise ValueError('El manifiesto repite una ruta o reemplaza su archivo.')
                if not isinstance(miembro.get('size_bytes'), int) or miembro['size_bytes'] < 0:
                    raise ValueError('El manifiesto contiene un tamaño inválido.')
                esperado_sha = miembro.get('sha256')
                if not isinstance(esperado_sha, str) or len(esperado_sha) != 64:
                    raise ValueError('El manifiesto contiene un hash inválido.')
                _verificar_hash(archivo_zip, miembro)
                rutas_vistas.add(nombre)
                esperados.add(nombre)

            db_member = manifiesto.get('database_member')
            if db_member not in rutas_vistas:
                raise ValueError('El respaldo no contiene la base de datos indicada.')
            if set(nombres) != esperados:
                raise ValueError('El ZIP tiene archivos no declarados en el manifiesto.')
            return manifiesto
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, KeyError) as error:
        raise ValueError(f'No se pudo leer el respaldo: {error}') from error


def _validar_nombre(nombre):
    if not isinstance(nombre, str) or not nombre or '\\' in nombre:
        raise ValueError('El ZIP contiene una ruta de archivo no permitida.')
    ruta = PurePosixPath(nombre)
    if ruta.is_absolute() or any(parte in ('..', '.') for parte in ruta.parts):
        raise ValueError('El ZIP contiene una ruta de archivo no permitida.')


def _verificar_hash(archivo_zip, miembro):
    sha = hashlib.sha256()
    peso = 0
    with archivo_zip.open(miembro['path']) as fuente:
        while True:
            fragmento = fuente.read(CHUNK_SIZE)
            if not fragmento:
                break
            sha.update(fragmento)
            peso += len(fragmento)
    if peso != miembro['size_bytes'] or sha.hexdigest() != miembro['sha256']:
        raise ValueError(f"El archivo «{miembro['path']}» no coincide con su hash.")
