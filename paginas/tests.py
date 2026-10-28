import io
import json
import re
import shutil
import tempfile
from html import unescape
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from paginas.contenido import MAX_ALT, MAX_ENLACE, MAX_TEXTO
from paginas.imagenes import MAX_IMAGEN
from paginas.models import BloquePortada


def _valor_campo(html, tipo, clave):
    if tipo == 'texto' and f'name="texto__{clave}"' in html:
        area = re.search(
            rf'<textarea[^>]*name="texto__{re.escape(clave)}"[^>]*>(.*?)</textarea>',
            html,
            flags=re.S,
        )
        if area:
            return unescape(area.group(1))
    etiqueta = 'texto' if tipo == 'texto' else 'enlace'
    campo = re.search(
        rf'<input[^>]*name="{etiqueta}__{re.escape(clave)}"[^>]*>',
        html,
    )
    if campo is None:
        return None
    valor = re.search(r'value="([^"]*)"', campo.group(0))
    return unescape(valor.group(1)) if valor else ''


def _png(color='red'):
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), color).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


def _archivo(nombre, contenido, tipo):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


class EditorInicioTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

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

    def _enlace_imagen(self, clave, estado):
        fila = BloquePortada.objects.get(clave=clave, estado=estado)
        self.assertIn('/portada/', fila.enlace)
        return fila.enlace

    def _ruta_subida(self, url):
        return Path(self.media_root) / 'portada' / url.rsplit('/', 1)[-1]

    def test_la_imagen_del_borrador_no_sale_en_la_portada_anonima(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'guardar',
            'imagen__tarjeta_profesionales_imagen': _png(),
            'texto__tarjeta_profesionales_imagen': 'Alt del borrador de la foto',
        })
        self.assertRedirects(respuesta, self.editor)
        url = self._enlace_imagen(
            'tarjeta_profesionales_imagen', BloquePortada.Estado.BORRADOR,
        )
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, url)
        self.assertContains(lienzo, 'alt="Alt del borrador de la foto"')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, url)
        self.assertNotContains(portada, 'Alt del borrador de la foto')
        self.assertContains(portada, 'profesional.jpg')
        self.assertContains(portada, 'alt="Profesionales"')

    def test_publicar_cambia_la_imagen_publica_y_conserva_la_actual_si_no_hay_archivo(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'imagen__tarjeta_profesionales_imagen': _png('blue'),
            'texto__tarjeta_profesionales_imagen': 'Alt publicado de la tarjeta',
        })
        url = self._enlace_imagen(
            'tarjeta_profesionales_imagen', BloquePortada.Estado.PUBLICADO,
        )
        self.assertFalse(
            BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).exists()
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, url)
        self.assertContains(portada, 'alt="Alt publicado de la tarjeta"')
        self.assertNotContains(portada, 'profesional.jpg')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__encontrar_titulo': 'Título sin tocar la foto',
        })
        self.client.logout()
        seguida = self.client.get('/')
        self.assertContains(seguida, url)
        self.assertContains(seguida, 'alt="Alt publicado de la tarjeta"')
        self.assertContains(seguida, 'Título sin tocar la foto')
        self.assertTrue(self._ruta_subida(url).is_file())

    def test_publicar_el_borrador_lleva_su_imagen_sin_volver_a_subirla(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            'imagen__partner_biocom': _png('green'),
        })
        url = self._enlace_imagen('partner_biocom', BloquePortada.Estado.BORRADOR)
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, url)
        self.assertNotContains(portada, 'sigiip.udes.edu.co')

    def test_descartar_no_cambia_la_imagen_publicada(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'imagen__tarjeta_servicios_imagen': _png('blue'),
        })
        publicada = self._enlace_imagen(
            'tarjeta_servicios_imagen', BloquePortada.Estado.PUBLICADO,
        )
        self.client.post(self.editor, {
            'accion': 'guardar',
            'imagen__tarjeta_servicios_imagen': _png('green'),
        })
        borrador = self._enlace_imagen(
            'tarjeta_servicios_imagen', BloquePortada.Estado.BORRADOR,
        )
        self.assertNotEqual(publicada, borrador)
        self.client.post(self.editor, {'accion': 'descartar'})
        self.assertFalse(self._ruta_subida(borrador).exists())
        self.assertTrue(self._ruta_subida(publicada).is_file())
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, publicada)
        self.assertNotContains(portada, borrador)

    def test_un_archivo_que_no_es_imagen_se_rechaza(self):
        self.client.force_login(self.staff)
        antes = set(Path(self.media_root).rglob('*'))
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'imagen__tarjeta_profesionales_imagen': _archivo(
                'nota.txt', b'esto no es una imagen', 'text/plain',
            ),
            'texto__hero_titulo': 'Título que no debe perderse',
            'texto__tarjeta_profesionales_imagen': 'Alt que tampoco se publica',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no es una imagen')
        self.assertContains(respuesta, 'id="error-imagen-tarjeta_profesionales_imagen"')
        self.assertContains(respuesta, 'Título que no debe perderse')
        self.assertContains(respuesta, 'Alt que tampoco se publica')
        self.assertFalse(
            BloquePortada.objects.filter(texto='Título que no debe perderse').exists()
        )
        self.assertEqual(set(Path(self.media_root).rglob('*')), antes)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'profesional.jpg')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertNotContains(portada, 'Alt que tampoco se publica')
        self.assertNotContains(portada, 'Título que no debe perderse')

    def test_una_imagen_demasiado_grande_no_se_guarda_ni_se_publica(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.editor, {
            'accion': 'guardar',
            'imagen__partner_udes': _archivo(
                'grande.png', b'\x89PNG\r\n\x1a\n' + b'a' * (MAX_IMAGEN + 1), 'image/png',
            ),
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'más de 2 MB')
        self.assertContains(respuesta, 'id="error-imagen-partner_udes"')
        self.assertFalse(
            BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).exists()
        )
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'udes-logo-principal.svg')
        self.assertNotContains(portada, '/portada/')

    def test_el_alt_publicado_sale_y_el_del_borrador_no(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__tarjeta_investigacion_imagen': 'Alt publicado de investigación',
        })
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__tarjeta_investigacion_imagen': 'Alt secreto del borrador',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'alt="Alt secreto del borrador"')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'alt="Alt publicado de investigación"')
        self.assertNotContains(portada, 'Alt secreto del borrador')

    def test_un_alt_vacio_no_inventa_texto(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__partner_biocom': '   ',
        })
        self.client.logout()
        html = self.client.get('/').content.decode()
        imagenes = re.findall(r'<img\b[^>]*>', html, flags=re.I)
        logo = next(img for img in imagenes if 'sigiip.udes.edu.co' in img)
        self.assertIn('alt=""', logo)
        self.assertNotIn('Logo Biología Computacional', logo)

    def test_un_alt_demasiado_largo_no_se_guarda_ni_se_publica(self):
        self.client.force_login(self.staff)
        largo = 'á' * (MAX_ALT + 1)
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__tarjeta_servicios_imagen': largo,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, largo)
        self.assertContains(respuesta, f'{MAX_ALT} caracteres')
        self.assertContains(respuesta, 'id="error-texto-tarjeta_servicios_imagen"')
        self.assertFalse(BloquePortada.objects.filter(texto=largo).exists())
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, largo)
        self.assertContains(portada, 'alt="Servicios"')

    def test_los_avisos_de_guardar_publicar_y_descartar_se_ven_en_el_editor(self):
        self.client.force_login(self.staff)
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'name="imagen__partner_biocom"')
        self.assertContains(editor, 'Texto alternativo')
        self.assertContains(editor, 'id="avisos-editor"')
        self.assertContains(editor, 'id="estado-guardado"')

        guardado = self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_titulo': 'Para el aviso de borrador',
        }, follow=True)
        self.assertContains(guardado, 'Borrador guardado. La portada pública no cambió.')
        self.assertContains(guardado, 'class="aviso aviso-success"')

        publicado = self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Para el aviso de publicar',
        }, follow=True)
        self.assertContains(publicado, 'Página de inicio publicada.')
        self.assertContains(publicado, 'class="aviso aviso-success"')

        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_titulo': 'Borrador que se descarta',
        })
        descartado = self.client.post(self.editor, {'accion': 'descartar'}, follow=True)
        self.assertContains(descartado, 'Borrador descartado. La portada publicada sigue igual.')
        self.assertTrue(
            BloquePortada.objects.filter(
                clave='hero_titulo',
                estado=BloquePortada.Estado.PUBLICADO,
                texto='Para el aviso de publicar',
            ).exists()
        )

    def test_al_abrir_no_hay_cambios_respecto_de_lo_guardado(self):
        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_subtitulo_sesion': 'Línea uno\nLínea dos',
            'texto__partner_biocom': 'Logo guardado',
        })
        html = self.client.get(self.editor).content.decode()
        datos = json.loads(re.search(
            r'<script id="estado-guardado" type="application/json">(.*?)</script>',
            html,
            flags=re.S,
        ).group(1))
        self.assertEqual(datos['textos']['hero_subtitulo_sesion'], 'Línea uno\nLínea dos')
        self.assertEqual(_valor_campo(html, 'texto', 'hero_subtitulo_sesion'), 'Línea uno\nLínea dos')
        self.assertEqual(_valor_campo(html, 'texto', 'partner_biocom'), 'Logo guardado')
        self.assertEqual(
            _valor_campo(html, 'enlace', 'partner_biocom'),
            datos['enlaces']['partner_biocom'],
        )
        orden = re.search(r'id="orden-secciones"[^>]*value="([^"]*)"', html)
        self.assertEqual(orden.group(1), datos['orden'])
        for clave, texto in datos['textos'].items():
            self.assertEqual(_valor_campo(html, 'texto', clave), texto)
        for clave, enlace in datos['enlaces'].items():
            self.assertEqual(_valor_campo(html, 'enlace', clave), enlace)

    def test_el_aviso_de_salida_esta_en_el_script_y_no_borra_el_borrador(self):
        from django.contrib.staticfiles import finders

        ruta = finders.find('paginas/editor.js')
        script = Path(ruta).read_text(encoding='utf-8')
        self.assertIn('beforeunload', script)
        self.assertIn('hayCambios', script)
        self.assertNotIn('accion=descartar', script)
        self.assertNotIn("value = \"descartar\"", script)
        self.assertIn('ctrlKey', script)
        self.assertIn('metaKey', script)
        self.assertIn('tecla === "u"', script)
        self.assertIn('underline', script)
        self.assertIn('insertOrderedList', script)
        self.assertIn('removeFormat', script)

    def _fieldset(self, html, clave):
        coincidencia = re.search(
            rf'<fieldset[^>]*data-clave="{re.escape(clave)}".*?</fieldset>',
            html,
            flags=re.S,
        )
        self.assertIsNotNone(coincidencia, clave)
        return coincidencia.group(0)

    def test_la_barra_depende_del_tipo_de_texto(self):
        self.client.force_login(self.staff)
        html = self.client.get(self.editor).content.decode()
        parrafo = self._fieldset(html, 'nosotros_parrafo_1')
        self.assertIn('data-formato="bloque"', parrafo)
        self.assertIn('role="toolbar"', parrafo)
        for boton in ('Negrita', 'Cursiva', 'Subrayado', 'Lista', 'Numerada', 'Enlace', 'Quitar formato'):
            self.assertIn(f'>{boton}<', parrafo)
        self.assertIn('data-fmt="ul"', parrafo)
        self.assertIn('data-fmt="ol"', parrafo)
        self.assertIn('Ctrl+B', parrafo)
        self.assertIn('Ctrl+I', parrafo)
        self.assertIn('Ctrl+U', parrafo)
        for clave in ('hero_titulo', 'nav_inicio', 'hero_cta_registro', 'pie_descripcion'):
            linea = self._fieldset(html, clave)
            self.assertIn('data-formato="linea"', linea, clave)
            self.assertIn('>Subrayado<', linea, clave)
            self.assertIn('>Quitar formato<', linea, clave)
            self.assertNotIn('data-fmt="ul"', linea, clave)
            self.assertNotIn('data-fmt="ol"', linea, clave)
        for clave in ('pie_telefono', 'tarjeta_profesionales_imagen'):
            self.assertNotIn('data-formato', self._fieldset(html, clave), clave)

    def test_se_guardan_los_formatos_permitidos(self):
        from paginas.saneo import PREFIJO_HTML

        self.client.force_login(self.staff)
        marcado = (
            PREFIJO_HTML
            + '<p>Hola <strong>negrita</strong> y <em>cursiva</em></p>'
            + '<ul><li>uno</li></ul>'
            + '<p><a href="https://example.com/lab">sitio</a> '
            + '<a href="mailto:lab@example.com">correo</a></p>'
        )
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__nosotros_parrafo_1': marcado,
        })
        self.assertRedirects(respuesta, self.editor)
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='nosotros_parrafo_1',
            estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertIn('<strong>negrita</strong>', fila.texto)
        self.assertIn('<em>cursiva</em>', fila.texto)
        self.assertIn('<ul><li>uno</li></ul>', fila.texto)
        self.assertIn('href="https://example.com/lab"', fila.texto)
        self.assertIn('href="mailto:lab@example.com"', fila.texto)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '<strong>negrita</strong>')
        self.assertContains(portada, '<em>cursiva</em>')
        self.assertContains(portada, '<ul><li>uno</li></ul>')
        self.assertContains(portada, 'href="https://example.com/lab"')
        self.assertContains(portada, 'href="mailto:lab@example.com"')
        self.assertNotContains(portada, PREFIJO_HTML)
        self.assertNotContains(portada, 'admin/css/')

    def test_se_elimina_un_script_o_un_enlace_javascript(self):
        from paginas.saneo import PREFIJO_HTML

        self.client.force_login(self.staff)
        sucio = (
            PREFIJO_HTML
            + '<p>Visible</p><script>alert(1)</script>'
            + '<a href="javascript:alert(1)">malo</a>'
            + '<a href="JavaScript:alert(2)">otro</a>'
            + '<a href="data:text/html,hi">dato</a>'
            + '<a href="//evil.example">relativo</a>'
            + '<a href="https://seguro.example">bueno</a>'
        )
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__nosotros_parrafo_1': sucio,
        })
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='nosotros_parrafo_1',
            estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertNotIn('<script', fila.texto.lower())
        self.assertNotIn('javascript:', fila.texto.lower())
        self.assertNotIn('data:', fila.texto.lower())
        self.assertNotIn('evil.example', fila.texto)
        self.assertIn('https://seguro.example', fila.texto)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Visible')
        self.assertContains(portada, 'href="https://seguro.example"')
        self.assertNotContains(portada, '<script>alert(1)</script>')
        self.assertNotContains(portada, 'javascript:')
        self.assertNotContains(portada, 'data:text/html')
        self.assertNotContains(portada, 'evil.example')

    def test_el_texto_plano_viejo_no_se_interpreta_como_html(self):
        from paginas.saneo import PREFIJO_HTML

        fila = BloquePortada.objects.get(
            pagina='inicio', clave='nosotros_parrafo_1',
            estado=BloquePortada.Estado.PUBLICADO,
        )
        fila.texto = 'Precio < 10 <script>alert(1)</script>'
        fila.save(update_fields=['texto'])
        portada = self.client.get('/')
        self.assertContains(portada, 'Precio &lt; 10 &lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(portada, '<script>alert(1)</script>')
        self.assertNotContains(portada, PREFIJO_HTML)

        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__pie_telefono': PREFIJO_HTML + '<strong>No</strong>',
        })
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '&lt;strong&gt;No&lt;/strong&gt;')
        self.assertNotContains(portada, '<strong>No</strong>')

    def test_el_titulo_guarda_formato_en_linea_y_descarta_la_lista(self):
        from paginas.saneo import PREFIJO_HTML

        self.client.force_login(self.staff)
        marcado = (
            PREFIJO_HTML
            + '<strong>Hola</strong> <em>mundo</em> <u>raya</u> '
            + '<a href="https://example.com/lab">web</a>'
            + '<ul><li>no</li></ul>'
            + '<script>alert(1)</script>'
            + '<a href="javascript:alert(1)">malo</a>'
        )
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': marcado,
        })
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='hero_titulo',
            estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertIn('<strong>Hola</strong>', fila.texto)
        self.assertIn('<em>mundo</em>', fila.texto)
        self.assertIn('<u>raya</u>', fila.texto)
        self.assertIn('href="https://example.com/lab"', fila.texto)
        self.assertNotIn('<ul', fila.texto)
        self.assertNotIn('<li', fila.texto)
        self.assertNotIn('script', fila.texto.lower())
        self.assertNotIn('javascript:', fila.texto.lower())
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '<strong>Hola</strong>')
        self.assertContains(portada, '<em>mundo</em>')
        self.assertContains(portada, '<u>raya</u>')
        self.assertContains(portada, 'href="https://example.com/lab"')
        self.assertNotContains(portada, '<ul><li>no</li></ul>')
        self.assertNotContains(portada, '<script>alert(1)</script>')
        self.assertNotContains(portada, 'javascript:')
        self.assertNotContains(portada, PREFIJO_HTML)

    def test_el_parrafo_guarda_subrayado_y_lista_numerada(self):
        from paginas.saneo import PREFIJO_HTML

        self.client.force_login(self.staff)
        marcado = PREFIJO_HTML + '<p>Hay <u>subrayado</u></p><ol><li>dos</li></ol>'
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__nosotros_parrafo_1': marcado,
        })
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='nosotros_parrafo_1',
            estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertIn('<u>subrayado</u>', fila.texto)
        self.assertIn('<ol><li>dos</li></ol>', fila.texto)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, '<u>subrayado</u>')
        self.assertContains(portada, '<ol><li>dos</li></ol>')
        self.assertNotContains(portada, PREFIJO_HTML)

    def test_un_anonimo_no_ve_el_borrador_enriquecido(self):
        from paginas.saneo import PREFIJO_HTML

        self.client.force_login(self.staff)
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__nosotros_parrafo_1': PREFIJO_HTML + '<p><strong>Borrador secreto rico</strong></p>',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, '<strong>Borrador secreto rico</strong>')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Borrador secreto rico')
        self.assertContains(portada, 'En Biología Computacional')
