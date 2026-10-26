import io
import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from investigacion.models import CategoriaI, Carrusel, CarruselBorrador, Investigacion


def _png():
    buffer = io.BytesIO()
    Image.new('RGB', (1, 1)).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class _MediaAislada:
    """Carpeta temporal de media para que ImageField no escriba en el proyecto."""

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


class EliminarInvestigacionTests(_MediaAislada, TestCase):
    def setUp(self):
        categoria = CategoriaI.objects.create(nombre_categoria='Otros')
        self.investigacion = Investigacion.objects.create(
            categoria=categoria,
            nombre='ProyectoPrueba',
            descrip='Descripción',
            imagen_investigacion=_png(),
        )
        self.url = f'/investigacion/{self.investigacion.nombre}/eliminar/'
        self.staff = User.objects.create_user(
            'gestor_inv', 'inv@example.com', 'ClaveSegura1', is_staff=True
        )
        self.estudiante = User.objects.create_user(
            'estudiante_inv', 'einv@example.com', 'ClaveSegura1'
        )

    def test_get_de_staff_no_elimina(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            Investigacion.objects.filter(pk=self.investigacion.pk).exists()
        )

    def test_post_de_usuario_no_staff_no_elimina(self):
        self.client.force_login(self.estudiante)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Investigacion.objects.filter(pk=self.investigacion.pk).exists()
        )

    def test_post_de_staff_elimina(self):
        self.client.force_login(self.staff)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Investigacion.objects.filter(pk=self.investigacion.pk).exists()
        )

    def test_el_pdf_solo_acepta_pdf(self):
        self.investigacion.pdf = SimpleUploadedFile(
            'malo.html', b'<p>x</p>', content_type='text/html'
        )
        with self.assertRaises(ValidationError):
            self.investigacion.full_clean()

        self.investigacion.pdf = SimpleUploadedFile(
            'ok.pdf', b'%PDF-1.4', content_type='application/pdf'
        )
        self.investigacion.full_clean()


class PaginaInvestigacionTests(_MediaAislada, TestCase):
    def _investigacion(self, categoria, nombre):
        return Investigacion.objects.create(
            categoria=categoria,
            nombre=nombre,
            descrip='Descripción',
            imagen_investigacion=_png(),
        )

    def test_una_categoria_nueva_aparece_en_la_pagina(self):
        nueva = CategoriaI.objects.create(nombre_categoria='Genómica')
        cry = CategoriaI.objects.create(nombre_categoria='Cry11')
        self._investigacion(nueva, 'ProyectoNuevo')
        self._investigacion(cry, 'ProyectoCry')

        response = self.client.get('/investigacion/')

        self.assertContains(response, 'Resultados para ProyectoNuevo')
        self.assertContains(response, 'Genómica')
        self.assertContains(response, 'A30P PDF')
        self.assertContains(response, 'order-1')
        self.assertNotContains(response, 'Editar investigación')

    def test_superusuario_sin_staff_puede_editar(self):
        categoria = CategoriaI.objects.create(nombre_categoria='Otros')
        self._investigacion(categoria, 'ProyectoStaff')
        gestor = User.objects.create_user(
            'super_sin_staff', 'sns@example.com', 'ClaveSegura1',
            is_staff=False, is_superuser=True,
        )
        self.client.force_login(gestor)

        response = self.client.get('/investigacion/')

        self.assertContains(response, 'Editar investigación')


class InvestigacionPublicaTests(_MediaAislada, TestCase):
    """La portada pública no debe mostrar un carrusel sin fotos."""

    def _carrusel(self, **textos):
        datos = {
            'titulo': 'Carrusel de prueba',
            'texto1': 'Texto de la primera diapositiva',
            'texto2': 'Texto de la segunda diapositiva',
            'texto3': 'Texto de la tercera diapositiva',
            'imagen1': _png(),
            'imagen2': _png(),
            'imagen3': _png(),
        }
        datos.update(textos)
        return Carrusel.objects.create(**datos)

    def test_sin_carrusel_no_pinta_imagenes_vacias(self):
        response = self.client.get('/investigacion/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="carouselExampleFade"')
        self.assertNotContains(response, 'src=""')
        self.assertContains(response, 'INVESTIGACIÓN')
        self.assertNotContains(response, 'Editar carrusel')

    def test_staff_sin_carrusel_puede_abrir_el_editor(self):
        staff = User.objects.create_user(
            'gestor_sin_carrusel', 'sincarrusel@example.com', 'ClaveSegura1', is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get('/investigacion/')
        self.assertContains(response, 'Editar carrusel')
        self.assertNotContains(response, 'id="carouselExampleFade"')

    def test_muestra_solo_las_imagenes_que_existen(self):
        carrusel = self._carrusel()
        os.remove(carrusel.imagen2.path)
        os.remove(carrusel.imagen3.path)

        response = self.client.get('/investigacion/')
        self.assertContains(response, carrusel.imagen1.url)
        self.assertContains(response, 'Carrusel de prueba')
        self.assertContains(response, 'Texto de la primera diapositiva')
        self.assertNotContains(response, carrusel.imagen2.url)
        self.assertNotContains(response, 'Diapositiva siguiente')

    def test_varias_imagenes_tienen_controles_en_espanol(self):
        carrusel = self._carrusel()
        response = self.client.get('/investigacion/')
        self.assertContains(response, carrusel.imagen1.url)
        self.assertContains(response, carrusel.imagen2.url)
        self.assertContains(response, carrusel.imagen3.url)
        self.assertContains(response, 'Diapositiva anterior')
        self.assertContains(response, 'Diapositiva siguiente')
        self.assertNotContains(response, '>Previous<')
        self.assertNotContains(response, '>Next<')
        self.assertNotContains(response, 'Editar carrusel')

    def test_staff_ve_editar_cuando_hay_carrusel(self):
        self._carrusel()
        staff = User.objects.create_user(
            'gestor_carrusel', 'carrusel@example.com', 'ClaveSegura1', is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get('/investigacion/')
        self.assertContains(response, 'Editar carrusel')


class CarruselBorradorTests(_MediaAislada, TestCase):
    """El borrador del carrusel no se publica hasta que el staff lo confirma."""

    edit_url = '/investigacion/editar-carrusel'
    preview_url = '/investigacion/carrusel/vista-previa/'
    publish_url = '/investigacion/carrusel/publicar/'
    discard_url = '/investigacion/carrusel/descartar/'

    def setUp(self):
        self.staff = User.objects.create_user(
            'editor_carrusel', 'editor-carrusel@example.com', 'ClaveSegura1',
            is_staff=True,
        )
        self.carrusel = Carrusel.objects.create(
            titulo='Título publicado',
            texto1='Texto publicado visible',
            texto2='Segunda publicada',
            texto3='Tercera publicada',
            imagen1=_png(),
            imagen2=_png(),
            imagen3=_png(),
        )

    def _datos(self, texto1):
        return {
            'accion': 'guardar',
            'titulo': 'Título del borrador',
            'texto1': texto1,
            'texto2': 'Segunda del borrador',
            'texto3': 'Tercera del borrador',
        }

    def _guardar(self, texto1='Texto secreto del borrador'):
        self.client.force_login(self.staff)
        response = self.client.post(self.edit_url, self._datos(texto1))
        self.assertEqual(response.status_code, 302)
        return response

    def test_anonimo_no_ve_el_borrador(self):
        self._guardar()
        self.client.logout()

        portada = self.client.get('/investigacion/')
        self.assertContains(portada, 'Texto publicado visible')
        self.assertNotContains(portada, 'Texto secreto del borrador')
        self.assertNotContains(portada, 'noindex')

        for url in (self.preview_url, self.edit_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertNotContains(response, 'Texto secreto del borrador', status_code=302)

    def test_staff_previsualiza_sin_publicar(self):
        self._guardar()
        response = self.client.get(self.preview_url)

        self.assertContains(response, 'Texto secreto del borrador')
        self.assertContains(response, 'INVESTIGACIÓN')
        self.assertContains(response, 'Vista previa del carrusel')
        self.assertContains(response, 'name="robots" content="noindex, nofollow"')
        self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertNotContains(response, 'Texto publicado visible')

        portada = self.client.get('/investigacion/')
        self.assertContains(portada, 'Texto publicado visible')
        self.assertNotContains(portada, 'Texto secreto del borrador')
        self.assertNotContains(portada, 'noindex')

    def test_publicar_actualiza_lo_publico(self):
        self._guardar()
        response = self.client.post(self.publish_url)

        self.assertRedirects(response, '/investigacion/')
        portada = self.client.get('/investigacion/')
        self.assertContains(portada, 'Texto secreto del borrador')
        self.assertNotContains(portada, 'Texto publicado visible')
        self.assertFalse(CarruselBorrador.objects.exists())

        publicado = Carrusel.objects.get(pk=self.carrusel.pk)
        self.assertTrue(os.path.exists(publicado.imagen1.path))

    def test_descartar_no_cambia_lo_publicado(self):
        ruta = self.carrusel.imagen1.path
        self._guardar()
        response = self.client.post(self.discard_url)

        self.assertRedirects(response, self.edit_url)
        self.assertFalse(CarruselBorrador.objects.exists())
        self.carrusel.refresh_from_db()
        self.assertEqual(self.carrusel.texto1, 'Texto publicado visible')
        self.assertTrue(os.path.exists(ruta))

        portada = self.client.get('/investigacion/')
        self.assertContains(portada, 'Texto publicado visible')
        self.assertNotContains(portada, 'Texto secreto del borrador')

        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.status_code, 302)
        self.assertNotContains(preview, 'Texto secreto del borrador', status_code=302)

    def test_validacion_conserva_el_texto_y_no_crea_borrador(self):
        self.client.force_login(self.staff)
        datos = self._datos('no se guarda')
        datos['texto1'] = ''
        datos['texto2'] = 'Texto que no debo perder'
        response = self.client.post(self.edit_url, datos)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Texto que no debo perder')
        self.assertContains(response, 'Escribe el texto de la diapositiva 1.')
        self.assertFalse(CarruselBorrador.objects.exists())
        self.carrusel.refresh_from_db()
        self.assertEqual(self.carrusel.texto1, 'Texto publicado visible')
