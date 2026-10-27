from django.contrib.auth.models import User
from django.test import TestCase

from paginas.contenido import hay_borrador
from paginas.models import BloquePortada


class _EditorDePagina:
    """Mismo contrato que el editor de inicio, para una página con columna fija."""

    slug = ''
    url_publica = ''
    clave = ''
    texto_fabrica = ''

    def setUp(self):
        self.editor = f'/admin/pagina/{self.slug}/'
        self.lienzo = f'/admin/pagina/{self.slug}/lienzo/'
        self.staff = User.objects.create_user(
            f'gestor_{self.slug.replace("-", "_")}',
            f'{self.slug}@example.com',
            'ClaveSegura1',
            is_staff=True,
        )

    def test_anonimo_no_abre_el_editor_ni_ve_el_borrador(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{self.clave}': 'Borrador secreto que no se publica',
        })
        self.assertTrue(hay_borrador(self.slug))
        self.assertFalse(hay_borrador('inicio'))
        self.client.logout()

        for url in (self.editor, self.lienzo):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn('/admin/login/', respuesta.url)
            self.assertNotContains(
                respuesta, 'Borrador secreto que no se publica', status_code=302,
            )

        publica = self.client.get(self.url_publica)
        self.assertContains(publica, self.texto_fabrica)
        self.assertNotContains(publica, 'Borrador secreto que no se publica')
        self.assertNotContains(publica, 'data-edit-id')

    def test_usuario_sin_staff_no_abre_el_editor(self):
        usuario = User.objects.create_user(
            f'alumno_{self.slug.replace("-", "_")}',
            f'alumno-{self.slug}@example.com',
            'ClaveSegura1',
        )
        self.client.force_login(usuario)
        respuesta = self.client.get(self.editor)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta.url)

    def test_staff_ve_el_editor_sin_barra_ni_flechas(self):
        self.client.force_login(self.staff)
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'Guardar borrador')
        self.assertContains(editor, 'Publicar')
        self.assertContains(editor, 'Descartar')
        self.assertContains(editor, self.lienzo)
        self.assertContains(editor, self.texto_fabrica)
        self.assertNotContains(editor, 'name="texto__nav_inicio"')
        self.assertNotContains(editor, 'name="texto__pie_telefono"')
        self.assertNotContains(editor, 'data-seccion-item')
        self.assertNotContains(editor, 'data-subir')

        indice = self.client.get('/admin/')
        self.assertContains(indice, self.editor)

        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, f'data-edit-id="{self.clave}"')
        self.assertContains(lienzo, self.texto_fabrica)
        self.assertNotContains(lienzo, 'data-edit-id="nav_inicio"')
        self.assertNotContains(lienzo, 'data-edit-id="pie_telefono"')
        self.assertEqual(lienzo.headers['X-Frame-Options'], 'SAMEORIGIN')

    def test_publicar_cambia_el_texto_publico(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{self.clave}': 'Texto publicado de prueba',
        })
        self.assertRedirects(respuesta, self.editor)
        self.assertFalse(BloquePortada.objects.filter(
            pagina=self.slug, estado=BloquePortada.Estado.BORRADOR,
        ).exists())
        self.assertTrue(BloquePortada.objects.filter(
            pagina=self.slug,
            clave=self.clave,
            estado=BloquePortada.Estado.PUBLICADO,
            texto='Texto publicado de prueba',
        ).exists())
        self.client.logout()
        publica = self.client.get(self.url_publica)
        self.assertContains(publica, 'Texto publicado de prueba')
        self.assertNotContains(publica, 'data-edit-id')

    def test_descartar_no_cambia_lo_publicado(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{self.clave}': 'Borrador que se descarta',
        })
        self.client.post(self.editor, {'accion': 'descartar'})
        self.assertFalse(BloquePortada.objects.filter(
            pagina=self.slug, estado=BloquePortada.Estado.BORRADOR,
        ).exists())
        self.client.logout()
        publica = self.client.get(self.url_publica)
        self.assertContains(publica, self.texto_fabrica)
        self.assertNotContains(publica, 'Borrador que se descarta')

    def test_publicar_no_borra_el_borrador_de_inicio(self):
        BloquePortada.objects.create(
            pagina='inicio',
            clave='hero_titulo',
            texto='Borrador de la portada',
            estado=BloquePortada.Estado.BORRADOR,
        )
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{self.clave}': 'Texto publicado de esta página',
        })
        self.assertTrue(BloquePortada.objects.filter(
            pagina='inicio',
            clave='hero_titulo',
            estado=BloquePortada.Estado.BORRADOR,
            texto='Borrador de la portada',
        ).exists())
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertNotContains(portada, 'Borrador de la portada')
        self.assertNotContains(portada, 'Texto publicado de esta página')

    def test_el_lienzo_no_mezcla_el_borrador_de_la_barra(self):
        BloquePortada.objects.create(
            pagina='inicio',
            clave='nav_contacto',
            texto='Borrador de la barra',
            enlace='/contacto/',
            estado=BloquePortada.Estado.BORRADOR,
        )
        self.client.force_login(self.staff)
        lienzo = self.client.get(self.lienzo)
        self.assertNotContains(lienzo, 'Borrador de la barra')
        self.assertNotContains(lienzo, 'data-edit-id="nav_contacto"')


class EditorInvestigacionTests(_EditorDePagina, TestCase):
    slug = 'investigacion'
    url_publica = '/investigacion/'
    clave = 'inv_titulo'
    texto_fabrica = 'INVESTIGACIÓN'

    def test_el_editor_enlaza_el_carrusel_sin_volver_a_publicarlo(self):
        self.client.force_login(self.staff)
        editor = self.client.get(self.editor)
        self.assertContains(editor, '/investigacion/editar-carrusel')
        self.assertNotContains(editor, '/investigacion/carrusel/publicar/')
        self.assertNotContains(editor, 'name="texto1"')
        lienzo = self.client.get(self.lienzo)
        self.assertNotContains(lienzo, 'Vista previa del carrusel')

    def test_el_ancla_de_ver_mas_se_puede_publicar(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__inv_titulo': 'Título publicado de prueba',
            'enlace__inv_ver_mas': '#seccion1',
        })
        self.assertRedirects(respuesta, self.editor)
        self.client.logout()
        pagina = self.client.get(self.url_publica)
        self.assertContains(pagina, 'href="#seccion1"')
        self.assertContains(pagina, 'Título publicado de prueba')

    def test_una_pagina_desconocida_no_abre_editor(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/pagina/no-existe/').status_code, 404)


class EditorProfesionalesTests(_EditorDePagina, TestCase):
    slug = 'profesionales'
    url_publica = '/profesionales/'
    clave = 'prof_titulo'
    texto_fabrica = 'Nuestros Profesionales'


class EditorServiciosTests(_EditorDePagina, TestCase):
    slug = 'servicios'
    url_publica = '/servicios/'
    clave = 'srv_titulo'
    texto_fabrica = 'Servicios'

    def test_publicar_no_cambia_las_bases_de_datos(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__srv_titulo': 'Servicios del laboratorio',
        })
        self.client.logout()
        bases = self.client.get('/servicios/bases-de-datos/')
        self.assertContains(bases, 'Servicios')
        self.assertNotContains(bases, 'Servicios del laboratorio')
        herramientas = self.client.get('/servicios/')
        self.assertContains(herramientas, 'Servicios del laboratorio')


class EditorBasesTests(_EditorDePagina, TestCase):
    slug = 'bases-de-datos'
    url_publica = '/servicios/bases-de-datos/'
    clave = 'db_titulo'
    texto_fabrica = 'Servicios'


class EditorContactoTests(_EditorDePagina, TestCase):
    slug = 'contacto'
    url_publica = '/contacto/'
    clave = 'cto_titulo'
    texto_fabrica = '¿Cómo podemos ayudarte?'

    def test_el_formulario_sigue_en_la_pagina(self):
        pagina = self.client.get(self.url_publica)
        self.assertContains(pagina, 'method="POST"')
        self.assertContains(pagina, 'name="nombres"')
        self.assertContains(pagina, 'name="apellidos"')
        self.assertContains(pagina, 'name="email"')
        self.assertContains(pagina, 'name="telefono"')
        self.assertContains(pagina, 'name="opiniones"')
        self.assertContains(pagina, 'Enviar mensaje')


class IndiceEditoresTests(TestCase):
    def test_el_indice_lista_los_editores_junto_al_de_inicio(self):
        staff = User.objects.create_user(
            'gestor_indice_paginas', 'indice-paginas@example.com', 'ClaveSegura1',
            is_staff=True,
        )
        self.client.force_login(staff)
        indice = self.client.get('/admin/')
        self.assertEqual(indice.status_code, 200)
        html = indice.content.decode()
        enlaces = (
            'Editar página de inicio',
            'Editar página de investigación',
            'Editar página de profesionales',
            'Editar página de servicios',
            'Editar página de bases de datos',
            'Editar página de contacto',
        )
        anterior = -1
        for texto in enlaces:
            posicion = html.find(texto)
            self.assertGreater(posicion, anterior, texto)
            anterior = posicion
        self.assertIn('/admin/pagina/investigacion/', html)
        self.assertIn('/admin/pagina/profesionales/', html)
        self.assertIn('/admin/pagina/servicios/', html)
        self.assertIn('/admin/pagina/bases-de-datos/', html)
        self.assertIn('/admin/pagina/contacto/', html)
