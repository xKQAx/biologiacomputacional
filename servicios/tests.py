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


class CatalogoPublicoTests(TestCase):
    def test_catalogo_vacio_explica_que_no_hay_publicaciones(self):
        herramientas = self.client.get('/servicios/')
        bases = self.client.get('/servicios/bases-de-datos/')

        self.assertContains(herramientas, 'Aún no hay herramientas publicadas.')
        self.assertNotContains(herramientas, 'No se encontraron herramientas.')
        self.assertContains(bases, 'Aún no hay bases de datos publicadas.')
        self.assertContains(herramientas, 'aria-current="page"')

    def test_busqueda_sin_resultados_no_usa_el_mensaje_de_catalogo_vacio(self):
        herramientas = self.client.get('/servicios/', {'q': 'no-existe'})
        bases = self.client.get('/servicios/bases-de-datos/', {'q': 'no-existe'})

        self.assertContains(herramientas, 'No se encontraron herramientas para esta búsqueda.')
        self.assertContains(herramientas, 'value="no-existe"')
        self.assertNotContains(herramientas, 'Aún no hay herramientas publicadas.')
        self.assertContains(bases, 'No se encontraron bases de datos para esta búsqueda.')
        self.assertContains(bases, 'value="no-existe"')
        self.assertNotContains(bases, 'Aún no hay bases de datos publicadas.')


class MetadatosServicioTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre_categoria='Herramienta')
        self.servicio = Servicio.objects.create(
            categoria=self.categoria,
            nombre='Analizador',
            descrip='Analiza secuencias.',
            desarrollador='Laboratorio',
            nombre_licencia='MIT',
            version='2.1',
            compatibilidad='Linux y macOS',
            requisitos='Python 3.12',
            instrucciones='Instala las dependencias y ejecuta el programa.',
            documentacion_url='https://example.org/docs',
            citacion='Cita el artículo del método.',
            fecha_actualizacion='2026-04-03',
        )
        self.usuario = User.objects.create_user(
            'lector', 'lector@example.com', 'ClaveSegura1'
        )

    def test_los_metadatos_se_muestran_en_la_ficha_publica(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(f'/servicios/{self.servicio.nombre}/')

        self.assertEqual(respuesta.status_code, 200)
        for texto in (
            'Detalles para usar el recurso', '2.1', 'Linux y macOS',
            'Python 3.12', 'Instala las dependencias',
            'Consultar documentación', 'Cita el artículo del método.', '03/04/2026',
        ):
            self.assertContains(respuesta, texto)

    def test_los_metadatos_son_opcionales_para_registros_existentes(self):
        servicio = Servicio.objects.create(
            categoria=self.categoria,
            nombre='Recurso anterior',
            descrip='Sin detalles técnicos.',
            desarrollador='Laboratorio',
            nombre_licencia='MIT',
        )
        self.client.force_login(self.usuario)
        respuesta = self.client.get(f'/servicios/{servicio.nombre}/')

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'Detalles para usar el recurso')

    def test_formulario_de_alta_guarda_los_metadatos(self):
        gestor = User.objects.create_user(
            'gestor', 'gestor@example.com', 'ClaveSegura1', is_staff=True
        )
        self.client.force_login(gestor)
        respuesta = self.client.post('/servicios/nuevo-servicio/', {
            'categoria': self.categoria.pk,
            'nombre': 'Nuevo analizador',
            'descrip': 'Descripción.',
            'desarrollador': 'Equipo',
            'nombre_licencia': 'MIT',
            'version': '1.0',
            'compatibilidad': 'Linux',
            'requisitos': 'Python',
            'instrucciones': 'Ejecutar.',
            'documentacion_url': 'https://example.org/manual',
            'citacion': 'Cita sugerida.',
            'fecha_actualizacion': '2026-05-12',
        })

        self.assertEqual(respuesta.status_code, 302)
        servicio = Servicio.objects.get(nombre='Nuevo analizador')
        self.assertEqual(servicio.version, '1.0')
        self.assertEqual(servicio.compatibilidad, 'Linux')
        self.assertEqual(servicio.documentacion_url, 'https://example.org/manual')
        self.assertEqual(str(servicio.fecha_actualizacion), '2026-05-12')
