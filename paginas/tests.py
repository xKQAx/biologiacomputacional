from django.contrib.auth.models import User
from django.test import TestCase

from paginas.contenido import MAX_ENLACE, MAX_TEXTO
from paginas.models import BloquePortada


class EditorInicioTests(TestCase):
    def setUp(self):
        self.editor = '/admin/pagina/inicio/'
        self.lienzo = '/admin/pagina/inicio/lienzo/'
        self.staff = User.objects.create_user(
            'gestor_portada', 'portada@example.com', 'ClaveSegura1', is_staff=True,
        )

    def test_anonimo_no_abre_el_editor_ni_el_lienzo_con_borrador(self):
        BloquePortada.objects.create(
            clave='hero_titulo',
            texto='Borrador secreto del lienzo',
            estado=BloquePortada.Estado.BORRADOR,
            orden=20,
        )
        for url in (self.editor, self.lienzo):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn('/admin/login/', respuesta.url)
            self.assertNotIn('Borrador secreto del lienzo', respuesta.content.decode())

    def test_usuario_sin_staff_no_abre_el_editor(self):
        usuario = User.objects.create_user(
            'alumno_portada', 'alumno_portada@example.com', 'ClaveSegura1',
        )
        self.client.force_login(usuario)
        respuesta = self.client.get(self.editor)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta.url)

    def test_staff_ve_el_editor_y_el_indice(self):
        self.client.force_login(self.staff)
        indice = self.client.get('/admin/')
        self.assertContains(indice, 'Editar página de inicio')
        self.assertContains(indice, self.editor)

        editor = self.client.get(self.editor)
        self.assertContains(editor, 'Guardar borrador')
        self.assertContains(editor, 'Publicar')
        self.assertContains(editor, 'Descartar')
        self.assertContains(editor, self.lienzo)
        self.assertContains(editor, 'Encabezado · Título')
        self.assertContains(editor, 'Barra de navegación · Inicio')
        self.assertContains(editor, 'Pie de página · Teléfono')
        self.assertContains(
            editor,
            'value="encabezado,instituciones,caracteristicas,encontrar,nosotros,beneficios,llamado"',
        )

        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'data-edit-id="hero_titulo"')
        self.assertContains(lienzo, 'Ciencia e Innovación')
        self.assertEqual(lienzo.headers['X-Frame-Options'], 'SAMEORIGIN')

    def test_la_portada_muestra_el_texto_actual(self):
        portada = self.client.get('/')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertContains(portada, 'Regístrate gratis')
        self.assertContains(portada, '¿Qué puedo encontrar en BioCOM?')
        self.assertContains(portada, 'Conectando Ciencia e Innovación')
        self.assertNotContains(portada, 'data-edit-id')

    def test_sin_publicado_la_portada_no_queda_en_blanco(self):
        BloquePortada.objects.all().delete()
        portada = self.client.get('/')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertContains(portada, 'Regístrate gratis')
        self.assertContains(portada, 'herramientas')

    def test_visitante_y_sesion_ven_su_propio_texto(self):
        anonima = self.client.get('/')
        self.assertContains(anonima, 'Regístrate gratis')
        self.assertContains(anonima, '¿Listo para comenzar?')
        self.assertNotContains(anonima, 'Contáctanos')

        usuario = User.objects.create_user(
            'alumno_inicio', 'alumno_inicio@example.com', 'ClaveSegura1',
        )
        self.client.force_login(usuario)
        sesion = self.client.get('/')
        self.assertContains(sesion, 'Contáctanos')
        self.assertContains(sesion, 'Ver profesionales')
        self.assertNotContains(sesion, 'Regístrate gratis')
        self.assertNotContains(sesion, '¿Listo para comenzar?')

    def test_el_borrador_no_sale_en_la_portada_anonima(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_titulo': 'Borrador que no debe publicarse',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Borrador que no debe publicarse')
        self.assertContains(lienzo, 'Regístrate gratis')

        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertNotContains(portada, 'Borrador que no debe publicarse')

    def test_publicar_cambia_el_texto_publico(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Título publicado de prueba',
        })
        self.assertRedirects(respuesta, self.editor)
        self.assertFalse(
            BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).exists()
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Título publicado de prueba')
        self.assertContains(
            portada,
            '<span data-edit-texto>Título publicado de prueba</span>',
            html=False,
        )

    def test_descartar_no_cambia_lo_publicado(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__encontrar_titulo': 'Borrador descartable',
        })
        self.client.post(self.editor, {'accion': 'descartar'})
        self.assertFalse(
            BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).exists()
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '¿Qué puedo encontrar en BioCOM?')
        self.assertNotContains(portada, 'Borrador descartable')

    def test_un_enlace_javascript_no_se_publica(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'enlace__hero_cta_registro': 'javascript:alert(1)',
            'texto__hero_titulo': 'Título que no debe perderse',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'javascript:alert(1)')
        self.assertContains(respuesta, 'Título que no debe perderse')
        self.assertContains(respuesta, 'debe ser una ruta')
        self.assertFalse(
            BloquePortada.objects.filter(texto='Título que no debe perderse').exists()
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'javascript:')
        self.assertNotContains(portada, 'Título que no debe perderse')
        self.assertContains(portada, '/identity/register/')

    def test_un_enlace_externo_con_doble_barra_no_se_publica(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'enlace__partner_biocom': '//evil.example/logo.png',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '//evil.example/logo.png')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'evil.example')

    def test_un_enlace_vacio_conserva_el_anterior(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'enlace__hero_cta_registro': '   ',
        })
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '/identity/register/')

    def test_un_texto_demasiado_largo_no_se_recorta(self):
        self.client.force_login(self.staff)
        largo = 'á' * (MAX_TEXTO + 1)
        respuesta = self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_titulo': largo,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-pendiente="1"')
        self.assertContains(respuesta, largo)
        self.assertContains(respuesta, f'{MAX_TEXTO} caracteres')
        self.assertFalse(BloquePortada.objects.filter(texto=largo).exists())
        self.assertFalse(BloquePortada.objects.filter(texto=largo[:MAX_TEXTO]).exists())

    def test_un_enlace_demasiado_largo_no_se_recorta(self):
        self.client.force_login(self.staff)
        largo = 'https://example.com/' + ('a' * MAX_ENLACE)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'enlace__hero_cta_registro': largo,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, largo)
        self.assertContains(respuesta, f'{MAX_ENLACE} caracteres')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '/identity/register/')
        self.assertNotContains(portada, 'example.com')

    def test_los_saltos_de_linea_se_publican_escapados(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__nosotros_parrafo_1': 'Línea uno\n<b>Línea dos</b>',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(
            lienzo,
            'data-edit-id="nosotros_parrafo_1" data-edit-grupo="nosotros" data-edit-multilinea="1"',
        )
        self.assertContains(
            lienzo,
            'data-edit-id="hero_titulo" data-edit-grupo="encabezado"',
        )
        self.assertNotContains(
            lienzo,
            'data-edit-id="hero_titulo" data-edit-grupo="encabezado" data-edit-multilinea',
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Línea uno<br>&lt;b&gt;Línea dos&lt;/b&gt;')
        self.assertNotContains(portada, '<b>Línea dos</b>')

    def _posicion(self, html, marca):
        posicion = html.find(marca)
        self.assertGreater(posicion, -1, marca)
        return posicion

    def test_sin_publicado_se_conservan_barra_pie_y_orden(self):
        portada = self.client.get('/')
        self.assertContains(portada, 'Registrarme')
        self.assertContains(portada, 'Términos de Servicio')
        self.assertContains(portada, 'Campus Universitario Lagos del Cacique')
        self.assertContains(portada, 'href="#"')
        self.assertNotContains(portada, 'data-edit-id')
        html = portada.content.decode()
        anterior = -1
        for seccion in (
            'encabezado', 'instituciones', 'caracteristicas', 'encontrar',
            'nosotros', 'beneficios', 'llamado',
        ):
            posicion = self._posicion(html, f'data-seccion="{seccion}"')
            self.assertGreater(posicion, anterior)
            anterior = posicion

        otra = self.client.get('/politicas_privacidad/')
        self.assertContains(otra, 'Registrarme')
        self.assertContains(otra, 'PBX: +57 607 6516500')
        self.assertNotContains(otra, 'data-edit-id')

    def test_el_orden_del_borrador_no_cambia_la_portada_hasta_publicar(self):
        borrador = 'nosotros,encabezado,instituciones,caracteristicas,encontrar,beneficios,llamado'
        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'guardar', 'orden_secciones': borrador})
        editor = self.client.get(self.editor).content.decode()
        self.assertLess(
            self._posicion(editor, 'data-seccion-item="nosotros"'),
            self._posicion(editor, 'data-seccion-item="encabezado"'),
        )
        lienzo = self.client.get(self.lienzo).content.decode()
        self.assertLess(
            self._posicion(lienzo, 'data-seccion="nosotros"'),
            self._posicion(lienzo, 'data-seccion="encabezado"'),
        )
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertLess(
            self._posicion(portada, 'data-seccion="encabezado"'),
            self._posicion(portada, 'data-seccion="nosotros"'),
        )

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'publicar', 'orden_secciones': borrador})
        self.client.logout()
        publicada = self.client.get('/').content.decode()
        self.assertLess(
            self._posicion(publicada, 'data-seccion="nosotros"'),
            self._posicion(publicada, 'data-seccion="encabezado"'),
        )

    def test_descartar_vuelve_al_orden_publicado(self):
        publicado = 'beneficios,encabezado,instituciones,caracteristicas,encontrar,nosotros,llamado'
        borrador = 'llamado,encabezado,instituciones,caracteristicas,encontrar,nosotros,beneficios'
        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'publicar', 'orden_secciones': publicado})
        self.client.post(self.editor, {'accion': 'guardar', 'orden_secciones': borrador})
        self.client.post(self.editor, {'accion': 'descartar'})
        lienzo = self.client.get(self.lienzo).content.decode()
        self.assertLess(
            self._posicion(lienzo, 'data-seccion="beneficios"'),
            self._posicion(lienzo, 'data-seccion="encabezado"'),
        )
        self.assertLess(
            self._posicion(lienzo, 'data-seccion="nosotros"'),
            self._posicion(lienzo, 'data-seccion="llamado"'),
        )
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertLess(
            self._posicion(portada, 'data-seccion="beneficios"'),
            self._posicion(portada, 'data-seccion="encabezado"'),
        )

    def test_un_orden_que_mezcla_la_barra_no_se_publica(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'orden_secciones': 'barra,encabezado,pie',
            'texto__hero_titulo': 'No debe publicarse por el orden',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no es válido')
        self.assertFalse(
            BloquePortada.objects.filter(texto='No debe publicarse por el orden').exists()
        )
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertNotIn('No debe publicarse por el orden', portada)
        self.assertLess(
            self._posicion(portada, 'data-seccion="encabezado"'),
            self._posicion(portada, 'data-seccion="instituciones"'),
        )

    def test_barra_y_pie_publicados_se_ven_en_otra_pagina_y_el_borrador_no(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__nav_contacto': 'Escríbenos ya',
            'texto__pie_telefono': 'PBX: +57 607 0000000',
            'enlace__pie_legal_terminos': 'https://example.com/terminos',
        })
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__nav_contacto': 'Borrador de la barra',
            'texto__pie_telefono': 'Teléfono que no debe verse',
            'enlace__pie_facebook': 'https://example.com/borrador-red',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Borrador de la barra')
        self.assertContains(lienzo, 'Teléfono que no debe verse')
        self.assertContains(lienzo, 'https://example.com/borrador-red')
        self.assertContains(lienzo, 'data-edit-id="nav_contacto"')
        self.assertContains(lienzo, 'data-edit-id="pie_telefono"')
        self.client.logout()

        for url in ('/', '/politicas_privacidad/', '/contacto/'):
            pagina = self.client.get(url)
            self.assertContains(pagina, 'Escríbenos ya')
            self.assertContains(pagina, 'PBX: +57 607 0000000')
            self.assertContains(pagina, 'https://example.com/terminos')
            self.assertNotContains(pagina, 'Borrador de la barra')
            self.assertNotContains(pagina, 'Teléfono que no debe verse')
            self.assertNotContains(pagina, 'borrador-red')
            self.assertNotContains(pagina, 'data-edit-id')

    def test_publicar_sin_cambios_conserva_el_subtitulo(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'text-warning fw-bold')
        self.assertContains(portada, 'herramientas')
        self.assertContains(portada, 'recursos')
