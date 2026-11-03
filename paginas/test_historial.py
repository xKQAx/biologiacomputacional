"""Cada Publicar deja una copia. Restaurar la lleva al borrador, no a la página pública."""

import io
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from paginas.models import BloquePortada, HistorialPagina


def _png(color='red'):
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), color).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class HistorialPublicacionTests(TestCase):
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
            'gestor_historial', 'historial@example.com', 'ClaveSegura1',
            is_staff=True, first_name='Ana', last_name='Ríos',
        )
        self.client.force_login(self.staff)

    def test_publicar_guarda_autor_y_fecha_en_el_editor_y_no_en_el_indice(self):
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Primera versión publicada',
        })
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Segunda versión publicada',
        })
        copias = list(HistorialPagina.objects.filter(pagina='inicio'))
        self.assertEqual(len(copias), 2)
        self.assertEqual(copias[0].autor, self.staff)
        textos = [
            fila['texto']
            for fila in copias[0].contenido
            if fila['clave'] == 'hero_titulo'
        ]
        self.assertEqual(textos, ['Segunda versión publicada'])
        editor = self.client.get(self.editor).content.decode()
        self.assertIn('Publicaciones', editor)
        self.assertIn('Ana Ríos', editor)
        self.assertIn('Restaurar', editor)
        self.assertRegex(editor, r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}')
        self.assertLess(
            editor.find(f'value="restaurar:{copias[0].pk}"'),
            editor.find(f'value="restaurar:{copias[1].pk}"'),
        )

        indice = self.client.get('/admin/')
        self.assertNotContains(indice, 'Restaurar')
        self.assertNotContains(indice, 'acciones recientes')
        self.assertNotContains(indice, 'Primera versión publicada')

    def test_restaurar_copia_al_borrador_y_el_anonimo_sigue_viendo_lo_publicado(self):
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Título que queda en el historial',
        })
        copia = HistorialPagina.objects.get(pagina='inicio')
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Título que ve el visitante',
        })
        respuesta = self.client.post(self.editor, {'accion': f'restaurar:{copia.pk}'}, follow=True)
        self.assertContains(respuesta, 'Versión copiada al borrador')
        self.assertTrue(BloquePortada.objects.filter(
            pagina='inicio', clave='hero_titulo', estado=BloquePortada.Estado.BORRADOR,
            texto='Título que queda en el historial',
        ).exists())
        self.assertTrue(BloquePortada.objects.filter(
            pagina='inicio', clave='hero_titulo', estado=BloquePortada.Estado.PUBLICADO,
            texto='Título que ve el visitante',
        ).exists())
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Título que queda en el historial')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Título que ve el visitante')
        self.assertNotContains(portada, 'Título que queda en el historial')

    def test_descartar_no_borra_el_historial_ni_lo_publicado(self):
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Publicado que se conserva',
        })
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__hero_titulo': 'Borrador que se tira',
        })
        self.client.post(self.editor, {'accion': 'descartar'})
        self.assertEqual(HistorialPagina.objects.filter(pagina='inicio').count(), 1)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Publicado que se conserva')
        self.assertNotContains(portada, 'Borrador que se tira')

    def test_publicar_inicio_no_cambia_servicios_ni_su_historial(self):
        self.client.post(self.editor, {
            'accion': 'publicar',
            'texto__hero_titulo': 'Solo la portada',
        })
        self.assertFalse(HistorialPagina.objects.filter(pagina='servicios').exists())
        self.assertFalse(HistorialPagina.objects.filter(pagina='bases-de-datos').exists())
        self.client.logout()
        servicios = self.client.get('/servicios/')
        self.assertContains(servicios, 'Servicios')
        self.assertNotContains(servicios, 'Solo la portada')

    def test_no_restaura_una_copia_de_otra_pagina(self):
        self.client.post('/admin/pagina/contacto/', {
            'accion': 'publicar',
            'texto__cto_titulo': 'Contacto publicado',
        })
        copia = HistorialPagina.objects.get(pagina='contacto')
        respuesta = self.client.post(
            self.editor, {'accion': f'restaurar:{copia.pk}'}, follow=True,
        )
        self.assertContains(respuesta, 'No se encontró esa publicación')
        self.assertFalse(BloquePortada.objects.filter(
            pagina='inicio', estado=BloquePortada.Estado.BORRADOR, texto='Contacto publicado',
        ).exists())

    def test_la_copia_conserva_la_foto_aunque_la_portada_ya_use_otra(self):
        self.client.post(self.editor, {
            'accion': 'publicar',
            'imagen__tarjeta_profesionales_imagen': _png('blue'),
            'texto__tarjeta_profesionales_imagen': 'Alt de la primera foto',
        })
        primera = HistorialPagina.objects.get(pagina='inicio')
        url_primera = next(
            fila['enlace'] for fila in primera.contenido
            if fila['clave'] == 'tarjeta_profesionales_imagen'
        )
        ruta = Path(self.media_root) / 'portada' / url_primera.rsplit('/', 1)[-1]
        self.client.post(self.editor, {
            'accion': 'publicar',
            'imagen__tarjeta_profesionales_imagen': _png('green'),
            'texto__tarjeta_profesionales_imagen': 'Alt de la foto actual',
        })
        self.assertTrue(ruta.is_file())
        self.client.post(self.editor, {'accion': f'restaurar:{primera.pk}'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Alt de la foto actual')
        self.assertNotContains(portada, 'Alt de la primera foto')
        self.assertNotContains(portada, url_primera)
        self.client.force_login(self.staff)
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, url_primera)
        self.assertContains(lienzo, 'Alt de la primera foto')
