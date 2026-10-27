from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db.models import ProtectedError
from django.test import TestCase

from identity.models import ProfileAdditionalInfo


class GestionCuentasAdminTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "gestor_cuentas",
            "gestor.cuentas@example.com",
            "ClaveSegura1",
            is_staff=True,
        )
        self.estudiante = User.objects.create_user(
            "alumno_cuentas",
            "alumno.cuentas@example.com",
            "ClaveSegura1",
        )
        self.superuser = User.objects.create_superuser(
            "raiz_cuentas",
            "raiz.cuentas@example.com",
            "ClaveSegura1",
        )

    def test_el_personal_ve_usuario_correo_y_acceso_sin_la_clave(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get("/admin/cuentas/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "alumno_cuentas")
        self.assertContains(respuesta, "alumno.cuentas@example.com")
        self.assertContains(respuesta, "Usuario")
        self.assertContains(respuesta, "Nombre")
        self.assertContains(respuesta, "Correo")
        self.assertContains(respuesta, "Personal")
        self.assertContains(respuesta, "Activa")
        self.assertContains(respuesta, "Ver / editar")
        self.assertContains(respuesta, "Desactivar")
        self.assertContains(respuesta, "Eliminar")
        self.assertContains(respuesta, f"/admin/cuentas/{self.estudiante.pk}/")
        self.assertContains(respuesta, f"/admin/cuentas/{self.estudiante.pk}/desactivar/")
        self.assertContains(respuesta, f"/admin/cuentas/{self.estudiante.pk}/eliminar/")
        self.assertNotContains(respuesta, f"/admin/cuentas/{self.staff.pk}/")
        self.assertNotContains(respuesta, "pbkdf2")

    def test_quien_no_es_personal_no_abre_la_gestion(self):
        self.client.force_login(self.estudiante)
        respuesta = self.client.get("/admin/cuentas/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/admin/login/", respuesta.url)

    def test_el_personal_crea_una_cuenta_que_puede_entrar(self):
        self.client.force_login(self.staff)
        antes = User.objects.count()
        respuesta = self.client.post("/admin/cuentas/nueva/", {
            "username": "nueva_lab",
            "first_name": "Nueva",
            "last_name": "Cuenta",
            "email": "nueva.lab@example.com",
            "password1": "ClaveSegura1",
            "password2": "ClaveSegura1",
            "is_active": "on",
            "is_staff": "on",
            "is_superuser": "on",
        })
        self.assertRedirects(respuesta, "/admin/cuentas/")
        self.assertEqual(User.objects.count(), antes + 1)
        creada = User.objects.get(username="nueva_lab")
        self.assertEqual(creada.email, "nueva.lab@example.com")
        self.assertEqual(creada.first_name, "Nueva")
        self.assertEqual(creada.last_name, "Cuenta")
        self.assertTrue(creada.is_active)
        self.assertFalse(creada.is_staff)
        self.assertFalse(creada.is_superuser)
        self.assertFalse(ProfileAdditionalInfo.objects.get(user=creada).suspendida)
        self.assertTrue(creada.check_password("ClaveSegura1"))
        self.assertTrue(ProfileAdditionalInfo.objects.filter(user=creada).exists())
        self.assertEqual(len(mail.outbox), 0)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.check_password("ClaveSegura1"))

        self.client.logout()
        entrada = self.client.post("/identity/", {
            "username": "nueva_lab",
            "password": "ClaveSegura1",
        })
        self.assertEqual(entrada.status_code, 302)

    def test_el_correo_repetido_no_crea_otra_cuenta(self):
        self.client.force_login(self.staff)
        antes = User.objects.count()
        respuesta = self.client.post("/admin/cuentas/nueva/", {
            "username": "otra_lab",
            "email": "Alumno.Cuentas@example.com",
            "password1": "ClaveSegura1",
            "password2": "ClaveSegura1",
            "is_active": "on",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ya existe una cuenta con este correo")
        self.assertEqual(User.objects.count(), antes)

    def test_el_superusuario_puede_crear_personal(self):
        self.client.force_login(self.superuser)
        respuesta = self.client.post("/admin/cuentas/nueva/", {
            "username": "nuevo_personal",
            "email": "nuevo.personal@example.com",
            "password1": "ClaveSegura1",
            "password2": "ClaveSegura1",
            "is_active": "on",
            "is_staff": "on",
        })
        self.assertRedirects(respuesta, "/admin/cuentas/")
        creada = User.objects.get(username="nuevo_personal")
        self.assertTrue(creada.is_staff)
        self.assertFalse(creada.is_superuser)

    def test_el_personal_no_edita_a_otro_personal(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get(f"/admin/cuentas/{self.superuser.pk}/")
        self.assertEqual(respuesta.status_code, 403)
        post = self.client.post(f"/admin/cuentas/{self.staff.pk}/", {
            "username": self.staff.username,
            "email": "tomado@example.com",
            "is_active": "on",
        })
        self.assertEqual(post.status_code, 403)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "gestor.cuentas@example.com")

    def test_el_personal_actualiza_correo_sin_volverla_personal(self):
        self.client.force_login(self.staff)
        respuesta = self.client.post(f"/admin/cuentas/{self.estudiante.pk}/", {
            "username": "alumno_cuentas",
            "email": "alumno.nuevo@example.com",
            "is_active": "on",
            "is_staff": "on",
        })
        self.assertRedirects(respuesta, "/admin/cuentas/")
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.email, "alumno.nuevo@example.com")
        self.assertFalse(self.estudiante.is_staff)
        self.assertTrue(self.estudiante.check_password("ClaveSegura1"))

    def test_el_superusuario_cambia_el_acceso_y_no_se_cierra_el_suyo(self):
        self.client.force_login(self.superuser)
        dar = self.client.post(f"/admin/cuentas/{self.estudiante.pk}/", {
            "username": "alumno_cuentas",
            "email": "alumno.cuentas@example.com",
            "is_active": "on",
            "is_staff": "on",
        })
        self.assertRedirects(dar, "/admin/cuentas/")
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.is_staff)

        propio = self.client.post(f"/admin/cuentas/{self.superuser.pk}/", {
            "username": "raiz_cuentas",
            "email": "raiz.cuentas@example.com",
            "is_staff": "on",
        })
        self.assertEqual(propio.status_code, 200)
        self.assertContains(propio, "No puedes desactivar tu propia cuenta.")
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.check_password("ClaveSegura1"))

    def test_la_clave_cambia_solo_si_se_escribe(self):
        self.client.force_login(self.superuser)
        cambio = self.client.post(f"/admin/cuentas/{self.estudiante.pk}/", {
            "username": "alumno_cuentas",
            "email": "alumno.cuentas@example.com",
            "is_active": "on",
            "password1": "OtraClaveSegura2",
            "password2": "OtraClaveSegura2",
        })
        self.assertRedirects(cambio, "/admin/cuentas/")
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password("OtraClaveSegura2"))

        igual = self.client.post(f"/admin/cuentas/{self.estudiante.pk}/", {
            "username": "alumno_cuentas",
            "email": "alumno.cuentas@example.com",
            "is_active": "on",
        })
        self.assertRedirects(igual, "/admin/cuentas/")
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password("OtraClaveSegura2"))

    def test_la_ficha_reune_los_datos_sin_grupos_ni_la_clave(self):
        self.client.force_login(self.superuser)
        respuesta = self.client.get(f"/admin/cuentas/{self.estudiante.pk}/")
        self.assertEqual(respuesta.status_code, 200)
        for texto in (
            "Usuario",
            "Nombre",
            "Apellidos",
            "Correo",
            "Activa",
            "Personal del panel",
            "Superusuario",
            "Nueva contraseña",
            "Desactivar",
            "Eliminar",
        ):
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, "pbkdf2")
        self.assertNotContains(respuesta, "Grupos")
        self.assertNotContains(respuesta, "Permisos de usuario")
        html = respuesta.content.decode()
        migas = html[html.find('class="breadcrumbs"'):html.find('id="main"')]
        self.assertLess(migas.find(">Inicio<"), migas.find(">Cuentas<"))
        self.assertLess(migas.find('href="/admin/cuentas/"'), migas.find("Editar cuenta"))
        self.assertIn('aria-current="page">Editar cuenta', migas)

    def test_el_superusuario_puede_crear_otro_superusuario(self):
        self.client.force_login(self.superuser)
        respuesta = self.client.post("/admin/cuentas/nueva/", {
            "username": "otra_raiz",
            "first_name": "Otra",
            "last_name": "Raíz",
            "email": "otra.raiz@example.com",
            "password1": "ClaveSegura1",
            "password2": "ClaveSegura1",
            "is_active": "on",
            "is_staff": "on",
            "is_superuser": "on",
        })
        self.assertRedirects(respuesta, "/admin/cuentas/")
        creada = User.objects.get(username="otra_raiz")
        self.assertTrue(creada.is_superuser)
        self.assertTrue(creada.is_staff)
        self.assertTrue(creada.is_active)
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        entrada = self.client.post("/admin/login/", {
            "username": "otra_raiz",
            "password": "ClaveSegura1",
            "next": "/admin/",
        })
        self.assertRedirects(entrada, "/admin/")

    def test_el_personal_no_se_desactiva_ni_se_elimina(self):
        self.client.force_login(self.staff)
        antes = User.objects.count()
        for ruta in ("desactivar", "activar", "eliminar"):
            respuesta = self.client.post(
                f"/admin/cuentas/{self.staff.pk}/{ruta}/",
                {"confirmar": "si"},
            )
            self.assertEqual(respuesta.status_code, 403, ruta)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
        self.assertTrue(self.staff.is_staff)
        self.assertEqual(User.objects.count(), antes)
        self.assertTrue(self.staff.check_password("ClaveSegura1"))

    def test_un_superusuario_no_se_desactiva_ni_se_elimina(self):
        self.client.force_login(self.superuser)
        for ruta in ("desactivar", "eliminar"):
            respuesta = self.client.post(
                f"/admin/cuentas/{self.superuser.pk}/{ruta}/",
                {"confirmar": "si"},
            )
            self.assertEqual(respuesta.status_code, 403, ruta)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.check_password("ClaveSegura1"))

    def test_desactivar_impide_el_login_y_activar_lo_devuelve(self):
        self.client.force_login(self.staff)
        aviso = self.client.get(f"/admin/cuentas/{self.estudiante.pk}/desactivar/")
        self.assertContains(aviso, "No podrá entrar")
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.is_active)

        respuesta = self.client.post(
            f"/admin/cuentas/{self.estudiante.pk}/desactivar/",
            {"confirmar": "si"},
        )
        self.assertRedirects(respuesta, "/admin/cuentas/")
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.is_active)
        self.assertTrue(ProfileAdditionalInfo.objects.get(user=self.estudiante).suspendida)
        self.assertEqual(len(mail.outbox), 0)

        self.client.logout()
        entrada = self.client.post("/identity/", {
            "username": "alumno_cuentas",
            "password": "ClaveSegura1",
        })
        self.assertEqual(entrada.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(entrada, "desactivada")
        self.assertNotContains(entrada, "Reenviar correo de activación")
        self.assertEqual(len(mail.outbox), 0)

        reenvio = self.client.post("/identity/reenviar-activacion/", {
            "email": "alumno.cuentas@example.com",
        })
        self.assertEqual(reenvio.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.is_active)

        self.client.force_login(self.staff)
        activar = self.client.post(
            f"/admin/cuentas/{self.estudiante.pk}/activar/",
            {"confirmar": "si"},
        )
        self.assertRedirects(activar, "/admin/cuentas/")
        self.client.logout()
        de_nuevo = self.client.post("/identity/", {
            "username": "alumno_cuentas",
            "password": "ClaveSegura1",
        })
        self.assertEqual(de_nuevo.status_code, 302)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.is_active)
        self.assertFalse(ProfileAdditionalInfo.objects.get(user=self.estudiante).suspendida)

    def test_eliminar_quita_la_cuenta_y_el_perfil(self):
        self.client.force_login(self.staff)
        pk = self.estudiante.pk
        aviso = self.client.get(f"/admin/cuentas/{pk}/eliminar/")
        self.assertContains(aviso, "No se puede deshacer")
        self.assertContains(aviso, "foto y el teléfono")
        self.assertTrue(User.objects.filter(pk=pk).exists())

        respuesta = self.client.post(f"/admin/cuentas/{pk}/eliminar/", {"confirmar": "si"})
        self.assertRedirects(respuesta, "/admin/cuentas/")
        self.assertFalse(User.objects.filter(pk=pk).exists())
        self.assertFalse(ProfileAdditionalInfo.objects.filter(user_id=pk).exists())

    def test_si_eliminar_falla_la_cuenta_sigue_entera(self):
        self.client.force_login(self.superuser)
        pk = self.estudiante.pk
        with patch.object(User, "delete", side_effect=ProtectedError("protegida", [self.estudiante])):
            respuesta = self.client.post(
                f"/admin/cuentas/{pk}/eliminar/",
                {"confirmar": "si"},
                follow=True,
            )
        self.assertContains(respuesta, "Sigue existiendo")
        self.assertTrue(User.objects.filter(pk=pk).exists())
        self.assertTrue(ProfileAdditionalInfo.objects.filter(user_id=pk).exists())
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.is_active)
        self.assertEqual(self.estudiante.email, "alumno.cuentas@example.com")
