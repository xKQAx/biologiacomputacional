# Laboratorio de Biología Computacional

Sitio web Django (profesionales, investigación, servicios, contacto e identidad).

## Requisitos

- Python 3.12
- Entorno virtual en `venv/` (ya está en `.gitignore`)

## Arranque en desarrollo

Python 3.12, entorno virtual y SQLite (no hace falta Postgres en local).

```bash
cd /home/santiago_cacua/proyectos/biologiacomputacional
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y pon al menos `SECRET_KEY`. Si no existe `db.sqlite3`:

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Abrir [http://127.0.0.1:8001/](http://127.0.0.1:8001/).

El puerto **8000** suele estar ocupado en este servidor; por eso se usa **8001**.

Si ya hay usuarios creados antes de la señal de perfil:

```bash
python manage.py create_profiles
```

## Variables de entorno

Están documentadas en `.env.example`. `python-dotenv` carga `.env` al arrancar y no pisa variables ya exportadas. Sin `DATABASE_URL` se usa `db.sqlite3`. Más adelante `DATABASE_URL` puede ser la URI de Supabase/Postgres (`?sslmode=require`).

Correo de activación (registro) y de contacto:

1. Copia `.env.example` a `.env` (el arranque ya lo hace). `.env` está en `.gitignore` y no se sube. Sin ese archivo, con `DEBUG=true` y sin `EMAIL_HOST_USER`, Django imprime el correo en la terminal del `runserver` (`From: webmaster@localhost`) y la bandeja queda vacía. El aviso de revisar el correo puede aparecer igual.
2. Para que llegue a Gmail: `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=true`. `EMAIL_HOST_USER` es la cuenta remitente. `EMAIL_HOST_PASSWORD` no es la contraseña de inicio de sesión.
3. En esa cuenta, activa la verificación en dos pasos ([enlace](https://myaccount.google.com/signinoptions/two-step-verification)) y crea una contraseña de aplicación de 16 caracteres en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Pégala sin espacios.
4. Guarda `.env` y reinicia `runserver`. Django solo lee `.env` al arrancar.
5. Si Google no ofrece contraseñas de aplicación (Workspace, menor de edad o 2FA avanzado), usa un SMTP transaccional como Brevo o Resend.
6. Para probar solo en local: deja `EMAIL_HOST_USER` vacío, reinicia y copia el enlace de activación que sale en la terminal.

El formulario de contacto envía a `CONTACT_EMAIL` (por defecto `lab.biomol.udes@gmail.com`).

## Notas

- Con `DEBUG=true`, Django muestra su 404 técnico. Las plantillas `404.html` y `403.html` se usan cuando `DEBUG` está en `false`.
- `titulo_universitario` admite 120 caracteres (antes 30, insuficiente para un título real).
- No dejes secretos en el código. Rota cualquier contraseña que haya estado en el repositorio.

## Lista previa a producción

- Usa `DEBUG=false`, una `SECRET_KEY` nueva y `ALLOWED_HOSTS` con el dominio real.
- Termina el despliegue detrás de HTTPS; configura `SECURE_SSL_REDIRECT=true`. Activa HSTS (`SECURE_HSTS_SECONDS`) solo cuando HTTPS esté probado en todo el dominio.
- Configura PostgreSQL y un almacenamiento persistente para archivos subidos; SQLite y el disco local no son una estrategia de producción ni de respaldo.
- Configura el SMTP real y confirma que activación de cuentas, recuperación de contraseña y formulario de contacto llegan al buzón acordado.
- Ejecuta `python manage.py check --deploy` en el entorno de producción y revisa sus avisos antes de abrir el sitio.
- Define y ensaya restauración de base de datos y medios; revisa los textos institucionales de privacidad antes de anunciar el formulario.

## Cuentas y rutas útiles

- Login: `/identity/`
- Admin: `/admin/`
- Registro: `/identity/register/`

## Respaldo y restauración

El comando `backup_lab` crea un ZIP con la base de datos, los archivos de `MEDIA_ROOT` y un manifiesto con tamaños y hashes SHA-256. Por defecto guarda el archivo en `../respaldos`, fuera del repositorio. También puedes indicar una carpeta segura fuera del proyecto:

```bash
python manage.py backup_lab --destino /ruta/segura/respaldos
python manage.py verificar_respaldo_laboratorio --archivo /ruta/segura/respaldos/biocom-FECHA.zip
```

La verificación no extrae ni restaura archivos. Comprueba el formato, las rutas y la integridad de cada archivo. El ZIP contiene datos del laboratorio y debe guardarse con acceso restringido. En SQLite se hace una copia consistente de la base activa; en PostgreSQL se exportan los registros con Django y se incluye la misma carpeta de medios.

### Restaurar una copia SQLite

1. Detén el servidor y conserva una copia de la base actual y de `MEDIA_ROOT` antes de continuar.
2. Verifica el ZIP con `verificar_respaldo_laboratorio`.
3. Extráelo en una carpeta temporal fuera del repositorio:

   ```bash
   python -m zipfile -e /ruta/segura/respaldos/biocom-FECHA.zip /tmp/biocom-restauracion
   ```

4. Comprueba la base extraída antes de reemplazar la actual:

   ```bash
   python -c "import sqlite3; db=sqlite3.connect('/tmp/biocom-restauracion/database/db.sqlite3'); print(db.execute('PRAGMA integrity_check').fetchone()[0]); db.close()"
   ```

   Continúa solo si imprime `ok`.
5. Aparta la base actual y la carpeta actual de medios con nombres de recuperación; copia en su lugar `database/db.sqlite3` y el contenido de `media/` del respaldo. Conserva las copias apartadas hasta confirmar que el sitio arrancó y las páginas cargan sus imágenes y archivos.
6. Ejecuta `python manage.py migrate` con la misma versión del proyecto y comprueba el sitio con `python manage.py check`.

### Restaurar una copia PostgreSQL

El miembro `database/django-fixture.json` es una exportación de registros, no una copia SQL del esquema. Restaura primero en una base PostgreSQL nueva y vacía con la misma versión del proyecto: configura temporalmente `DATABASE_URL` para apuntar a esa base, ejecuta `python manage.py migrate` y luego `python manage.py loaddata /tmp/biocom-restauracion/database/django-fixture.json`. Restaura también los archivos de `media/` en un `MEDIA_ROOT` vacío. Valida el sitio y cambia la configuración a la base restaurada solo después de comprobar los datos y archivos. Mantén la base y los medios anteriores hasta cerrar la revisión.

Si una restauración falla, detén el servidor y vuelve a colocar las copias apartadas de la base y los medios antes de arrancarlo. No extraigas un ZIP que no haya pasado la verificación.
