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

El formulario de contacto envía a `CONTACT_EMAIL` (por defecto `biocomp@udes.edu.co`).

## Notas

- Con `DEBUG=true`, Django muestra su 404 técnico. Las plantillas `404.html` y `403.html` se usan cuando `DEBUG` está en `false`.
- `titulo_universitario` admite 120 caracteres (antes 30, insuficiente para un título real).
- No dejes secretos en el código. Rota cualquier contraseña que haya estado en el repositorio.

## Cuentas y rutas útiles

- Login: `/identity/`
- Admin: `/admin/`
- Registro: `/identity/register/`
