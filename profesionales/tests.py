from django.contrib.auth.models import User
from django.test import TestCase

from BiologiaComputacional.forms import ProfileFormProfessional
from profesionales.models import InformacionProfesional


class TituloUniversitarioTests(TestCase):
    def test_modelo_y_formulario_admiten_120(self):
        self.assertEqual(
            InformacionProfesional._meta.get_field('titulo_universitario').max_length,
            120,
        )
        self.assertEqual(
            ProfileFormProfessional.base_fields['titulo_universitario'].max_length,
            120,
        )


class InfoProfesionalJsonTests(TestCase):
    def setUp(self):
        InformacionProfesional.objects.create(
            nombre='Ana',
            apellido='Perez',
            titulo_universitario='Bióloga',
            email='ana@example.com',
            telefono='3001234567',
        )
        self.staff = User.objects.create_user(
            'gestor_prof', 'prof@example.com', 'ClaveSegura1', is_staff=True
        )

    def test_anonimo_no_recibe_el_json(self):
        response = self.client.get('/profesionales/info_profesional/')
        self.assertEqual(response.status_code, 302)

    def test_staff_no_recibe_correo_ni_telefono(self):
        self.client.force_login(self.staff)
        response = self.client.get('/profesionales/info_profesional/')
        self.assertEqual(response.status_code, 200)
        row = response.json()['info_pro'][0]
        self.assertNotIn('email', row)
        self.assertNotIn('telefono', row)
        self.assertNotIn('ana@example.com', response.content.decode())
