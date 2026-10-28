from django.contrib import admin


def registrar_rutas():
    """Cuelga la bandeja del admin. La bandera evita registrarla dos veces."""
    if getattr(admin.site, '_mensajes_registrados', False):
        return

    original = admin.site.get_urls

    def get_urls():
        from django.urls import path

        from contacto.bandeja import detalle_mensaje, lista_mensajes

        extra = [
            path('mensajes/', admin.site.admin_view(lista_mensajes), name='mensajes'),
            path(
                'mensajes/<int:pk>/',
                admin.site.admin_view(detalle_mensaje),
                name='mensajes_detalle',
            ),
        ]
        return extra + original()

    admin.site.get_urls = get_urls
    admin.site._mensajes_registrados = True


registrar_rutas()
