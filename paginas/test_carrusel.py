"""El carrusel del editor de páginas. No es el de /investigacion/editar-carrusel."""

import io
import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from investigacion.models import Carrusel
from paginas.models import BloquePortada, HistorialPagina


def _png(color='red'):
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), color).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class CarruselSeccionTests(TestCase):
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
            'gestor_carrusel', 'carrusel@example.com', 'ClaveSegura1', is_staff=True,
        )
        self.client.force_login(self.staff)

    def test_se_agrega_como_las_otras_secciones_y_no_toca_el_carrusel_de_investigacion(self):
        self.assertEqual(Carrusel.objects.count(), 0)
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'Carrusel')
        investigacion = self.client.get('/admin/pagina/investigacion/')
        self.assertContains(investigacion, 'Editar carrusel')
        self.assertNotContains(investigacion, 'name="tipo_pieza"')

        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'carrusel'})
        pieza = self._id()
        editor = self.client.get(self.editor)
        self.assertContains(editor, f'value="dia-agregar:{pieza}"')
        self.assertContains(editor, 'Agregar diapositiva')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, f'data-seccion="{pieza}"')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertEqual(Carrusel.objects.count(), 0)

    def test_el_borrador_no_sale_y_al_publicar_se_ven_orden_alt_y_enlace(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'carrusel'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'dia-agregar:{pieza}'})
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'imagen__{pieza}-d01': _png('blue'),
            f'texto__{pieza}-d01': 'Alt de la primera',
            f'enlace__{pieza}-r01': 'https://example.com/primera',
            f'imagen__{pieza}-d02': _png('green'),
            f'texto__{pieza}-d02': 'Alt de la segunda',
        })
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Alt de la primera')
        self.assertNotContains(portada, 'Alt de la segunda')
        self.assertNotContains(portada, 'example.com/primera')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': f'dia-subir:{pieza}:02'})
        self.client.post(self.editor, {'accion': 'publicar'})
        self.assertEqual(Carrusel.objects.count(), 0)
        self.client.logout()
        publicada = self.client.get('/').content.decode()
        self.assertLess(
            publicada.find('alt="Alt de la segunda"'),
            publicada.find('alt="Alt de la primera"'),
        )
        self.assertIn('href="https://example.com/primera"', publicada)
        self.assertIn('Anterior', publicada)
        self.assertIn('Siguiente', publicada)
        servicios = self.client.get('/servicios/')
        self.assertNotContains(servicios, 'Alt de la primera')
        self.assertNotContains(servicios, 'example.com/primera')

    def test_un_enlace_javascript_no_se_guarda_y_el_alt_no_se_ejecuta(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'carrusel'})
        pieza = self._id()
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'imagen__{pieza}-d01': _png('red'),
            f'texto__{pieza}-d01': '<script>alert(1)</script>',
        })
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            f'enlace__{pieza}-r01': 'javascript:alert(1)',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(BloquePortada.objects.filter(
            pagina='inicio', clave=f'{pieza}-r01', estado=BloquePortada.Estado.PUBLICADO,
        ).exists())
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'alt="&lt;script&gt;alert(1)&lt;/script&gt;"')
        self.assertNotContains(portada, 'javascript:')
        self.assertNotContains(portada, 'alt="<script>alert(1)</script>"')

    def test_no_se_quita_la_ultima_diapositiva_y_descartar_conserva_la_foto_publicada(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'carrusel'})
        pieza = self._id()
        respuesta = self.client.post(self.editor, {'accion': f'dia-quitar:{pieza}:01'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'al menos una diapositiva')

        self.client.post(self.editor, {
            'accion': 'publicar',
            f'imagen__{pieza}-d01': _png('blue'),
            f'texto__{pieza}-d01': 'Alt publicado del carrusel',
        })
        publicada = BloquePortada.objects.get(
            pagina='inicio', clave=f'{pieza}-d01', estado=BloquePortada.Estado.PUBLICADO,
        )
        ruta = Path(self.media_root) / 'portada' / publicada.enlace.rsplit('/', 1)[-1]
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'imagen__{pieza}-d01': _png('green'),
            f'texto__{pieza}-d01': 'Alt solo del borrador',
        })
        self.client.post(self.editor, {'accion': 'descartar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'alt="Alt publicado del carrusel"')
        self.assertContains(portada, publicada.enlace)
        self.assertNotContains(portada, 'Alt solo del borrador')
        self.assertTrue(ruta.is_file())

    def test_restaurar_el_carrusel_no_cambia_lo_publicado(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'carrusel'})
        pieza = self._id()
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'imagen__{pieza}-d01': _png('blue'),
            f'texto__{pieza}-d01': 'Alt de la copia',
        })
        copia = HistorialPagina.objects.get(pagina='inicio')
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{pieza}-d01': 'Alt que ve el visitante',
        })
        self.client.post(self.editor, {'accion': f'restaurar:{copia.pk}'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Alt que ve el visitante')
        self.assertNotContains(portada, 'Alt de la copia')
        self.client.force_login(self.staff)
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Alt de la copia')

    def _id(self):
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='composicion', estado=BloquePortada.Estado.BORRADOR,
        )
        return json.loads(fila.texto)['piezas'][0]['id']
