"""Cuelga el editor de páginas del admin, sin registrar el modelo como formulario suelto."""

from django.contrib import admin


def registrar_rutas():
    if getattr(admin.site, '_portada_registrada', False):
        return

    original = admin.site.get_urls

    def get_urls():
        from django.urls import path

        from paginas.editor import editor_inicio, editor_pagina, lienzo_inicio, lienzo_pagina

        # Antes que el resto: son rutas propias, no un modelo del admin.
        # Inicio va primero para conservar sus nombres. El resto usa el mismo editor.
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
            path(
                'pagina/<slug:pagina>/lienzo/',
                admin.site.admin_view(lienzo_pagina),
                name='pagina_lienzo',
            ),
            path(
                'pagina/<slug:pagina>/',
                admin.site.admin_view(editor_pagina),
                name='pagina_editor',
            ),
        ]
        return extra + original()

    admin.site.get_urls = get_urls
    admin.site.index_template = 'admin/indice_biocom.html'
    admin.site._portada_registrada = True


registrar_rutas()
