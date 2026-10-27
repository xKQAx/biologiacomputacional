"""Agrupa lo que queda del índice del admin, debajo de las páginas del sitio.

Investigación, profesionales y servicios se editan en sus páginas.
Las cuentas tienen su pantalla; usuarios, grupos y perfiles no vuelven
como filas de Añadir/Modificar. Las tablas internas, al final y solo
para un superusuario.
"""

from django.contrib import admin

# Nombre visible en el índice, no el de la clase.
NOMBRES = {
    ("identity", "profileadditionalinfo"): ("Perfil", "Perfiles"),
    ("auth", "user"): ("Usuario", "Usuarios"),
    ("auth", "group"): ("Grupo", "Grupos"),
    ("auth", "permission"): ("Permiso", "Permisos"),
    ("sessions", "session"): ("Sesión", "Sesiones"),
    ("admin", "logentry"): ("Registro", "Registros"),
    ("contenttypes", "contenttype"): ("Tipo de contenido", "Tipos de contenido"),
}

# Orden dentro de cada grupo. Lo que no esté aquí va al final, por nombre.
ORDEN = {}

SECCIONES = (
    ("sistema", "Sistema"),
)

# El sitio público sigue leyendo estos modelos. No vuelven al índice ni a la barra.
APPS_FUERA_DEL_INDICE = {"investigacion", "profesionales", "servicios"}
APPS_CUENTAS = {"auth", "identity"}
APPS_SISTEMA = {"admin", "sessions", "contenttypes"}

# Tablas que un editor de contenido no necesita ver en el índice.
INTERNOS = {
    ("auth", "permission"),
    ("sessions", "session"),
    ("admin", "logentry"),
    ("contenttypes", "contenttype"),
    ("paginas", "bloqueportada"),
    ("identity", "additionaluserinfo"),
    ("investigacion", "carruselborrador"),
}

_ENVUELTO = False


def aplicar_nombres():
    from django.apps import apps

    for (app_label, model_name), (singular, plural) in NOMBRES.items():
        try:
            modelo = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        modelo._meta.verbose_name = singular
        modelo._meta.verbose_name_plural = plural


def destino_de(app_label, model_name):
    if app_label in APPS_FUERA_DEL_INDICE or app_label in APPS_CUENTAS:
        # Siguen registrados: el login del admin no depende de estas filas.
        return None
    clave = (app_label, model_name)
    if clave in INTERNOS or app_label in APPS_SISTEMA or app_label == "paginas":
        return "sistema"
    return "sistema"


def agrupar_indice(app_list, request):
    """Reparte los modelos ya filtrados por permiso en los grupos del índice."""
    grupos = {clave: [] for clave, _nombre in SECCIONES}
    es_super = bool(getattr(request.user, "is_superuser", False))

    for app in app_list:
        for modelo in app["models"]:
            clase = modelo["model"]
            destino = destino_de(clase._meta.app_label, clase._meta.model_name)
            if destino is None or (destino == "sistema" and not es_super):
                continue
            grupos[destino].append(modelo)

    resultado = []
    for clave, nombre in SECCIONES:
        modelos = grupos[clave]
        if not modelos:
            continue
        modelos.sort(key=lambda modelo: _clave_orden(clave, modelo))
        resultado.append({
            "name": nombre,
            "app_label": clave,
            "app_url": "",
            "has_module_perms": True,
            "models": modelos,
        })
    return resultado


def _clave_orden(seccion, modelo):
    nombre = modelo["model"]._meta.model_name
    preferido = ORDEN.get(seccion, ())
    if nombre in preferido:
        return (0, preferido.index(nombre))
    return (1, modelo["name"].lower())


def configurar_admin():
    """Cabecera, índice y nombres. Se puede llamar más de una vez."""
    global _ENVUELTO

    aplicar_nombres()
    admin.site.site_header = "Laboratorio de Biología Computacional"
    admin.site.site_title = "Biología Computacional"
    admin.site.index_title = "Panel del laboratorio"
    admin.site.index_template = "admin/indice_laboratorio.html"
    admin.site.site_url = "/"

    if _ENVUELTO:
        return

    original = admin.site.get_app_list

    def get_app_list(request, app_label=None):
        # La página de una app concreta sigue el listado de Django.
        lista = original(request, app_label)
        if app_label:
            return lista
        return agrupar_indice(lista, request)

    admin.site.get_app_list = get_app_list
    _ENVUELTO = True
