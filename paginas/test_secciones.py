"""Secciones que se agregan, ocultan o quitan en el borrador de inicio."""

import io
import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from paginas.models import BloquePortada
from paginas.saneo import PREFIJO_HTML


def _png(color='red'):
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), color).save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class SeccionesAgregablesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.editor = '/admin/pagina/inicio/'
        self.lienzo = '/admin/pagina/inicio/lienzo/'
        self.staff = User.objects.create_user(
            'gestor_secciones', 'secciones@example.com', 'ClaveSegura1', is_staff=True,
        )
        self.client.force_login(self.staff)

    def test_el_catalogo_esta_en_inicio_y_no_en_contacto_ni_bases(self):
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'Agregar sección')
        self.assertContains(editor, 'Encabezado')
        self.assertContains(editor, 'Texto')
        self.assertContains(editor, 'Imagen')
        self.assertContains(editor, 'Botón')
        self.assertContains(editor, 'value="ocultar:encabezado"')
        self.assertContains(editor, 'data-asa')
        self.assertContains(editor, 'Editando la sección')
        self.assertNotContains(editor, 'Dos columnas')
        self.assertNotContains(editor, 'data-columnas=')
        fila = editor.content.decode().split('data-seccion-item="nosotros"', 1)[1].split('</li>', 1)[0]
        self.assertIn('data-asa', fila)
        self.assertIn('value="ocultar:nosotros"', fila)
        self.assertIn('>Ocultar<', fila)
        self.assertNotIn('>Mostrar<', fila)
        self.assertNotIn('editor-badge', fila)
        self.assertEqual(fila.count('data-vivo='), 1)
        self.assertNotIn('>Eliminar<', fila)
        self.assertNotIn('name="texto__', fila)
        self.assertNotIn('<textarea', fila)
        self.assertContains(editor, 'data-divisor')
        self.assertNotContains(editor, 'data-subir')
        self.assertNotContains(editor, 'value="quitar:encabezado"')
        self.assertNotContains(editor, 'value="quitar:barra"')
        self.assertNotContains(editor, 'value="ocultar:barra"')
        self.assertNotContains(editor, 'value="ocultar:pie"')

        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertNotContains(portada, 'Nuevo encabezado')
        self.assertNotContains(portada, 'data-edit-id')

        self.client.force_login(self.staff)
        contacto = self.client.get('/admin/pagina/contacto/')
        self.assertNotContains(contacto, 'Agregar sección')
        self.assertNotContains(contacto, 'name="tipo_pieza"')
        bases = self.client.get('/admin/pagina/bases-de-datos/')
        self.assertNotContains(bases, 'name="tipo_pieza"')

    def test_agregar_queda_en_el_borrador_y_el_anonimo_no_lo_ve(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'encabezado'})
        pieza = self._id()
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Nuevo encabezado')
        self.assertContains(lienzo, f'data-seccion="{pieza}"')
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'Encabezado agregado')
        self.assertContains(editor, f'value="quitar:{pieza}"')

        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Nuevo encabezado')
        self.assertNotContains(portada, f'data-seccion="{pieza}"')
        self.assertContains(portada, 'Ciencia e Innovación')
        self.assertContains(portada, 'data-seccion="encabezado"')

    def test_publicar_muestra_la_seccion_y_no_cambia_servicios(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{pieza}-cuerpo': 'Párrafo publicado de la sección nueva',
        })
        self.assertFalse(BloquePortada.objects.filter(
            pagina='inicio', estado=BloquePortada.Estado.BORRADOR,
        ).exists())
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Párrafo publicado de la sección nueva')
        self.assertContains(portada, f'data-seccion="{pieza}"')
        servicios = self.client.get('/servicios/')
        self.assertContains(servicios, 'Servicios')
        self.assertNotContains(servicios, 'Párrafo publicado de la sección nueva')
        bases = self.client.get('/servicios/bases-de-datos/')
        self.assertNotContains(bases, 'Párrafo publicado de la sección nueva')

    def test_ocultar_en_el_borrador_no_vacia_la_portada(self):
        self.client.post(self.editor, {'accion': 'ocultar:nosotros'})
        editor = self.client.get(self.editor).content.decode()
        fila = editor.split('data-seccion-item="nosotros"', 1)[1].split('</li>', 1)[0]
        self.assertIn('value="mostrar:nosotros"', fila)
        self.assertIn('>Mostrar<', fila)
        self.assertNotIn('>Ocultar<', fila)
        self.assertNotIn('editor-badge', fila)
        self.assertEqual(fila.count('data-vivo='), 1)
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertIn('data-seccion="nosotros"', portada)
        self.assertIn('Conectando Ciencia e Innovación', portada)
        self.assertLess(portada.find('data-seccion="encabezado"'), portada.find('data-seccion="nosotros"'))

    def test_ocultar_la_quita_del_lienzo_y_mostrarla_la_devuelve(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'ocultar:{pieza}'})
        self.client.post(self.editor, {'accion': 'ocultar:nosotros'})

        lienzo = self.client.get(self.lienzo)
        self.assertNotContains(lienzo, f'data-seccion="{pieza}"')
        self.assertNotContains(lienzo, 'data-seccion="nosotros"')
        self.assertNotContains(lienzo, 'fomentamos la intersección')
        self.assertContains(lienzo, 'data-seccion="encabezado"')
        editor = self.client.get(self.editor)
        self.assertContains(editor, f'value="mostrar:{pieza}"')
        self.assertContains(editor, 'value="mostrar:nosotros"')

        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'data-seccion="nosotros"')
        self.assertContains(portada, 'Conectando Ciencia e Innovación')
        self.assertNotContains(portada, f'data-seccion="{pieza}"')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'mostrar:nosotros'})
        self.client.post(self.editor, {'accion': f'mostrar:{pieza}'})
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'data-seccion="nosotros"')
        self.assertContains(lienzo, 'fomentamos la intersección')
        self.assertContains(lienzo, f'data-seccion="{pieza}"')

        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'data-seccion="nosotros"')
        self.assertNotContains(portada, f'data-seccion="{pieza}"')

    def test_publicar_una_seccion_oculta_la_quita_de_la_portada_y_deja_la_barra(self):
        self.client.post(self.editor, {'accion': 'ocultar:nosotros'})
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'data-seccion="nosotros"')
        self.assertNotContains(portada, 'fomentamos la intersección')
        self.assertContains(portada, 'Registrarme')
        self.assertContains(portada, 'Campus Universitario Lagos del Cacique')
        self.assertContains(portada, 'data-seccion="encabezado"')

    def test_no_se_puede_quitar_una_seccion_de_la_plantilla(self):
        respuesta = self.client.post(self.editor, {'accion': 'quitar:encabezado'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'pertenece a la plantilla')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'data-seccion="encabezado"')

    def test_quitar_del_borrador_no_borra_lo_publicado(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'boton'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        self.assertContains(self.client.get('/'), 'Nuevo botón')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': f'quitar:{pieza}'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Nuevo botón')
        self.assertContains(portada, f'data-seccion="{pieza}"')
        lienzo = self.client.get(self.lienzo)
        self.assertEqual(lienzo.status_code, 302)

        self.client.force_login(self.staff)
        editor = self.client.get(self.lienzo)
        self.assertNotContains(editor, f'data-seccion="{pieza}"')

    def test_descartar_devuelve_la_seccion_publicada_y_no_borra_su_archivo(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'imagen'})
        pieza = self._id()
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'imagen__{pieza}-foto': _png('blue'),
            f'texto__{pieza}-foto': 'Alt publicado de la sección',
        })
        publicada = BloquePortada.objects.get(
            pagina='inicio', clave=f'{pieza}-foto', estado=BloquePortada.Estado.PUBLICADO,
        )
        ruta = Path(self.media_root) / 'portada' / publicada.enlace.rsplit('/', 1)[-1]
        self.assertTrue(ruta.is_file())

        self.client.post(self.editor, {
            'accion': 'guardar',
            f'imagen__{pieza}-foto': _png('green'),
            f'texto__{pieza}-foto': 'Alt que solo está en el borrador',
        })
        self.client.post(self.editor, {'accion': 'descartar'})
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, publicada.enlace)
        self.assertContains(portada, 'alt="Alt publicado de la sección"')
        self.assertNotContains(portada, 'Alt que solo está en el borrador')
        self.assertTrue(ruta.is_file())

    def test_una_imagen_sin_archivo_no_se_publica(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'imagen'})
        pieza = self._id()
        respuesta = self.client.post(self.editor, {'accion': 'publicar'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'necesita una imagen')
        self.client.logout()
        self.assertNotContains(self.client.get('/'), f'data-seccion="{pieza}"')

    def test_el_orden_del_borrador_no_mueve_la_portada(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'encabezado'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': 'publicar'})
        orden = (
            f'{pieza},encabezado,instituciones,caracteristicas,'
            'encontrar,nosotros,beneficios,llamado'
        )
        self.client.post(self.editor, {'accion': 'guardar', 'orden_secciones': orden})
        lienzo = self.client.get(self.lienzo).content.decode()
        self.assertLess(lienzo.find(f'data-seccion="{pieza}"'), lienzo.find('data-seccion="encabezado"'))
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertLess(portada.find('data-seccion="llamado"'), portada.find(f'data-seccion="{pieza}"'))

    def test_el_nombre_de_una_pieza_agregada_se_guarda(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'nombre__{pieza}': '  Nota del laboratorio  ',
        })
        self.assertEqual(self._piezas()[0]['nombre'], 'Nota del laboratorio')
        editor = self.client.get(self.editor)
        self.assertContains(editor, 'value="Nota del laboratorio"')
        self.assertContains(editor, f'name="nombre__{pieza}"')
        self.assertContains(editor, 'placeholder="Texto agregado"')
        self.client.post(self.editor, {'accion': f'ocultar:{pieza}'})
        self.assertEqual(self._piezas()[0]['nombre'], 'Nota del laboratorio')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Nota del laboratorio')
        self.assertNotContains(portada, f'data-seccion="{pieza}"')

    def test_reordenar_piezas_persiste_en_el_borrador(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'encabezado'})
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        piezas = self._piezas()
        primera, segunda = piezas[0]['id'], piezas[1]['id']
        orden = (
            f'{segunda},{primera},encabezado,instituciones,caracteristicas,'
            'encontrar,nosotros,beneficios,llamado'
        )
        self.client.post(self.editor, {'accion': 'guardar', 'orden_secciones': orden})
        lienzo = self.client.get(self.lienzo).content.decode()
        self.assertLess(
            lienzo.find(f'data-seccion="{segunda}"'),
            lienzo.find(f'data-seccion="{primera}"'),
        )
        editor = self.client.get(self.editor).content.decode()
        self.assertLess(
            editor.find(f'data-seccion-item="{segunda}"'),
            editor.find(f'data-seccion-item="{primera}"'),
        )
        self.assertIn(f'name="orden_secciones" id="orden-secciones" value="{orden}"', editor)
        self.client.logout()
        portada = self.client.get('/').content.decode()
        self.assertNotIn(f'data-seccion="{primera}"', portada)
        self.assertLess(
            portada.find('data-seccion="encabezado"'),
            portada.find('data-seccion="nosotros"'),
        )

    def test_un_script_o_javascript_no_se_guarda_en_la_seccion_nueva(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'encabezado'})
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'boton'})
        piezas = self._piezas()
        encabezado = next(item['id'] for item in piezas if item['tipo'] == 'encabezado')
        boton = next(item['id'] for item in piezas if item['tipo'] == 'boton')
        sucio = PREFIJO_HTML + '<p>Visible</p><script>alert(1)</script>'
        respuesta = self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{encabezado}-bajada': sucio,
            f'enlace__{boton}-boton': 'javascript:alert(1)',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'javascript')
        fila = BloquePortada.objects.filter(
            pagina='inicio', clave=f'{encabezado}-bajada', estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertFalse(fila.exists())
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, '<script>alert(1)</script>')
        self.assertNotContains(portada, 'javascript:')

    def test_el_parrafo_agregado_sanea_el_script_y_conserva_el_enlace(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        sucio = (
            PREFIJO_HTML
            + '<p>Visible</p><script>alert(1)</script>'
            + '<a href="javascript:alert(1)">malo</a>'
            + '<a href="https://seguro.example/seccion">bueno</a>'
        )
        self.client.post(self.editor, {
            'accion': 'publicar',
            f'texto__{pieza}-cuerpo': sucio,
        })
        fila = BloquePortada.objects.get(
            pagina='inicio', clave=f'{pieza}-cuerpo', estado=BloquePortada.Estado.PUBLICADO,
        )
        self.assertNotIn('<script', fila.texto.lower())
        self.assertNotIn('javascript:', fila.texto.lower())
        self.assertIn('https://seguro.example/seccion', fila.texto)
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'Visible')
        self.assertContains(portada, 'href="https://seguro.example/seccion"')
        self.assertNotContains(portada, '<script>alert(1)</script>')
        self.assertNotContains(portada, 'javascript:')

    def test_ocultar_en_vivo_no_devuelve_otra_pagina_del_editor(self):
        respuesta = self.client.post(
            self.editor,
            {'accion': 'ocultar:nosotros'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('application/json', respuesta['Content-Type'])
        cuerpo = respuesta.content.decode()
        self.assertNotIn('form-portada', cuerpo)
        self.assertNotIn('<!DOCTYPE', cuerpo)
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        self.assertTrue(datos['oculta'])
        self.assertEqual(datos['id'], 'nosotros')
        self.assertNotIn('data-seccion="nosotros"', datos['html_lienzo'])
        self.assertNotIn('fomentamos la intersección', datos['html_lienzo'])
        self.assertNotIn('form-portada', respuesta.content.decode())
        self.assertIn('>Mostrar<', datos['html_item'])
        self.assertNotIn('>Ocultar<', datos['html_item'])
        self.assertNotIn('editor-badge', datos['html_item'])
        self.assertEqual(datos['html_item'].count('data-vivo='), 1)
        self.assertIn('nosotros', self._composicion()['ocultas'])

        lienzo = self.client.get(self.lienzo)
        self.assertNotContains(lienzo, 'data-seccion="nosotros"')
        self.assertNotContains(lienzo, 'fomentamos la intersección')
        self.assertContains(lienzo, 'data-seccion="encabezado"')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'data-seccion="nosotros"')
        self.assertContains(portada, 'Conectando Ciencia e Innovación')

    def test_agregar_en_vivo_abre_la_seccion_sin_pagina_nueva(self):
        respuesta = self.client.post(
            self.editor,
            {'accion': 'agregar', 'tipo_pieza': 'texto'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('form-portada', respuesta.content.decode())
        datos = respuesta.json()
        pieza = self._id()
        self.assertTrue(datos['ok'])
        self.assertEqual(datos['seleccionar'], pieza)
        self.assertIn('>Eliminar<', datos['html_item'])
        self.assertIn('data-asa', datos['html_item'])
        self.assertNotIn('<textarea', datos['html_item'])
        self.assertIn('Cuadrícula', datos['html_campos'])
        self.assertIn('1 columna', datos['html_campos'])
        self.assertIn('2 columnas', datos['html_campos'])
        self.assertIn('3 columnas', datos['html_campos'])
        self.assertIn('Casilla 1', datos['html_campos'])
        self.assertIn('data-asa-pieza', datos['html_campos'])
        self.assertNotIn('Dos columnas iguales', datos['html_campos'])
        self.assertNotIn('Tres columnas (tarjetas)', datos['html_campos'])
        self.assertNotIn('Imagen a la izquierda y texto a la derecha', datos['html_campos'])
        self.assertNotIn('editor-disenos', datos['html_campos'])
        self.assertIn('Agregar pieza', datos['html_campos'])
        self.assertIn('Editando la sección', datos['html_campos'])
        self.assertIn(
            'Agrega un texto, una imagen, un carrusel o un botón.',
            datos['html_campos'],
        )
        self.assertIn('Una casilla vacía no rompe la página.', datos['html_campos'])
        self.assertIn(f'data-seccion="{pieza}"', datos['html_lienzo'])
        self.client.logout()
        self.assertNotContains(self.client.get('/'), f'data-seccion="{pieza}"')

    def test_el_texto_del_borrador_llega_al_lienzo_sin_recargar_el_editor(self):
        self.client.post(self.editor, {
            'accion': 'guardar',
            'texto__nosotros_titulo': 'Título que el lienzo pide ya',
        })
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'Título que el lienzo pide ya')
        self.assertContains(lienzo, 'data-edit-id="nosotros_titulo"')
        self.assertNotContains(lienzo, 'form-portada')
        self.assertNotContains(lienzo, 'id="lista-secciones"')
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Título que el lienzo pide ya')
        self.assertContains(portada, 'Conectando Ciencia e Innovación')

    def test_la_pieza_elegida_trae_solo_sus_campos_en_el_inspector(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        respuesta = self.client.post(
            self.editor,
            {'accion': f'pieza-agregar:{pieza}:imagen'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        datos = respuesta.json()
        self.assertEqual(datos['pieza'], 'b01')
        campos = datos['html_campos']
        self.assertIn('data-pieza-btn', campos)
        self.assertIn('data-pieza="b01"', campos)
        self.assertIn('>Quitar<', campos)
        self.assertIn(f'name="texto__{pieza}-b01-foto"', campos)
        self.assertIn('Una casilla vacía no rompe la página.', campos)
        self.assertIn('data-asa-pieza', campos)
        self.assertIn('Casilla 1', campos)
        self.assertIn('Subir imagen', campos)
        self.assertIn('type="file"', campos)
        self.assertIn('accept="image/jpeg,image/png,image/gif,image/webp"', campos)
        self.assertIn('editor-archivo-nativo', campos)
        self.assertNotIn('data-columnas="nosotros"', campos)
        self.assertNotIn('data-diseno="nosotros"', campos)
        self.assertIn(f'data-seccion="{pieza}"', datos['html_lienzo'])
        self.assertIn(f'data-edit-id="{pieza}-b01-foto"', datos['html_lienzo'])
        self.assertNotIn('form-portada', datos['html_lienzo'])
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, f'data-edit-id="{pieza}-b01-foto"')
        self.assertContains(lienzo, f'data-seccion="{pieza}"')
        self.assertNotContains(lienzo, 'form-portada')
        self.client.logout()
        self.assertNotContains(self.client.get('/'), f'data-seccion="{pieza}"')

    def test_el_script_escribe_en_el_documento_del_lienzo(self):
        from pathlib import Path

        from django.contrib.staticfiles import finders

        script = Path(finders.find('paginas/editor.js')).read_text(encoding='utf-8')
        self.assertIn('contentDocument', script)
        self.assertIn('aplicarMensaje', script)
        self.assertIn('documentoLienzo', script)
        self.assertIn('function ubicarEnLista', script)
        self.assertEqual(script.count('function colocarSeccion'), 1)
        self.assertNotIn('if (listo) post', script)

    def test_una_seccion_agregada_guarda_piezas_y_dos_columnas(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {'accion': f'columnas:{pieza}:2'})
        bloque = self._piezas()[0]['bloques'][0]['id']
        self.assertEqual(self._piezas()[0]['columnas'], 2)
        self.assertEqual(self._piezas()[0]['bloques'][0]['tipo'], 'imagen')
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'nombre__{pieza}': 'Nota interna del laboratorio',
            f'texto__{pieza}-cuerpo': 'Texto de la primera columna',
            f'imagen__{pieza}-{bloque}-foto': _png('blue'),
            f'texto__{pieza}-{bloque}-foto': 'Alt de la pieza interna',
        })
        self.assertEqual(self._piezas()[0]['nombre'], 'Nota interna del laboratorio')
        self.assertEqual(self._piezas()[0]['columnas'], 2)
        lienzo = self.client.get(self.lienzo).content.decode()
        self.assertIn('pieza-diseno-dos', lienzo)
        self.assertIn('Texto de la primera columna', lienzo)
        self.assertIn('Alt de la pieza interna', lienzo)
        self.assertLess(lienzo.find('Texto de la primera columna'), lienzo.find('Alt de la pieza interna'))
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Texto de la primera columna')
        self.assertNotContains(portada, 'Alt de la pieza interna')
        self.assertNotContains(portada, 'Nota interna del laboratorio')
        self.assertNotContains(portada, 'pieza-diseno-dos')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        publicada = self.client.get('/').content.decode()
        self.assertIn('pieza-diseno-dos', publicada)
        self.assertIn('Texto de la primera columna', publicada)
        self.assertIn('Alt de la pieza interna', publicada)
        self.assertLess(
            publicada.find('Texto de la primera columna'),
            publicada.find('Alt de la pieza interna'),
        )
        self.assertNotIn('Nota interna del laboratorio', publicada)

    def test_dos_columnas_en_vivo_quedan_en_el_html_del_lienzo(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        respuesta = self.client.post(
            self.editor,
            {'accion': f'columnas:{pieza}:2'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertNotIn('form-portada', respuesta.content.decode())
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        self.assertIn('pieza-diseno-dos', datos['html_lienzo'])
        self.assertIn('data-columnas="2"', datos['html_lienzo'])
        self.assertEqual(self._piezas()[0]['columnas'], 2)
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'pieza-diseno-dos')
        self.assertContains(lienzo, f'data-seccion="{pieza}"')
        self.assertNotContains(lienzo, 'form-portada')
        self.client.logout()
        self.assertNotContains(self.client.get('/'), 'pieza-diseno-dos')

    def test_la_plantilla_no_gana_columnas_ni_piezas(self):
        respuesta = self.client.post(self.editor, {'accion': 'columnas:nosotros:2'})
        self.assertContains(respuesta, 'sección agregada')
        respuesta = self.client.post(self.editor, {'accion': 'pieza-agregar:nosotros:imagen'})
        self.assertContains(respuesta, 'sección agregada')
        self.client.logout()
        portada = self.client.get('/')
        self.assertContains(portada, 'data-seccion="nosotros"')
        self.assertNotContains(portada, 'pieza-rejilla')
        self.assertNotContains(portada, 'pieza-diseno')

    def test_tres_columnas_reparten_lo_que_ya_hay_sin_publicar(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:boton'})
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{pieza}-cuerpo': 'Texto que ya estaba',
            f'imagen__{pieza}-b01-foto': _png('blue'),
            f'texto__{pieza}-b01-foto': 'Alt que ya estaba',
            f'texto__{pieza}-b02-boton': 'Botón que ya estaba',
        })
        tres = self.client.post(
            self.editor,
            {'accion': f'columnas:{pieza}:3'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(tres.status_code, 200)
        self.assertNotIn('form-portada', tres.content.decode())
        self.assertNotIn('<!DOCTYPE', tres.content.decode())
        datos = tres.json()
        self.assertTrue(datos['ok'])
        html = datos['html_lienzo']
        self.assertIn('pieza-diseno-tres', html)
        self.assertIn('data-columnas="3"', html)
        celdas = self._celdas(html)
        self.assertEqual(sorted(celdas), ['0', '1', '2'])
        self.assertIn(f'data-edit-id="{pieza}-cuerpo"', celdas['0'])
        self.assertIn(f'data-edit-id="{pieza}-b01-foto"', celdas['1'])
        self.assertIn(f'data-edit-id="{pieza}-b02-boton"', celdas['2'])
        self.assertNotIn('pieza-diseno-imagen-texto', html)
        self.assertEqual(self._piezas()[0]['columnas'], 3)
        self.client.logout()
        self.assertNotContains(self.client.get('/'), 'pieza-diseno-tres')
        self.assertNotContains(self.client.get('/'), 'Texto que ya estaba')

        self.client.force_login(self.staff)
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        publicada = self.client.get('/').content.decode()
        self.assertIn('pieza-diseno-tres', publicada)
        self.assertIn('Texto que ya estaba', publicada)
        publicadas = self._celdas(publicada)
        self.assertIn('Texto que ya estaba', publicadas['0'])
        self.assertIn('Alt que ya estaba', publicadas['1'])
        self.assertIn('Botón que ya estaba', publicadas['2'])

    def test_mover_una_pieza_entre_casillas_queda_en_el_borrador(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:boton'})
        self.client.post(self.editor, {'accion': f'columnas:{pieza}:3'})
        respuesta = self.client.post(
            self.editor,
            {'accion': f'pieza-ubicar:{pieza}:b02:0:1'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertNotIn('<!DOCTYPE', respuesta.content.decode())
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        celdas = self._celdas(datos['html_lienzo'])
        self.assertIn(f'data-edit-id="{pieza}-cuerpo"', celdas['0'])
        self.assertIn(f'data-edit-id="{pieza}-b02-boton"', celdas['0'])
        self.assertIn(f'data-edit-id="{pieza}-b01-foto"', celdas['1'])
        self.assertNotIn('b02', celdas['2'])
        puestos = self._piezas()[0]['puestos']
        self.assertEqual(puestos[0]['celda'], 0)
        self.assertNotIn('ref', puestos[0])
        self.assertEqual(puestos[1], {'ref': 'b02', 'celda': 0})
        self.assertEqual(puestos[2], {'ref': 'b01', 'celda': 1})
        self.client.logout()
        self.assertNotContains(self.client.get('/'), f'data-seccion="{pieza}"')

    def test_un_borrador_antiguo_de_dos_columnas_sigue_en_el_lienzo(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='composicion', estado=BloquePortada.Estado.BORRADOR,
        )
        datos = json.loads(fila.texto)
        datos['piezas'][0]['columnas'] = 2
        datos['piezas'][0].pop('diseno', None)
        fila.texto = json.dumps(datos)
        fila.save()
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'pieza-diseno-dos')
        self.client.logout()
        self.assertNotContains(self.client.get('/'), 'pieza-diseno-dos')

    def _celdas(self, html):
        import re

        partes = re.split(r'data-celda="(\d+)"', html)
        celdas = {}
        datos = partes[1:]
        for indice in range(0, len(datos) - 1, 2):
            celdas[datos[indice]] = datos[indice + 1].split('data-celda=', 1)[0]
        return celdas

    def _composicion(self, estado=BloquePortada.Estado.BORRADOR):
        fila = BloquePortada.objects.get(pagina='inicio', clave='composicion', estado=estado)
        return json.loads(fila.texto)

    def _id(self, estado=BloquePortada.Estado.BORRADOR):
        return self._piezas(estado)[0]['id']

    def _piezas(self, estado=BloquePortada.Estado.BORRADOR):
        fila = BloquePortada.objects.get(pagina='inicio', clave='composicion', estado=estado)
        return json.loads(fila.texto)['piezas']
