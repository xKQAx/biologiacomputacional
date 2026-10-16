from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
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
        cache.clear()
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

    def test_recuerdame_fija_dos_semanas_y_no_se_renueva(self):
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'ClaveSegura1',
            'remember_me': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        cookie = response.cookies['sessionid']
        self.assertGreater(int(cookie['max-age']), 1209600 - 120)
        self.assertLessEqual(int(cookie['max-age']), 1209600)
        deadline = self.client.session.get_expiry_date()
        self.assertEqual(self.client.session.get_expiry_date(), deadline)
        session = self.client.session
        session['marca'] = 1
        session.save()
        self.assertEqual(self.client.session.get_expiry_date(), deadline)

    def test_sin_recuerdame_la_sesion_muere_al_cerrar_el_navegador(self):
        response = self.client.post('/identity/', {
            'username': 'existe',
            'password': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.assertEqual(response.cookies['sessionid']['max-age'], '')

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

    def test_el_correo_nuevo_queda_en_minusculas(self):
        response = self.client.post('/identity/register/', {
            'username': 'minusculas',
            'email': 'Nuevo.Correo@Example.com',
            'password1': 'ClaveSegura1',
            'password2': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='minusculas')
        self.assertEqual(user.email, 'nuevo.correo@example.com')
        self.assertFalse(user.is_active)

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
        landing = self.client.get(f'/identity/reset/{uid}/{token}/')
        self.assertRedirects(landing, '/identity/reset/clave/')
        self.assertNotIn(token, landing.url)
        response = self.client.post('/identity/reset/clave/', {
            'new_password1': 'ClaveNueva9',
            'new_password2': 'OtraClave9',
        })
        self.assertContains(response, 'id="newPassword2Error"')
        self.assertContains(response, 'no coinciden')
        self.assertContains(response, 'Mostrar contraseña')
        self.assertNotContains(response, token)

    def test_el_enlace_sale_de_la_barra_y_guarda_la_clave(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        landing = self.client.get(f'/identity/reset/{uid}/{token}/')
        self.assertRedirects(landing, '/identity/reset/clave/')
        response = self.client.post('/identity/reset/clave/', {
            'new_password1': 'ClaveNueva9',
            'new_password2': 'ClaveNueva9',
        })
        self.assertRedirects(response, '/identity/reset_password_complete/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ClaveNueva9'))
        otra = self.client.get('/identity/reset/clave/')
        self.assertRedirects(otra, '/identity/reset/invalid/')

    def test_sin_token_en_la_sesion_el_enlace_es_invalido(self):
        response = self.client.get('/identity/reset/clave/')
        self.assertRedirects(response, '/identity/reset/invalid/')

    def test_cuenta_inactiva_recibe_activacion_sin_cambiar_la_clave(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        response = self.client.post('/identity/reset_password/', {
            'email': 'olvido@example.com',
        }, follow=True)
        self.assertContains(response, 'Si existe una cuenta')
        self.assertNotContains(response, 'no está activada')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Activa tu cuenta')
        self.assertIn('/identity/activate/', mail.outbox[0].body)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.check_password('ClaveSegura1'))

    def test_enlace_invalido_ofrece_otro_y_el_login(self):
        response = self.client.get('/identity/reset/invalid/')
        self.assertContains(response, 'Pedir otro enlace')
        self.assertContains(response, 'Iniciar sesión')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_en_local_avisa_que_el_enlace_sale_por_la_terminal(self):
        response = self.client.get('/identity/reset_password_sent/')
        self.assertContains(response, 'terminal')


class CorreoUnicoTests(TestCase):
    def test_la_base_rechaza_dos_cuentas_con_el_mismo_correo(self):
        User.objects.create_user('cuenta_a', 'Mismo@example.com', 'ClaveSegura1')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user('cuenta_b', 'mismo@example.com', 'ClaveSegura1')

    def test_varias_cuentas_sin_correo_no_chocan(self):
        User.objects.create_user('sin_correo_a', '', 'ClaveSegura1')
        User.objects.create_user('sin_correo_b', '', 'ClaveSegura1')
        self.assertEqual(User.objects.filter(email='').count(), 2)

    def test_el_perfil_no_puede_tomar_el_correo_de_otra_cuenta(self):
        propio = User.objects.create_user('propio', 'propio@example.com', 'ClaveSegura1')
        User.objects.create_user('ajeno', 'ajeno@example.com', 'ClaveSegura1')
        self.client.force_login(propio)
        response = self.client.post('/identity/perfil/', {
            'first_name': 'Ana',
            'last_name': 'Perez',
            'email': 'Ajeno@example.com',
            'phone_number': '3001234567',
        }, follow=True)
        self.assertContains(response, 'Ya existe una cuenta con este correo')
        propio.refresh_from_db()
        self.assertEqual(propio.email, 'propio@example.com')

    def test_el_perfil_conserva_su_correo_aunque_cambie_las_mayusculas(self):
        propio = User.objects.create_user('propio', 'propio@example.com', 'ClaveSegura1')
        self.client.force_login(propio)
        response = self.client.post('/identity/perfil/', {
            'first_name': 'Ana',
            'last_name': 'Perez',
            'email': 'Propio@Example.com',
            'phone_number': '3001234567',
        }, follow=True)
        self.assertContains(response, 'Información actualizada con éxito')
        propio.refresh_from_db()
        self.assertEqual(propio.email, 'propio@example.com')


class LogoutPostTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sale', 'sale@example.com', 'ClaveSegura1')
        self.client.force_login(self.user)

    def test_get_no_cierra_la_sesion(self):
        response = self.client.get('/identity/logout/')
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_cierra_la_sesion(self):
        response = self.client.post('/identity/logout/')
        self.assertRedirects(response, '/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_el_menu_no_cierra_sesion_con_un_enlace(self):
        response = self.client.get('/identity/perfil/')
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'action="/identity/logout/"')
        self.assertNotContains(response, 'href="/identity/logout/"')


THROTTLE_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'identity-login-throttle-tests',
    }
}


@override_settings(CACHES=THROTTLE_CACHE)
class LimiteLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('bloqueado', 'bloqueado@example.com', 'ClaveSegura1')

    def _fallo(self, username='bloqueado', password='OtraClave1'):
        return self.client.post('/identity/', {
            'username': username,
            'password': password,
        })

    def test_al_quinto_fallo_bloquea_sin_decir_si_la_cuenta_existe(self):
        for _ in range(4):
            response = self._fallo()
            self.assertContains(response, 'Nombre de usuario o contraseña incorrectos')
        quinto = self._fallo(username='Bloqueado')
        self.assertContains(quinto, '15 minutos')
        self.assertNotContains(quinto, 'incorrectos')
        self.assertNotContains(quinto, 'no existe')
        correcto = self._fallo(password='ClaveSegura1')
        self.assertContains(correcto, '15 minutos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_un_acierto_reinicia_el_contador(self):
        for _ in range(4):
            self._fallo()
        ok = self._fallo(password='ClaveSegura1')
        self.assertEqual(ok.status_code, 302)
        self.client.logout()
        response = self._fallo()
        self.assertContains(response, 'Nombre de usuario o contraseña incorrectos')
        self.assertNotContains(response, '15 minutos')

    def test_otra_cuenta_no_queda_bloqueada(self):
        User.objects.create_user('vecino', 'vecino@example.com', 'ClaveSegura1')
        for _ in range(5):
            self._fallo()
        response = self._fallo(username='vecino')
        self.assertContains(response, 'Nombre de usuario o contraseña incorrectos')
        self.assertNotContains(response, '15 minutos')

    def test_el_registro_no_usa_el_limite_del_login(self):
        for _ in range(5):
            self._fallo()
        response = self.client.post('/identity/register/', {
            'username': 'recien_ok',
            'email': 'recien_ok@example.com',
            'password1': 'ClaveSegura1',
            'password2': 'ClaveSegura1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='recien_ok').exists())
        self.assertNotContains(response, '15 minutos')
