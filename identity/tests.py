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

    def test_entra_con_el_correo_si_solo_hay_una_cuenta(self):
        response = self.client.post('/identity/', {
            'username': 'existe@example.com',
            'password': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 302)

    def test_acepta_un_usuario_con_arroba(self):
        User.objects.create_user('ana@lab.test', 'ana.otra@example.com', 'ClaveSegura1')
        response = self.client.post('/identity/', {
            'username': 'ana@lab.test',
            'password': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 302)

    def test_correo_compartido_pide_el_usuario(self):
        User.objects.create_user('cuenta_a', 'mismo@example.com', 'ClaveSegura1')
        User.objects.create_user('cuenta_b', 'mismo@example.com', 'ClaveSegura1')
        response = self.client.post('/identity/', {
            'username': 'mismo@example.com',
            'password': 'ClaveSegura1',
        })
        self.assertContains(response, 'Hay varias cuentas con este correo')

    def test_cuenta_inactiva_explica_como_activarla(self):
        pendiente = User.objects.create_user(
            'pendiente', 'pendiente@example.com', 'ClaveSegura1'
        )
        pendiente.is_active = False
        pendiente.save(update_fields=['is_active'])
        response = self.client.post('/identity/', {
            'username': 'pendiente',
            'password': 'ClaveSegura1',
        })
        self.assertContains(response, 'todavía no está activada')
        self.assertContains(response, 'Reenviar correo de activación')
        self.assertNotContains(response, 'problemas')
        reenvio = self.client.post('/identity/reenviar-activacion/')
        self.assertContains(reenvio, 'Enviamos de nuevo el enlace')
        self.assertContains(reenvio, 'pendiente@example.com')


class RegistroCuentaExistenteTests(TestCase):
    def setUp(self):
        User.objects.create_user('existe', 'existe@example.com', 'ClaveSegura1')

    def test_correo_repetido_no_crea_otra_cuenta(self):
        antes = User.objects.count()
        response = self.client.post('/identity/register/', {
            'username': 'otro_nombre',
            'email': 'Existe@example.com',
            'password1': 'ClaveSegura1',
            'password2': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta con este correo')
        self.assertContains(response, 'otro_nombre')
        self.assertEqual(User.objects.count(), antes)

    def test_usuario_repetido_conserva_lo_escrito(self):
        response = self.client.post('/identity/register/', {
            'username': 'Existe',
            'email': 'nuevo@example.com',
            'password1': 'ClaveSegura1',
            'password2': 'ClaveSegura1',
        })
        self.assertContains(response, 'Este nombre de usuario ya está registrado')
        self.assertContains(response, 'nuevo@example.com')
        self.assertFalse(User.objects.filter(username__iexact='existe').count() > 1)

    def test_disponibilidad_avisa_antes_de_enviar(self):
        ocupado = self.client.get('/identity/disponibilidad/', {
            'username': 'existe',
            'email': 'existe@example.com',
        })
        libre = self.client.get('/identity/disponibilidad/', {
            'username': 'libre_ok',
            'email': 'libre@example.com',
        })
        self.assertEqual(ocupado.json()['username_taken'], True)
        self.assertEqual(ocupado.json()['email_taken'], True)
        self.assertEqual(libre.json()['username_taken'], False)
        self.assertEqual(libre.json()['email_taken'], False)
