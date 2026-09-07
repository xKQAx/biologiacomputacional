# Laboratorio de Biología Computacional

Sitio web Django (profesionales, investigación, servicios, contacto e identidad).

## Requisitos

- Python 3.12
- Entorno virtual en `venv/` (ya está en `.gitignore`)

## Arranque en desarrollo

```bash
cd /home/server3/Proyectos/biologiacomputacional
source venv/bin/activate
python manage.py runserver 127.0.0.1:8001
```

Abrir [http://127.0.0.1:8001/](http://127.0.0.1:8001/).

Si el `venv` no existe:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

El puerto **8000** suele estar ocupado en este servidor; por eso se usa **8001**.

## Notas

- En `requirements.txt`, `numpy` y `pandas` no se usan en el código y no instalan en Python 3.12. El resto de dependencias sí.
- Con `DEBUG = True`, Django muestra su 404 técnico. Las plantillas `404.html` y `403.html` se usan cuando `DEBUG` está en `False`.
- Las credenciales SMTP están en `BiologiaComputacional/settings.py`; conviene pasarlas a variables de entorno.

## Cuentas y rutas útiles

- Login: `/identity/`
- Admin: `/admin/`
- Registro: `/identity/register/`
