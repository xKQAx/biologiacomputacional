from django.contrib import admin
from identity.models import ProfileAdditionalInfo

# AdditionalUserInfo es el perfil legado: la web no lo lee.
# El perfil vigente sigue registrado, pero el índice no lo lista: las cuentas
# se administran en /admin/cuentas/. User y Group tampoco se quitan del admin,
# para no dejar el login del panel sin su maquinaria.


class PerfilAdmin(admin.ModelAdmin):
    """Foto, teléfono y género. Activar o suspender se hace en Cuentas."""

    exclude = ("suspendida",)


admin.site.register(ProfileAdditionalInfo, PerfilAdmin)


def registrar_rutas():
    if getattr(admin.site, "_cuentas_registradas", False):
        return

    original = admin.site.get_urls

    def get_urls():
        from django.urls import path

        from identity.cuentas import (
            activar_cuenta,
            desactivar_cuenta,
            editar_cuenta,
            eliminar_cuenta,
            lista_cuentas,
            nueva_cuenta,
        )

        extra = [
            path("cuentas/", admin.site.admin_view(lista_cuentas), name="cuentas"),
            path("cuentas/nueva/", admin.site.admin_view(nueva_cuenta), name="cuentas_nueva"),
            path(
                "cuentas/<int:pk>/desactivar/",
                admin.site.admin_view(desactivar_cuenta),
                name="cuentas_desactivar",
            ),
            path(
                "cuentas/<int:pk>/activar/",
                admin.site.admin_view(activar_cuenta),
                name="cuentas_activar",
            ),
            path(
                "cuentas/<int:pk>/eliminar/",
                admin.site.admin_view(eliminar_cuenta),
                name="cuentas_eliminar",
            ),
            path(
                "cuentas/<int:pk>/",
                admin.site.admin_view(editar_cuenta),
                name="cuentas_editar",
            ),
        ]
        return extra + original()

    admin.site.get_urls = get_urls
    admin.site._cuentas_registradas = True


registrar_rutas()
