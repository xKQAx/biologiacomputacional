from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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
        self.assertContains(clave_mala, 'value="existe"')
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

    def test_correo_compartido_con_clave_mala_no_revela_cuentas(self):
        User.objects.create_user('cuenta_a', 'mismo@example.com', 'ClaveSegura1')
        User.objects.create_user('cuenta_b', 'mismo@example.com', 'ClaveSegura1')
        response = self.client.post('/identity/', {
            'username': 'mismo@example.com',
            'password': 'OtraClave1',
        })
        self.assertContains(response, 'Nombre de usuario o contraseña incorrectos')
        self.assertNotContains(response, 'varias cuentas')
        self.assertContains(response, 'value="mismo@example.com"')

    def test_fallo_conserva_recuerdame_y_el_destino(self):
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'OtraClave1',
            'remember_me': 'on',
            'next': '/identity/cambio_contrasena/',
        })
        self.assertContains(response, 'id="rememberMe" checked')
        self.assertContains(response, 'value="/identity/cambio_contrasena/"')
        self.assertContains(response, 'Mostrar contraseña')

    def test_entra_y_vuelve_a_la_pagina_pedida(self):
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'ClaveSegura1',
            'next': '/identity/cambio_contrasena/',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/identity/cambio_contrasena/')

    def test_destino_externo_no_sale_del_sitio(self):
        pagina = self.client.get('/identity/', {'next': 'https://evil.example/phish'})
        self.assertNotContains(pagina, 'evil.example')
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'ClaveSegura1',
            'next': 'https://evil.example/phish',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_destino_al_propio_login_no_hace_bucle(self):
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'ClaveSegura1',
            'next': '/identity/',
        })
        self.assertEqual(response.url, '/')

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


def _enlace_activacion(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'/identity/activate/{uid}/{token}/'


class ActivacionCuentaTests(TestCase):
    def test_activar_entra_y_recargar_el_enlace_no_parece_roto(self):
        pendiente = User.objects.create_user(
            'por_activar', 'activar@example.com', 'ClaveSegura1'
        )
        pendiente.is_active = False
        pendiente.save(update_fields=['is_active'])
        enlace = _enlace_activacion(pendiente)
        response = self.client.get(enlace)
        self.assertRedirects(response, '/identity/cuenta-activada/')
        pendiente.refresh_from_db()
        self.assertTrue(pendiente.is_active)
        pagina = self.client.get('/identity/cuenta-activada/')
        self.assertContains(pagina, 'Cuenta activada')
        self.assertContains(pagina, 'Ir al inicio')
        # El mismo enlace, ya usado: no debe verse como un error de activación.
        otra_vez = self.client.get(enlace)
        self.assertContains(otra_vez, 'ya está activada')
        self.assertNotContains(otra_vez, 'inválido')

    def test_enlace_roto_de_cuenta_pendiente_ofrece_reenvio(self):
        pendiente = User.objects.create_user(
            'sigue_pendiente', 'sigue@example.com', 'ClaveSegura1'
        )
        pendiente.is_active = False
        pendiente.save(update_fields=['is_active'])
        uid = urlsafe_base64_encode(force_bytes(pendiente.pk))
        response = self.client.get(f'/identity/activate/{uid}/token-malo/')
        self.assertContains(response, 'Reenviar enlace')
        self.assertNotContains(response, 'ya está activada')
        pendiente.refresh_from_db()
        self.assertFalse(pendiente.is_active)


class CambioContrasenaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'cambia', 'cambia@example.com', 'ClaveSegura1'
        )
        self.client.force_login(self.user)

    def test_clave_actual_incorrecta_se_explica_junto_al_campo(self):
        response = self.client.post('/identity/cambio_contrasena/', {
            'old_password': 'NoEsLaClave',
            'new_password1': 'ClaveNueva9',
            'new_password2': 'ClaveNueva9',
        })
        self.assertContains(response, 'id="oldPasswordError"')
        self.assertContains(response, 'incorrecta')
        self.assertNotContains(response, 'No se pudo cambiar la contraseña')

    def test_claves_nuevas_distintas_se_explican(self):
        response = self.client.post('/identity/cambio_contrasena/', {
            'old_password': 'ClaveSegura1',
            'new_password1': 'ClaveNueva9',
            'new_password2': 'OtraClave9',
        })
        self.assertContains(response, 'id="newPassword2Error"')
        self.assertContains(response, 'no coinciden')

    def test_cambio_exitoso_mantiene_la_sesion(self):
        response = self.client.post('/identity/cambio_contrasena/', {
            'old_password': 'ClaveSegura1',
            'new_password1': 'ClaveNueva9',
            'new_password2': 'ClaveNueva9',
        }, follow=True)
        self.assertEqual(response.redirect_chain[0][0], '/identity/cambio_contrasena/')
        self.assertContains(response, 'Cambio de contraseña exitoso')

    def test_sin_perfil_la_pantalla_sigue_abriendo(self):
        ProfileAdditionalInfo.objects.filter(user=self.user).delete()
        response = self.client.get('/identity/cambio_contrasena/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contraseña actual')


class RestablecerContrasenaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'olvido', 'olvido@example.com', 'ClaveSegura1'
        )

    def test_no_dice_si_el_correo_existe_y_deja_volver(self):
        response = self.client.post('/identity/reset_password/', {
            'email': 'nadie@example.com',
        }, follow=True)
        self.assertEqual(response.redirect_chain[0][0], '/identity/reset_password_sent/')
        self.assertContains(response, 'Si existe una cuenta')
        self.assertContains(response, 'Volver a iniciar sesión')
        self.assertNotContains(response, 'no existe')
        self.assertEqual(len(mail.outbox), 0)

    def test_el_asunto_del_correo_esta_en_espanol(self):
        self.client.post('/identity/reset_password/', {'email': 'olvido@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('contraseña', mail.outbox[0].subject.lower())

    def test_claves_distintas_se_ven_en_el_campo(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.post(f'/identity/reset/{uid}/{token}/', {
            'new_password1': 'ClaveNueva9',
            'new_password2': 'OtraClave9',
        })
        self.assertContains(response, 'id="newPassword2Error"')
        self.assertContains(response, 'no coinciden')
        self.assertContains(response, 'Mostrar contraseña')

    def test_enlace_invalido_ofrece_otro_y_el_login(self):
        response = self.client.get('/identity/reset/invalid/')
        self.assertContains(response, 'Pedir otro enlace')
        self.assertContains(response, 'Iniciar sesión')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_en_local_avisa_que_el_enlace_sale_por_la_terminal(self):
        response = self.client.get('/identity/reset_password_sent/')
        self.assertContains(response, 'terminal')
