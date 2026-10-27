from django.contrib.auth.models import User
from django.core import mail
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
        self.assertContains(respuesta, "Correo")
        self.assertContains(respuesta, "Personal")
        self.assertContains(respuesta, "Activa")
        self.assertContains(respuesta, f"/admin/cuentas/{self.estudiante.pk}/")
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
            "email": "nueva.lab@example.com",
            "password1": "ClaveSegura1",
            "password2": "ClaveSegura1",
            "is_active": "on",
            "is_staff": "on",
        })
        self.assertRedirects(respuesta, "/admin/cuentas/")
        self.assertEqual(User.objects.count(), antes + 1)
        creada = User.objects.get(username="nueva_lab")
        self.assertEqual(creada.email, "nueva.lab@example.com")
        self.assertTrue(creada.is_active)
        self.assertFalse(creada.is_staff)
        self.assertFalse(creada.is_superuser)
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
