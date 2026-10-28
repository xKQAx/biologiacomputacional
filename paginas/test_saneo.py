from django.test import SimpleTestCase

from paginas.saneo import (
    LINEA,
    PREFIJO_HTML,
    html_para_plantilla,
    preparar_texto,
    sanear_html,
    sin_marcas,
)


class SaneoHtmlTests(SimpleTestCase):
    def test_conserva_negrita_cursiva_lista_y_enlace(self):
        html = sanear_html(
            '<p>Hola <b>negrita</b> y <i>cursiva</i></p>'
            '<ul><li>uno</li></ul><ol><li>dos</li></ol>'
            '<a href="https://example.com/lab">sitio</a>'
            '<a href="mailto:lab@example.com">correo</a>'
            '<a href="http://example.com">web</a>'
        )
        self.assertIn('<strong>negrita</strong>', html)
        self.assertIn('<em>cursiva</em>', html)
        self.assertIn('<ul><li>uno</li></ul>', html)
        self.assertIn('<ol><li>dos</li></ol>', html)
        self.assertIn('href="https://example.com/lab"', html)
        self.assertIn('href="mailto:lab@example.com"', html)
        self.assertIn('href="http://example.com"', html)
        self.assertNotIn('<b>', html)
        self.assertNotIn('<i>', html)

    def test_elimina_script_javascript_data_y_protocolo_relativo(self):
        html = sanear_html(
            '<p>Visible</p><script>alert(1)</script>'
            '<a href="javascript:alert(1)">malo</a>'
            '<a href="JavaScript:alert(2)">otro</a>'
            '<a href="java&#10;script:alert(3)">salto</a>'
            '<a href="data:text/html,hi">dato</a>'
            '<a href="//evil.example">relativo</a>'
            '<a href="/ruta">interna</a>'
            '<img src=x onerror="alert(1)">'
            '<p style="color:red" onclick="alert(1)">limpio</p>'
        )
        self.assertIn('Visible', html)
        self.assertIn('limpio', html)
        self.assertNotIn('<script', html.lower())
        self.assertNotIn('javascript:', html.lower())
        self.assertNotIn('alert(1)', html)
        self.assertNotIn('data:', html.lower())
        self.assertNotIn('evil.example', html)
        self.assertNotIn('onclick', html)
        self.assertNotIn('style=', html)
        self.assertNotIn('href="/ruta"', html)

    def test_sin_marca_el_menor_que_sigue_siendo_texto(self):
        guardado = preparar_texto('Precio < 10 <script>alert(1)</script>')
        self.assertEqual(guardado, 'Precio < 10 <script>alert(1)</script>')
        self.assertIsNone(html_para_plantilla(guardado, True))
        self.assertIsNone(html_para_plantilla(PREFIJO_HTML + '<p><strong>x</strong></p>', False))

    def test_con_marca_se_sanea_y_sin_formato_vuelve_a_plano(self):
        self.assertEqual(preparar_texto(PREFIJO_HTML + '<p>Hola</p>'), 'Hola')
        marcado = preparar_texto(PREFIJO_HTML + '<p><b>Hola</b></p><script>alert(1)</script>')
        self.assertTrue(marcado.startswith(PREFIJO_HTML))
        self.assertIn('<strong>Hola</strong>', marcado)
        self.assertNotIn('script', marcado.lower())
        pintado = html_para_plantilla(marcado, True)
        self.assertIn('<strong>Hola</strong>', str(pintado))
        self.assertNotIn(PREFIJO_HTML, str(pintado))

    def test_subrayado_y_lista_numerada_siguen_en_el_parrafo(self):
        html = sanear_html('<p>Hay <u>subrayado</u> e <ins>otro</ins></p><ol><li>dos</li></ol>')
        self.assertIn('<u>subrayado</u>', html)
        self.assertIn('<u>otro</u>', html)
        self.assertIn('<ol><li>dos</li></ol>', html)
        guardado = preparar_texto(PREFIJO_HTML + html)
        self.assertIn('<u>subrayado</u>', guardado)
        self.assertIn('<ol><li>dos</li></ol>', guardado)

    def test_en_un_titulo_se_guarda_la_linea_y_se_quita_la_lista(self):
        guardado = preparar_texto(
            PREFIJO_HTML
            + '<strong>Hola</strong> <em>mundo</em> <u>raya</u> '
            + '<a href="https://example.com/lab">web</a>'
            + '<ul><li>no</li></ul><ol><li>tampoco</li></ol>'
            + '<script>alert(1)</script>'
            + '<a href="javascript:alert(1)">malo</a>'
            + '<a href="data:text/html,hi">dato</a>',
            LINEA,
        )
        self.assertIn('<strong>Hola</strong>', guardado)
        self.assertIn('<em>mundo</em>', guardado)
        self.assertIn('<u>raya</u>', guardado)
        self.assertIn('href="https://example.com/lab"', guardado)
        self.assertNotIn('<ul', guardado)
        self.assertNotIn('<ol', guardado)
        self.assertNotIn('<li', guardado)
        self.assertNotIn('<p', guardado)
        self.assertNotIn('script', guardado.lower())
        self.assertNotIn('javascript:', guardado.lower())
        self.assertNotIn('data:', guardado.lower())
        plano = sin_marcas(guardado, LINEA)
        self.assertTrue(plano.startswith('Hola mundo raya web'))
        self.assertNotIn('<', plano)
        self.assertNotIn('alert', plano)
