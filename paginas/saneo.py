"""Saneo único del texto enriquecido.

Estrategia: el perfil elige la lista blanca y guardar y pintar llaman a la
misma función. Línea (título, botón, etiqueta) admite negrita, cursiva,
subrayado y enlace. Bloque (párrafo e introducción) suma párrafos y listas.
Un título no conserva una lista.

El texto plano antiguo no lleva la marca. Un «<» guardado así no se
interpreta como etiqueta.
"""

import re
from html import escape, unescape
from html.parser import HTMLParser

from django.utils.safestring import mark_safe

# Marca que solo escribe este módulo. El texto ya guardado no la tiene.
PREFIJO_HTML = '<!--biocom-html-->'

PLANO = 'plano'
LINEA = 'linea'
BLOQUE = 'bloque'

_ETIQUETAS_LINEA = frozenset({'br', 'strong', 'em', 'u', 'a'})
_ETIQUETAS_BLOQUE = _ETIQUETAS_LINEA | frozenset({'p', 'ul', 'ol', 'li'})
_VACIAS = frozenset({'br'})
_ALIAS = {'b': 'strong', 'i': 'em', 'ins': 'u'}
# Se elimina la etiqueta y lo que hay dentro: un script no debe quedar como texto.
_DESCARTAR = frozenset({
    'script', 'style', 'iframe', 'object', 'embed', 'noscript', 'template',
    'svg', 'math',
})
_ESQUEMAS = frozenset({'http', 'https', 'mailto'})
_FORMATO = frozenset({'strong', 'em', 'u', 'b', 'i', 'ins', 'ul', 'ol', 'li', 'a'})
# Espacios y controles escondidos, para que «java\nscript:» no pase.
_IGNORADOS = re.compile(
    r'[\x00-\x20\x7f\u00a0\u1680\u2000-\u200d\u2028\u2029\u202f\u205f\u2060\u3000\ufeff]+'
)
_MAX_HREF = 2000


def preparar_texto(valor, perfil=BLOQUE):
    """Texto listo para la base.

    Sin la marca queda plano, aunque traiga «<». Con la marca se sanea según
    el perfil. Si solo había párrafos y saltos, se guarda como texto plano:
    publicar sin formato no cambia lo que ya veía el visitante.
    """
    texto = str(valor or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    perfil = _perfil(perfil)
    if perfil == PLANO or not texto.startswith(PREFIJO_HTML):
        return texto
    html = sanear_html(texto[len(PREFIJO_HTML):], perfil)
    if not html:
        return ''
    plano = a_texto_plano(html)
    if plano is not None:
        return plano.strip()
    return PREFIJO_HTML + html


def html_para_plantilla(texto, perfil):
    """HTML ya saneado para la plantilla, o None si hay que escaparlo.

    Se sanea otra vez al pintar: la fila pudo cambiarse fuera del editor.
    El SafeString sale solo de aquí, nunca de la entrada cruda.
    """
    perfil = _perfil(perfil, ausente=PLANO)
    if perfil == PLANO or not texto or not str(texto).startswith(PREFIJO_HTML):
        return None
    return mark_safe(sanear_html(str(texto)[len(PREFIJO_HTML):], perfil))


def sin_marcas(texto, perfil=BLOQUE):
    """Texto visible sin etiquetas, para aria-label, tooltip o placeholder."""
    bruto = str(texto or '')
    perfil = _perfil(perfil, ausente=PLANO)
    if perfil == PLANO or not bruto.startswith(PREFIJO_HTML):
        return bruto
    html = sanear_html(bruto[len(PREFIJO_HTML):], perfil)
    parser = _APlano()
    parser.feed(html)
    parser.close()
    return ''.join(parser.partes)


def sanear_html(fragmento, perfil=BLOQUE):
    """Deja solo las etiquetas del perfil y enlaces http, https o mailto."""
    parser = _Saneador(_etiquetas(perfil))
    parser.feed(fragmento or '')
    parser.close()
    return ''.join(parser.partes)


def a_texto_plano(html):
    """Texto con saltos, o None si hay negrita, cursiva, subrayado, listas o enlaces."""
    parser = _APlano()
    parser.feed(html or '')
    parser.close()
    if parser.formato:
        return None
    return ''.join(parser.partes)


def _perfil(perfil, ausente=BLOQUE):
    if perfil is True:
        return BLOQUE
    if perfil is False or perfil is None:
        return ausente
    if perfil == '':
        return ausente
    if perfil not in (PLANO, LINEA, BLOQUE):
        raise ValueError(f'Perfil de saneo desconocido: {perfil}')
    return perfil


def _etiquetas(perfil):
    perfil = _perfil(perfil)
    if perfil == LINEA:
        return _ETIQUETAS_LINEA
    if perfil == BLOQUE:
        return _ETIQUETAS_BLOQUE
    raise ValueError(f'Perfil de saneo desconocido: {perfil}')


class _Saneador(HTMLParser):
    def __init__(self, etiquetas):
        super().__init__(convert_charrefs=True)
        self.etiquetas = etiquetas
        self.partes = []
        self._pila = []
        self._descartar = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._descartar:
            self._descartar += 1
            return
        if tag in _DESCARTAR:
            self._descartar = 1
            return
        tag = _ALIAS.get(tag, tag)
        if tag not in self.etiquetas:
            # Una lista descartada en un título no debe pegar las palabras.
            if tag == 'li':
                self.partes.append(' ')
            return
        if tag == 'a':
            href = _href_de(attrs)
            if not href:
                return
            if tag in self._pila:
                self._cerrar_hasta(tag)
            self.partes.append(f'<a href="{escape(href, quote=True)}">')
            self._pila.append('a')
            return
        if tag in _VACIAS:
            self.partes.append('<br>')
            return
        if tag in ('p', 'li') and tag in self._pila:
            self._cerrar_hasta(tag)
        self.partes.append(f'<{tag}>')
        self._pila.append(tag)

    def handle_endtag(self, tag):
        if self._descartar:
            self._descartar -= 1
            return
        tag = _ALIAS.get(tag.lower(), tag.lower())
        if tag not in self.etiquetas or tag in _VACIAS:
            return
        if tag in self._pila:
            self._cerrar_hasta(tag)

    def handle_data(self, data):
        if self._descartar or not data:
            return
        self.partes.append(escape(data))

    def close(self):
        super().close()
        while self._pila:
            self.partes.append(f'</{self._pila.pop()}>')

    def _cerrar_hasta(self, tag):
        while self._pila:
            abierto = self._pila.pop()
            self.partes.append(f'</{abierto}>')
            if abierto == tag:
                return


class _APlano(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.formato = False
        self.partes = []
        self._parrafo = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _FORMATO:
            self.formato = True
        elif tag == 'br':
            self.partes.append('\n')
        elif tag == 'p':
            if self._parrafo:
                self.partes.append('\n')
            self._parrafo = True
        else:
            self.formato = True

    def handle_data(self, data):
        self.partes.append(data)


def _href_de(attrs):
    vistos = [valor for nombre, valor in attrs if nombre.lower() == 'href']
    if not vistos:
        return None
    seguros = [_normalizar_href(valor) for valor in vistos]
    if any(item is None for item in seguros):
        return None
    return seguros[0]


def _normalizar_href(valor):
    if valor is None:
        return None
    compacto = _IGNORADOS.sub('', unescape(str(valor)))
    if not compacto or '\\' in compacto or len(compacto) > _MAX_HREF:
        return None
    bajo = compacto.lower()
    # «//sitio» es un protocolo relativo, no una ruta del laboratorio.
    if bajo.startswith('//'):
        return None
    if ':' not in bajo:
        return None
    esquema, resto = bajo.split(':', 1)
    if esquema not in _ESQUEMAS or not resto:
        return None
    return compacto
