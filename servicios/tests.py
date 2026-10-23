from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from servicios.models import Categoria, Servicio


class EliminarServicioTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre_categoria='Herramienta')
        self.servicio = Servicio.objects.create(
            categoria=categoria,
            nombre='HerramientaPrueba',
            descrip='Descripción',
            desarrollador='Laboratorio',
            nombre_licencia='MIT',
        )
        self.url = f'/servicios/{self.servicio.nombre}/'
        self.estudiante = User.objects.create_user(
            'estudiante', 'est@example.com', 'ClaveSegura1'
        )
        self.staff = User.objects.create_user(
            'gestor', 'gestor@example.com', 'ClaveSegura1', is_staff=True
        )

    def test_usuario_no_staff_no_puede_borrar(self):
        self.client.force_login(self.estudiante)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Servicio.objects.filter(pk=self.servicio.pk).exists())

    def test_get_no_elimina_el_servicio(self):
        self.client.force_login(self.estudiante)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Servicio.objects.filter(pk=self.servicio.pk).exists())

    def test_staff_borra_por_post(self):
        self.client.force_login(self.staff)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Servicio.objects.filter(pk=self.servicio.pk).exists())


class ArchivoServicioTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre_categoria='Herramienta')
        self.servicio = Servicio.objects.create(
            categoria=categoria,
            nombre='ServicioArchivo',
            descrip='Descripción',
            desarrollador='Laboratorio',
            nombre_licencia='MIT',
        )

    def test_rechaza_un_html(self):
        self.servicio.archivo = SimpleUploadedFile(
            'malo.html', b'<p>x</p>', content_type='text/html'
        )
        with self.assertRaises(ValidationError):
            self.servicio.full_clean()

    def test_acepta_un_zip(self):
        self.servicio.archivo = SimpleUploadedFile(
            'paquete.zip', b'PK', content_type='application/zip'
        )
        self.servicio.full_clean()
