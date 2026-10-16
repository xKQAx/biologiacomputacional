from django.contrib.auth.models import User
from django.test import TestCase

from identity.models import ProfileAdditionalInfo


class InfoUsuariosTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            'gestor_id', 'id@example.com', 'ClaveSegura1', is_staff=True
        )
        self.estudiante = User.objects.create_user(
            'alumno_id', 'alumno@example.com', 'ClaveSegura1'
        )
        self.url = '/identity/info_usuarios/'

    def test_json_de_staff_no_incluye_password(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()['info_users']
        self.assertTrue(payload)
        for row in payload:
            self.assertNotIn('password', row)
        body = response.content.decode()
        self.assertNotIn('pbkdf2', body)
        self.assertNotIn('password', body)

    def test_usuario_no_staff_no_recibe_el_json(self):
        self.client.force_login(self.estudiante)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('pbkdf2', response.content.decode())


class EliminarUsuarioTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            'root', 'root@example.com', 'ClaveSegura1'
        )
        self.objetivo = User.objects.create_user(
            'borrarme', 'borrar@example.com', 'ClaveSegura1'
        )
        self.url = f'/identity/eliminar_usuario/id={self.objetivo.pk}/'

    def test_get_no_elimina(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(User.objects.filter(pk=self.objetivo.pk).exists())


class PerfilAlCrearUsuarioTests(TestCase):
    def test_crear_usuario_crea_perfil(self):
        user = User.objects.create_user('nuevo_perfil', 'np@example.com', 'ClaveSegura1')
        self.assertTrue(ProfileAdditionalInfo.objects.filter(user=user).exists())


class LoginNoRevelaUsuarioTests(TestCase):
    def setUp(self):
        User.objects.create_user('existe', 'existe@example.com', 'ClaveSegura1')

    def test_mensaje_unico_si_falla_la_clave_o_el_usuario(self):
        desconocido = self.client.post('/identity/', {
            'username': 'no_existe',
            'password': 'ClaveSegura1',
        })
        clave_mala = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'OtraClave1',
        })
        self.assertContains(desconocido, 'Nombre de usuario o contraseña incorrectos')
        self.assertContains(clave_mala, 'Nombre de usuario o contraseña incorrectos')
        self.assertNotContains(desconocido, 'no existe')
        self.assertNotContains(clave_mala, 'no coincide')

    def test_clave_guardada_sin_minuscula_si_entra(self):
        # El login no puede exigir la política de alta: esa clave ya está guardada.
        User.objects.create_user('sinminus', 'sm@example.com', 'PASSWORD1')
        response = self.client.post('/identity/', {
            'username': 'sinminus',
            'password': 'PASSWORD1',
        })
        self.assertEqual(response.status_code, 302)
