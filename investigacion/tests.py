import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from investigacion.models import CategoriaI, Investigacion


def _png():
    buffer = io.BytesIO()
    Image.new('RGB', (1, 1)).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class EliminarInvestigacionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # El ImageField no debe escribir en profesionales/media del proyecto.
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

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


class PaginaInvestigacionTests(TestCase):
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
