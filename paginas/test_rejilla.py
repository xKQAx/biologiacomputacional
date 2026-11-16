"""Lógica de la cuadrícula libre y su guardado en el borrador."""

import io
import json
import re
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from paginas.models import BloquePortada
from paginas.piezas import Composicion, Pieza, Puesto, mutar, parsear, serializar
from paginas.rejilla import (
    aplicar_preset,
    con_span,
    derivar_columnas,
    derivar_movil,
    poner,
    quitar,
    resolver,
    soltar,
)


def _png():
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(buffer, format='PNG')
    return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')


class RejillaPuraTests(SimpleTestCase):
    def test_el_preset_conserva_las_piezas_y_no_las_solapa(self):
        refs = ('', 'b01', 'b02', 'b03')
        rejilla = aplicar_preset(refs, 2, 2)
        self.assertEqual(rejilla.columnas, 2)
        self.assertEqual(rejilla.filas, 2)
        self.assertEqual(tuple(pos.ref for pos in rejilla.posiciones), refs)
        ocupadas = []
        for posicion in rejilla.posiciones:
            for fila in range(posicion.fila, posicion.fila + posicion.filas):
                for columna in range(posicion.columna, posicion.columna + posicion.columnas):
                    ocupadas.append((fila, columna))
        self.assertEqual(len(ocupadas), len(set(ocupadas)))
        self.assertTrue(all(1 <= fila <= 2 and 1 <= columna <= 2 for fila, columna in ocupadas))

    def test_el_preset_crece_si_hay_mas_piezas_que_celdas(self):
        rejilla = aplicar_preset(('a', 'b', 'c', 'd', 'e'), 2, 2)
        self.assertEqual(rejilla.columnas, 2)
        self.assertEqual(rejilla.filas, 3)
        self.assertEqual(len(rejilla.posiciones), 5)

    def test_soltar_en_vacia_libera_la_anterior_y_en_ocupada_intercambia(self):
        rejilla = aplicar_preset(('', 'b01'), 2, 2)
        movida, error = soltar(rejilla, 'b01', 2, 1)
        self.assertIsNone(error)
        self.assertEqual(_en(movida, 'b01'), (2, 1))
        self.assertEqual(_en(movida, ''), (1, 1))
        cambiada, error = soltar(movida, '', 2, 1)
        self.assertIsNone(error)
        self.assertEqual(_en(cambiada, ''), (2, 1))
        self.assertEqual(_en(cambiada, 'b01'), (1, 1))

    def test_un_span_que_no_cabe_no_cambia_la_rejilla(self):
        rejilla = aplicar_preset(('', 'b01'), 2, 1)
        misma, error = con_span(rejilla, '', 1, 2)
        self.assertIsNotNone(error)
        self.assertEqual(misma, rejilla)
        fuera, error = soltar(rejilla, '', 1, 2)
        self.assertIsNone(error)
        ancha, error = con_span(fuera, '', 1, 2)
        self.assertIsNotNone(error)
        self.assertEqual(_en(ancha, ''), (1, 2))

    def test_cambiar_un_dispositivo_no_pisa_los_otros(self):
        base = derivar_columnas((('',), ('b01',)))
        movil = derivar_movil((('',), ('b01',)))
        escritorio = aplicar_preset(('', 'b01'), 3, 2, base)
        pares = poner((), 'escritorio', escritorio)
        pares = poner(pares, 'movil', movil)
        self.assertEqual(dict(pares)['escritorio'], escritorio)
        self.assertNotIn('tablet', dict(pares))
        resueltas = resolver((('',), ('b01',)), dict(pares))
        self.assertEqual(resueltas['escritorio'].columnas, 3)
        self.assertEqual(resueltas['tablet'], base)
        self.assertEqual(resueltas['movil'].columnas, 1)
        self.assertEqual(resueltas['movil'].filas, 2)
        sin_movil = quitar(pares, 'movil')
        self.assertEqual(tuple(nombre for nombre, _rejilla in sin_movil), ('escritorio',))

    def test_el_movil_predeterminado_apila_cada_columna(self):
        grupos = (('', 'b01'), ('b02', 'b03'))
        movil = derivar_movil(grupos)
        self.assertEqual(
            [(pos.ref, pos.fila, pos.columna) for pos in movil.posiciones],
            [('', 1, 1), ('b01', 2, 1), ('b02', 3, 1), ('b03', 4, 1)],
        )
        escritorio = aplicar_preset(('b03', 'b02', '', 'b01'), 2, 2)
        solo_escritorio = resolver(grupos, {'escritorio': escritorio})
        self.assertEqual(solo_escritorio['escritorio'], escritorio)
        self.assertEqual(
            [pos.ref for pos in solo_escritorio['movil'].posiciones],
            ['', 'b01', 'b02', 'b03'],
        )
        personal = aplicar_preset(('b03', '', 'b01', 'b02'), 1, 4)
        con_movil = resolver(grupos, {'movil': personal})
        self.assertEqual(con_movil['movil'], personal)

    def test_soltar_no_intercambia_si_los_spans_no_caben(self):
        rejilla = aplicar_preset(('', 'b01'), 3, 2)
        alta, error = con_span(rejilla, '', 2, 1)
        self.assertIsNone(error)
        ancha, error = con_span(alta, 'b01', 2, 2)
        self.assertIsNone(error)
        misma, error = soltar(ancha, '', 1, 2)
        self.assertIsNotNone(error)
        self.assertEqual(misma, ancha)

    def test_una_composicion_vieja_sigue_en_columnas(self):
        comp = parsear(json.dumps({
            'ocultas': [],
            'piezas': [{
                'id': 'pz1234abcd',
                'tipo': 'texto',
                'visible': True,
                'columnas': 2,
                'puestos': [{'celda': 0}, {'ref': 'b01', 'celda': 1}],
                'bloques': [{'id': 'b01', 'tipo': 'imagen'}],
            }],
        }))
        pieza = comp.piezas[0]
        self.assertEqual(pieza.distribucion, ())
        self.assertEqual(pieza.columnas, 2)
        self.assertEqual(pieza.puestos[1], Puesto('b01', 1))
        otra = serializar(comp)
        self.assertNotIn('distribucion', otra)

    def test_el_id_del_mosaico_de_plantilla_no_colisiona_con_secciones(self):
        comp = parsear(json.dumps({
            'piezas': [{'id': 'pz00000000', 'tipo': 'texto'}],
            'layout_encontrar': {'id': 'pz00000000', 'tipo': 'tarjeta'},
        }))
        self.assertEqual(comp.piezas, ())
        self.assertEqual(comp.layout_encontrar.id, 'pz00000000')

    def test_la_mutacion_de_escritorio_no_borra_el_texto_ni_el_movil(self):
        pieza = Pieza(
            id='pz1234abcd',
            tipo='texto',
            columnas=1,
            bloques=(),
            puestos=(Puesto('', 0),),
            distribucion=poner((), 'movil', aplicar_preset(('',), 1, 2)),
        )
        comp = Composicion((), (pieza,))
        valores = {'pz1234abcd-cuerpo': ('Texto que ya estaba', '')}
        nueva, orden, valores, error = mutar(
            comp, ['pz1234abcd'], valores, 'rejilla-preset:pz1234abcd:escritorio:2x2', None,
        )
        self.assertIsNone(error)
        guardada = dict(nueva.piezas[0].distribucion)
        self.assertEqual(guardada['escritorio'].columnas, 2)
        self.assertEqual(guardada['escritorio'].filas, 2)
        self.assertEqual(guardada['movil'].filas, 2)
        self.assertEqual(guardada['movil'].columnas, 1)
        self.assertEqual(valores['pz1234abcd-cuerpo'][0], 'Texto que ya estaba')
        self.assertNotIn('tablet', guardada)
        crudo = json.loads(serializar(nueva))
        self.assertEqual(set(crudo['piezas'][0]['distribucion']), {'escritorio', 'movil'})


def _estilo_mosaico(html):
    """El <style> de la cuadrícula, para ver el selector real y no el texto suelto."""
    estilos = re.findall(r'<style>(.*?)</style>', html, flags=re.DOTALL)
    return next((estilo for estilo in estilos if 'pieza-mosaico-item' in estilo), '')


def _en(rejilla, ref):
    for posicion in rejilla.posiciones:
        if posicion.ref == ref:
            return posicion.fila, posicion.columna
    return None


class RejillaEditorTests(TestCase):
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
            'gestor_rejilla', 'rejilla@example.com', 'ClaveSegura1', is_staff=True,
        )
        self.client.force_login(self.staff)

    def _id(self):
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='composicion', estado=BloquePortada.Estado.BORRADOR,
        )
        return json.loads(fila.texto)['piezas'][0]['id']

    def _pieza(self):
        fila = BloquePortada.objects.get(
            pagina='inicio', clave='composicion', estado=BloquePortada.Estado.BORRADOR,
        )
        return json.loads(fila.texto)['piezas'][0]

    def test_el_preset_se_guarda_y_la_publicacion_no_lleva_guias(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{pieza}-cuerpo': 'Párrafo que no debe moverse',
            f'imagen__{pieza}-b01-foto': _png(),
            f'texto__{pieza}-b01-foto': 'Alt que sigue',
        })
        respuesta = self.client.post(
            self.editor,
            {'accion': f'rejilla-preset:{pieza}:escritorio:2x2'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        self.assertIn('pieza-mosaico', datos['html_lienzo'])
        self.assertIn('data-guia-celda', datos['html_lienzo'])
        self.assertIn('html[data-dispositivo="escritorio"]', datos['html_lienzo'])
        self.assertIn('data-mapa="', datos['html_lienzo'])
        self.assertNotIn('Ajustes de la cuadrícula', datos['html_campos'])
        self.assertNotIn('data-aplicar-medida', datos['html_campos'])
        self.assertNotIn('data-span=', datos['html_campos'])
        self.assertNotIn('data-aplicar-span', datos['html_campos'])
        self.assertIn('Párrafo que no debe moverse', datos['html_lienzo'])
        self.assertIn('grid-column:1 / span 1', datos['html_lienzo'])
        self.assertIn('grid-column: 1 / span 1', datos['html_lienzo'])
        self.assertIn('data-ocupante="propia"', datos['html_lienzo'])
        self.assertNotIn('Aplicar esta cuadrícula', datos['html_campos'])
        self.assertNotIn('Usar el diseño predeterminado', datos['html_campos'])
        self.assertNotIn('editor-lista-rejilla', datos['html_campos'])
        self.assertIn('data-preset="2x1"', datos['html_campos'])
        estilo_editor = _estilo_mosaico(datos['html_lienzo'])
        self.assertIn('>.pieza-mosaico-item[data-ref="propia"]', estilo_editor)
        self.assertNotIn('&gt;', estilo_editor)
        self.assertNotIn('&quot;', estilo_editor)
        self.assertIn('html[data-dispositivo="escritorio"]', estilo_editor)
        guardada = self._pieza()
        self.assertIn('escritorio', guardada['distribucion'])
        self.assertNotIn('tablet', guardada['distribucion'])
        self.assertEqual(guardada['bloques'][0]['tipo'], 'imagen')
        self.client.post(self.editor, {'accion': f'rejilla-preset:{pieza}:movil:1x2'})
        guardada = self._pieza()
        self.assertEqual(guardada['distribucion']['escritorio']['columnas'], 2)
        self.assertEqual(guardada['distribucion']['movil']['columnas'], 1)
        self.assertEqual(guardada['distribucion']['movil']['filas'], 2)
        self.client.post(self.editor, {'accion': 'publicar'})
        self.client.logout()
        publicada = self.client.get('/').content.decode()
        self.assertIn('pieza-mosaico', publicada)
        self.assertIn('Párrafo que no debe moverse', publicada)
        self.assertIn('@media (max-width:767.98px)', publicada)
        self.assertNotIn('html[data-dispositivo', publicada)
        self.assertNotIn('data-guia-celda', publicada)
        self.assertNotIn('data-mapa', publicada)
        self.assertNotIn('pieza-guias-clasicas', publicada)
        self.assertNotIn('draggable', publicada)
        estilo = _estilo_mosaico(publicada)
        self.assertIn('>.pieza-mosaico-item[data-ref="propia"]', estilo)
        self.assertNotIn('&gt;', estilo)
        self.assertNotIn('&quot;', estilo)
        self.assertNotIn('html[data-dispositivo', estilo)

    def test_el_arrastre_intercambia_y_un_span_invalido_no_borra_el_contenido(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:boton'})
        self.client.post(self.editor, {'accion': f'rejilla-preset:{pieza}:escritorio:2x1'})
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{pieza}-cuerpo': 'Cuerpo fijo',
            f'texto__{pieza}-b01-boton': 'Botón fijo',
        })
        self.client.post(self.editor, {'accion': f'rejilla-mover:{pieza}:escritorio:b01:1:1'})
        posiciones = {
            item['id']: (item['fila'], item['columna'])
            for item in self._pieza()['distribucion']['escritorio']['posiciones']
        }
        self.assertEqual(posiciones['b01'], (1, 1))
        self.assertEqual(posiciones['propia'], (1, 2))
        rechazo = self.client.post(
            self.editor,
            {'accion': f'rejilla-span:{pieza}:escritorio:propia:1:2'},
        )
        self.assertContains(rechazo, 'no cabe')
        self.assertEqual(self._pieza()['distribucion']['escritorio']['columnas'], 2)
        self.client.logout()
        portada = self.client.get('/')
        self.assertNotContains(portada, 'Cuerpo fijo')

    def test_un_span_rechazado_en_vivo_no_trae_html_ni_guarda_el_numero(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:boton'})
        self.client.post(self.editor, {'accion': f'rejilla-preset:{pieza}:escritorio:2x1'})
        respuesta = self.client.post(
            self.editor,
            {'accion': f'rejilla-span:{pieza}:escritorio:propia:1:2'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        datos = respuesta.json()
        self.assertFalse(datos['ok'])
        self.assertIn('no cabe', datos['aviso'])
        self.assertNotIn('html_campos', datos)
        self.assertNotIn('html_lienzo', datos)
        posiciones = {
            item['id']: item
            for item in self._pieza()['distribucion']['escritorio']['posiciones']
        }
        self.assertEqual(posiciones['propia']['columnas'], 1)
        self.assertEqual(posiciones['propia']['filas'], 1)
        self.assertEqual(self._pieza()['distribucion']['escritorio']['columnas'], 2)

    def test_una_columna_ya_guardada_sale_de_la_cuadricula_libre(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {
            'accion': 'guardar',
            f'texto__{pieza}-cuerpo': 'Párrafo que sigue en columnas',
        })
        self.assertNotIn('columnas', self._pieza())
        self.client.post(self.editor, {'accion': f'rejilla-preset:{pieza}:escritorio:2x2'})
        self.assertIn('distribucion', self._pieza())
        respuesta = self.client.post(
            self.editor,
            {'accion': f'columnas:{pieza}:1'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        self.assertIn('Columnas guardadas', datos['aviso'])
        guardada = self._pieza()
        self.assertNotIn('distribucion', guardada)
        self.assertEqual(guardada['bloques'][0]['tipo'], 'imagen')
        self.assertNotIn('pieza-mosaico', datos['html_lienzo'])
        self.assertIn('pieza-diseno-una', datos['html_lienzo'])
        self.assertIn('Párrafo que sigue en columnas', datos['html_lienzo'])
        self.assertNotIn('html[data-dispositivo', datos['html_lienzo'])

    def test_agregar_en_una_celda_ocupada_no_intercambia(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'pieza-agregar:{pieza}:imagen'})
        self.client.post(self.editor, {'accion': f'rejilla-preset:{pieza}:escritorio:2x2'})
        antes = self._pieza()
        ocupada = antes['distribucion']['escritorio']['posiciones'][0]
        rechazo = self.client.post(
            self.editor,
            {
                'accion': (
                    f"rejilla-agregar:{pieza}:escritorio:boton:"
                    f"{ocupada['fila']}:{ocupada['columna']}"
                ),
            },
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        datos = rechazo.json()
        self.assertFalse(datos['ok'])
        self.assertIn('ocupada', datos['aviso'])
        despues = self._pieza()
        self.assertEqual(despues['bloques'], antes['bloques'])
        self.assertEqual(
            despues['distribucion']['escritorio']['posiciones'],
            antes['distribucion']['escritorio']['posiciones'],
        )
        ocupadas = {
            (item['fila'], item['columna'])
            for item in despues['distribucion']['escritorio']['posiciones']
        }
        libre = next(
            (fila, columna)
            for fila in range(1, 3)
            for columna in range(1, 3)
            if (fila, columna) not in ocupadas
        )
        alta = self.client.post(
            self.editor,
            {'accion': f'rejilla-agregar:{pieza}:escritorio:boton:{libre[0]}:{libre[1]}'},
            HTTP_X_EDITOR_VIVO='1',
            HTTP_ACCEPT='application/json',
        )
        self.assertTrue(alta.json()['ok'])
        piezas = self._pieza()
        self.assertEqual([bloque['tipo'] for bloque in piezas['bloques']], ['imagen', 'boton'])
        puesta = next(
            item for item in piezas['distribucion']['escritorio']['posiciones']
            if item['id'] == 'b02'
        )
        self.assertEqual((puesta['fila'], puesta['columna']), libre)

    def test_las_columnas_clasicas_siguen_sin_distribucion(self):
        self.client.post(self.editor, {'accion': 'agregar', 'tipo_pieza': 'texto'})
        pieza = self._id()
        self.client.post(self.editor, {'accion': f'columnas:{pieza}:2'})
        self.assertNotIn('distribucion', self._pieza())
        lienzo = self.client.get(self.lienzo)
        self.assertContains(lienzo, 'pieza-diseno-dos')
        self.assertContains(lienzo, 'pieza-celda')
        self.assertNotContains(lienzo, 'pieza-guias-clasicas')
        self.client.logout()
        self.assertNotContains(self.client.get('/'), 'pieza-guias-clasicas')
        self.assertNotContains(self.client.get('/'), 'pieza-guia-celda')
        self.assertNotContains(self.client.get('/'), 'pieza-diseno-dos')
