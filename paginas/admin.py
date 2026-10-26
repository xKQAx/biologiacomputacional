"""Cuelga el editor de inicio del admin, sin registrar el modelo como formulario suelto."""

from django.contrib import admin


def registrar_rutas():
    if getattr(admin.site, '_portada_registrada', False):
        return

    original = admin.site.get_urls

    def get_urls():
        from django.urls import path

        from paginas.editor import editor_inicio, lienzo_inicio

        # Antes que el resto: son rutas propias, no un modelo del admin.
        extra = [
            path(
                'pagina/inicio/lienzo/',
                admin.site.admin_view(lienzo_inicio),
                name='pagina_inicio_lienzo',
            ),
            path(
                'pagina/inicio/',
                admin.site.admin_view(editor_inicio),
                name='pagina_inicio',
            ),
        ]
        return extra + original()

    admin.site.get_urls = get_urls
    admin.site.index_template = 'admin/indice_biocom.html'
    admin.site._portada_registrada = True


registrar_rutas()
