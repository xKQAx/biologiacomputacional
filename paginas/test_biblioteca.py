import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from paginas.models import BloquePortada, ImagenBiblioteca


def _png():
    buffer = io.BytesIO()
    Image.new('RGB', (2, 2), '#285aa5').save(buffer, format='PNG')
    return SimpleUploadedFile('imagen.png', buffer.getvalue(), content_type='image/png')


class BibliotecaImagenesTests(TestCase):
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
        self.url = reverse('admin:pagina_biblioteca_imagenes')
        self.staff = User.objects.create_user(
            'editor_imagenes', 'imagenes@example.org', 'ClaveSegura1', is_staff=True,
        )

    def test_la_biblioteca_requiere_acceso_de_personal(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_personal_puede_subir_imagen_con_texto_alternativo(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(self.url, {
            'nombre': 'Logo del laboratorio',
            'imagen': _png(),
            'texto_alternativo': 'Identidad visual del laboratorio',
        })

        self.assertRedirects(respuesta, self.url)
        imagen = ImagenBiblioteca.objects.get()
        self.assertEqual(imagen.nombre, 'Logo del laboratorio')
        self.assertEqual(imagen.texto_alternativo, 'Identidad visual del laboratorio')
        self.assertEqual(imagen.subida_por, self.staff)

    def test_no_acepta_imagen_sin_alt_ni_archivo_que_no_sea_imagen(self):
        self.client.force_login(self.staff)
        sin_alt = self.client.post(self.url, {
            'nombre': 'Sin descripción', 'imagen': _png(), 'texto_alternativo': '',
        })
        self.assertEqual(sin_alt.status_code, 200)
        self.assertEqual(ImagenBiblioteca.objects.count(), 0)

        archivo_invalido = self.client.post(self.url, {
            'nombre': 'Archivo falso',
            'imagen': SimpleUploadedFile('falso.png', b'no es una imagen', content_type='image/png'),
            'texto_alternativo': 'Imagen falsa',
        })
        self.assertEqual(archivo_invalido.status_code, 200)
        self.assertEqual(ImagenBiblioteca.objects.count(), 0)

    def test_imagen_de_biblioteca_se_ofrece_en_el_inspector_y_alt_faltante_se_reporta(self):
        imagen = ImagenBiblioteca.objects.create(
            nombre='Logo compartido',
            imagen=_png(),
            texto_alternativo='Logo reutilizable',
            subida_por=self.staff,
        )
        BloquePortada.objects.create(
            pagina='inicio', clave='partner_biocom', estado=BloquePortada.Estado.BORRADOR,
            texto='', enlace='/static/images/biocom.png',
        )
        self.client.force_login(self.staff)

        respuesta = self.client.get(reverse('admin:pagina_inicio'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-biblioteca-imagen')
        self.assertContains(respuesta, 'Logo compartido')
        self.assertContains(respuesta, imagen.texto_alternativo)
        self.assertContains(respuesta, 'Revisión antes de publicar')
        self.assertContains(respuesta, 'Logo del laboratorio')
        self.assertContains(respuesta, 'Escritorio, Tablet y Móvil')

    def test_la_direccion_y_alt_de_la_biblioteca_se_guardan_en_el_borrador(self):
        imagen = ImagenBiblioteca.objects.create(
            nombre='Logo compartido', imagen=_png(), texto_alternativo='Logo del equipo',
        )
        self.client.force_login(self.staff)

        respuesta = self.client.post(reverse('admin:pagina_inicio'), {
            'accion': 'guardar',
            'texto__partner_biocom': imagen.texto_alternativo,
            'enlace__partner_biocom': imagen.imagen.url,
        })

        self.assertRedirects(respuesta, reverse('admin:pagina_inicio'))
        guardado = BloquePortada.objects.get(
            pagina='inicio', clave='partner_biocom', estado=BloquePortada.Estado.BORRADOR,
        )
        self.assertEqual(guardado.texto, 'Logo del equipo')
        self.assertEqual(guardado.enlace, imagen.imagen.url)
