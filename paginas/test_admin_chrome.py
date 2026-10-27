from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.staticfiles import finders
from django.test import RequestFactory, TestCase

from BiologiaComputacional.admin_lab import agrupar_indice

# Listados que ya no se abren desde el admin.
_CHANGELISTS_RETIRADOS = (
    "/admin/investigacion/carrusel/",
    "/admin/investigacion/investigacion/",
    "/admin/investigacion/categoriai/",
    "/admin/profesionales/informacionprofesional/",
    "/admin/profesionales/articulos/",
    "/admin/servicios/servicio/",
    "/admin/servicios/categoria/",
)


class AdminLaboratorioTests(TestCase):
    def test_el_login_responde_con_el_nombre_del_laboratorio(self):
        respuesta = self.client.get("/admin/login/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Laboratorio de Biología Computacional")
        self.assertContains(respuesta, "Sitio público")
        self.assertContains(respuesta, "css/admin_lab.css")
        self.assertIsNotNone(finders.find("css/admin_lab.css"))

    def test_staff_ve_el_enlace_para_editar_el_inicio(self):
        staff = User.objects.create_user(
            "gestor_admin_lab",
            "adminlab@example.com",
            "ClaveSegura1",
            is_staff=True,
        )
        self.client.force_login(staff)
        indice = self.client.get("/admin/")
        self.assertEqual(indice.status_code, 200)
        self.assertContains(indice, "Editar página de inicio")
        self.assertContains(indice, "Páginas del sitio")
        for ruta in (
            "/admin/pagina/inicio/",
            "/admin/pagina/investigacion/",
            "/admin/pagina/profesionales/",
            "/admin/pagina/servicios/",
            "/admin/pagina/bases-de-datos/",
            "/admin/pagina/contacto/",
            "/admin/cuentas/",
        ):
            self.assertContains(indice, ruta)
        self.assertContains(indice, "Usuarios del laboratorio: correo, acceso de personal")
        self._sin_filas_de_cuentas(indice)
        self.assertNotContains(indice, "Carrusel")
        self.assertNotContains(indice, "Investigaciones")
        self.assertNotContains(indice, "Artículos")
        for ruta in _CHANGELISTS_RETIRADOS:
            self.assertNotContains(indice, ruta)

    def test_el_superuser_ve_el_contenido_agrupado(self):
        User.objects.create_superuser(
            "gestor_super_lab",
            "superlab@example.com",
            "ClaveSegura1",
        )
        self.client.force_login(User.objects.get(username="gestor_super_lab"))
        indice = self.client.get("/admin/")
        html = indice.content.decode()

        self.assertLess(html.find(">Inicio<"), html.find(">Investigación<"))
        self.assertLess(html.find(">Investigación<"), html.find(">Profesionales<"))
        self.assertLess(html.find(">Profesionales<"), html.find(">Servicios<"))
        self.assertLess(html.find(">Servicios<"), html.find(">Bases de datos<"))
        self.assertLess(html.find(">Bases de datos<"), html.find(">Contacto<"))
        # La barra también dice Cuentas; el orden se mira en el contenido.
        contenido = html[html.find('id="content"'):]
        self.assertLess(contenido.find(">Contacto<"), contenido.find(">Cuentas<"))
        self.assertContains(indice, "Portada del sitio, con el editor en vivo.")
        self.assertContains(indice, "/admin/cuentas/")
        self._sin_filas_de_cuentas(indice)
        self.assertNotContains(indice, "Carrusel")
        self.assertNotContains(indice, "Investigaciones")
        self.assertNotContains(indice, "Artículos")
        self.assertNotContains(indice, "Categoria is")
        self.assertNotContains(indice, "Informacion profesional")
        for ruta in _CHANGELISTS_RETIRADOS:
            self.assertNotContains(indice, ruta)
        self.assertNotContains(indice, "/admin/sessions/session/")
        self.assertNotContains(indice, "/admin/auth/permission/")
        self.assertNotContains(indice, ">Sistema<")

    def test_el_sistema_no_sale_en_el_indice_de_un_staff(self):
        sesion = {
            "name": "Sesiones",
            "app_label": "sessions",
            "app_url": "/admin/sessions/",
            "models": [{
                "name": "Sesiones",
                "object_name": "Session",
                "model": Session,
                "admin_url": "/admin/sessions/session/",
                "add_url": None,
                "perms": {},
            }],
        }
        fabrica = RequestFactory()
        staff = fabrica.get("/admin/")
        staff.user = User.objects.create_user(
            "gestor_sin_sistema",
            "sinsistema@example.com",
            "ClaveSegura1",
            is_staff=True,
        )
        self.assertEqual(agrupar_indice([sesion], staff), [])

        superuser = fabrica.get("/admin/")
        superuser.user = User.objects.create_superuser(
            "gestor_con_sistema",
            "consistema@example.com",
            "ClaveSegura1",
        )
        grupos = agrupar_indice([sesion], superuser)
        self.assertEqual([grupo["name"] for grupo in grupos], ["Sistema"])
        self.assertEqual(grupos[0]["models"][0]["admin_url"], "/admin/sessions/session/")

    def test_un_anonimo_no_abre_la_gestion_de_cuentas(self):
        for ruta in ("/admin/cuentas/", "/admin/cuentas/nueva/", "/admin/cuentas/1/"):
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 302, ruta)
            self.assertIn("/admin/login/", respuesta.url)

    def test_el_login_del_admin_sigue_entrando(self):
        User.objects.create_user(
            "gestor_login_admin",
            "loginadmin@example.com",
            "ClaveSegura1",
            is_staff=True,
        )
        respuesta = self.client.post("/admin/login/", {
            "username": "gestor_login_admin",
            "password": "ClaveSegura1",
            "next": "/admin/",
        })
        self.assertRedirects(respuesta, "/admin/")

    def _sin_filas_de_cuentas(self, indice):
        for ruta in (
            "/admin/auth/user/",
            "/admin/auth/group/",
            "/admin/identity/profileadditionalinfo/",
        ):
            self.assertNotContains(indice, ruta)
        self.assertNotContains(indice, ">Perfiles<")
        self.assertNotContains(indice, ">Grupos<")
        self.assertNotContains(indice, ">Usuarios<")
