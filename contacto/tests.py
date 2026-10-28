from smtplib import SMTPException
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacto.models import MensajeContacto


class ContactoPublicoTests(TestCase):
    def _datos(self, **cambios):
        datos = {
            'nombres': 'Ana',
            'apellidos': 'Pérez',
            'email': 'ana@example.com',
            'telefono': '3001234567',
            'opiniones': 'Quiero saber del laboratorio',
        }
        datos.update(cambios)
        return datos

    def test_el_envio_valido_avisa_en_el_inicio(self):
        respuesta = self.client.post(
            reverse('contactos'), self._datos(), follow=True,
        )
        self.assertRedirects(respuesta, reverse('inicio'))
        self.assertContains(respuesta, 'Tu mensaje se envió correctamente.')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Información de contacto')
        self.assertEqual(mail.outbox[0].to, [settings.CONTACT_EMAIL])
        self.assertIn('Ana Pérez', mail.outbox[0].body)
        self.assertIn('Quiero saber del laboratorio', mail.outbox[0].body)
        guardado = MensajeContacto.objects.get()
        self.assertEqual(guardado.nombres, 'Ana')
        self.assertEqual(guardado.apellidos, 'Pérez')
        self.assertEqual(guardado.email, 'ana@example.com')
        self.assertEqual(guardado.telefono, '3001234567')
        self.assertEqual(guardado.opiniones, 'Quiero saber del laboratorio')
        self.assertFalse(guardado.leido)
        self.assertNotContains(respuesta, 'Quiero saber del laboratorio')

    def test_el_telefono_invalido_conserva_lo_escrito(self):
        respuesta = self.client.post(reverse('contactos'), self._datos(
            telefono='12345',
            opiniones='Mensaje que no debe perderse',
        ))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'El teléfono debe tener 10 dígitos, sin espacios ni otros caracteres.',
        )
        self.assertContains(respuesta, 'id="error-telefono"')
        self.assertContains(respuesta, 'value="Ana"')
        self.assertContains(respuesta, 'value="Pérez"')
        self.assertContains(respuesta, 'value="ana@example.com"')
        self.assertContains(respuesta, 'value="12345"')
        self.assertContains(respuesta, 'Mensaje que no debe perderse')
        self.assertNotContains(respuesta, 'Hubo un error en el formulario')
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(MensajeContacto.objects.count(), 0)

    def test_otro_error_conserva_lo_escrito_y_es_especifico(self):
        respuesta = self.client.post(reverse('contactos'), self._datos(
            email='no-es-correo',
            opiniones='Sigo aquí',
        ))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Introduce un correo electrónico válido.')
        self.assertContains(respuesta, 'id="error-email"')
        self.assertContains(respuesta, 'value="Ana"')
        self.assertContains(respuesta, 'value="3001234567"')
        self.assertContains(respuesta, 'Sigo aquí')
        self.assertNotContains(respuesta, 'Hubo un error en el formulario')
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(MensajeContacto.objects.count(), 0)

    def test_un_fallo_de_correo_no_borra_el_mensaje(self):
        with patch(
            'BiologiaComputacional.mail.send_mail',
            side_effect=SMTPException('rechazado'),
        ):
            respuesta = self.client.post(reverse('contactos'), self._datos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'No se pudo enviar el mensaje: el correo no está configurado o el servidor lo rechazó. Inténtalo más tarde.',
        )
        self.assertEqual(len(mail.outbox), 0)
        guardado = MensajeContacto.objects.get()
        self.assertEqual(guardado.opiniones, 'Quiero saber del laboratorio')
        self.assertFalse(guardado.leido)

        staff = User.objects.create_user(
            'lector_fallo_correo',
            'lector.fallo@example.com',
            'ClaveSegura1',
            is_staff=True,
        )
        self.client.force_login(staff)
        detalle = self.client.get(
            reverse('admin:mensajes_detalle', args=[guardado.pk]),
        )
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, 'Quiero saber del laboratorio')
        guardado.refresh_from_db()
        self.assertTrue(guardado.leido)


class BandejaContactoTests(TestCase):
    def setUp(self):
        self.mensaje = MensajeContacto.objects.create(
            nombres='Ana',
            apellidos='Pérez',
            email='ana@example.com',
            telefono='3001234567',
            opiniones=('Texto visible en el panel. ' * 6) + 'COLAUNICA987',
        )

    def test_un_anonimo_no_entra_y_el_personal_si(self):
        for ruta in (
            reverse('admin:mensajes'),
            reverse('admin:mensajes_detalle', args=[self.mensaje.pk]),
        ):
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 302, ruta)
            self.assertIn('/admin/login/', respuesta.url)

        visitante = User.objects.create_user(
            'visitante_mensajes',
            'visitante.mensajes@example.com',
            'ClaveSegura1',
        )
        self.client.force_login(visitante)
        respuesta = self.client.get(reverse('admin:mensajes'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta.url)

        staff = User.objects.create_user(
            'lector_mensajes',
            'lector.mensajes@example.com',
            'ClaveSegura1',
            is_staff=True,
        )
        self.client.force_login(staff)
        lista = self.client.get(reverse('admin:mensajes'))
        self.assertEqual(lista.status_code, 200)
        fecha = timezone.localtime(self.mensaje.creado).strftime('%d/%m/%Y')
        self.assertContains(lista, fecha)
        self.assertContains(lista, 'Ana Pérez')
        self.assertContains(lista, 'ana@example.com')
        self.assertContains(lista, '3001234567')
        self.assertContains(lista, self.mensaje.extracto)
        self.assertContains(lista, 'No leído')
        self.assertNotContains(lista, 'COLAUNICA987')

        detalle = self.client.get(
            reverse('admin:mensajes_detalle', args=[self.mensaje.pk]),
        )
        self.assertContains(detalle, 'COLAUNICA987')
        self.assertContains(detalle, 'Ana Pérez')
        self.mensaje.refresh_from_db()
        self.assertTrue(self.mensaje.leido)
        lista = self.client.get(reverse('admin:mensajes'))
        self.assertContains(lista, 'Leído')

    def test_el_indice_ofrece_mensajes_fuera_de_usuarios(self):
        staff = User.objects.create_user(
            'indice_mensajes',
            'indice.mensajes@example.com',
            'ClaveSegura1',
            is_staff=True,
        )
        self.client.force_login(staff)
        indice = self.client.get('/admin/')
        html = indice.content.decode()
        usuarios = html.find('id="usuarios"')
        bloque = html.find('id="mensajes-de-contacto"')
        self.assertGreaterEqual(usuarios, 0)
        self.assertLess(usuarios, bloque)
        self.assertNotIn('Mensajes de contacto', html[usuarios:bloque])
        self.assertIn('/admin/mensajes/', html[bloque:])
        self.assertNotContains(indice, '/admin/contacto/mensajecontacto/')

        pagina = self.client.get(reverse('admin:mensajes'))
        menu = pagina.content.decode()
        nav = menu[menu.find('id="nav-sidebar"'):menu.find('id="content"')]
        self.assertLess(nav.find('>Usuarios<'), nav.find('>Mensajes<'))
        self.assertLess(nav.find('>Cuentas<'), nav.find('>Mensajes de contacto<'))
        self.assertIn('aria-current="page">Mensajes de contacto', nav)

    def test_el_sitio_publico_no_muestra_los_mensajes(self):
        for ruta in ('/', reverse('contactos')):
            respuesta = self.client.get(ruta)
            self.assertNotContains(respuesta, 'COLAUNICA987')
            self.assertNotContains(respuesta, 'ana@example.com')
