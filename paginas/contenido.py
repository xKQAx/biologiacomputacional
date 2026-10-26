"""Resuelve y guarda los bloques de la portada.

Lo publicado es lo que ve el visitante. El borrador solo lo ve el lienzo
del editor. Publicar copia el borrador encima de lo publicado.
"""

from django.db import transaction
from django.template.defaultfilters import linebreaksbr

from paginas.catalogo import (
    CATALOGO,
    GRUPOS,
    TEXTO,
    enlace_predeterminado,
    html_subtitulo_visitante,
)
from paginas.models import BloquePortada

MAX_TEXTO = 4000
MAX_ENLACE = 500
_ESQUEMAS = ('javascript:', 'data:', 'vbscript:')


class BloqueVista:
    """Bloque listo para la plantilla: texto publicado, borrador o el de fábrica."""

    def __init__(self, definicion, texto, enlace):
        self.clave = definicion.clave
        self.grupo = definicion.grupo
        self.etiqueta = definicion.etiqueta
        self.tipo = definicion.tipo
        self.vista = definicion.vista
        self.area = definicion.area
        self.texto = texto
        self.enlace = enlace
        self.predeterminado = definicion.texto
        self.usa_rico = bool(definicion.rico and texto == definicion.texto)
        self.html_rico = html_subtitulo_visitante() if definicion.rico else ''

    @property
    def contenido(self):
        """HTML del bloque. El texto del editor se escapa; solo el subtítulo de fábrica trae marcas propias."""
        if self.usa_rico:
            return self.html_rico
        if self.area or '\n' in self.texto:
            return linebreaksbr(self.texto)
        return self.texto

    @property
    def etiqueta_texto(self):
        if self.tipo == 'imagen':
            return 'Texto alternativo'
        return 'Texto'

    @property
    def etiqueta_enlace(self):
        if self.tipo == 'imagen':
            return 'Dirección de la imagen'
        return 'Enlace'


class MapaBloques:
    """Acceso por atributo: {{ bloques.hero_titulo.texto }}."""

    def __init__(self, mapa):
        self._mapa = mapa
        for clave, bloque in mapa.items():
            setattr(self, clave, bloque)

    def __iter__(self):
        return iter(self._mapa.values())


def resolver(preferir_borrador=False):
    """Arma cada bloque. El borrador tapa a lo publicado, y eso al texto de fábrica."""
    estados = [BloquePortada.Estado.PUBLICADO]
    if preferir_borrador:
        estados.append(BloquePortada.Estado.BORRADOR)

    publicados = {}
    borradores = {}
    for fila in BloquePortada.objects.filter(estado__in=estados):
        destino = borradores if fila.estado == BloquePortada.Estado.BORRADOR else publicados
        destino[fila.clave] = fila

    mapa = {}
    for definicion in CATALOGO:
        fuente = borradores.get(definicion.clave) or publicados.get(definicion.clave)
        if fuente is None:
            texto = definicion.texto
            enlace = enlace_predeterminado(definicion)
        else:
            texto = fuente.texto
            enlace = _enlace_de_fila(definicion, fuente.enlace)
        mapa[definicion.clave] = BloqueVista(definicion, texto, enlace)
    return MapaBloques(mapa)


def contexto_publico():
    return {
        'bloques': resolver(preferir_borrador=False),
        'modo_editor': False,
    }


def contexto_lienzo():
    return {
        'bloques': resolver(preferir_borrador=True),
        'modo_editor': True,
    }


def grupos_editor(valores=None):
    """Partes de la portada. Con valores, el formulario muestra lo recién enviado."""
    if valores is None:
        mapa = resolver(preferir_borrador=True)
    else:
        mapa = MapaBloques({
            definicion.clave: BloqueVista(
                definicion,
                valores[definicion.clave][0],
                valores[definicion.clave][1],
            )
            for definicion in CATALOGO
        })
    grupos = []
    for grupo_id, nombre in GRUPOS:
        bloques = [getattr(mapa, item.clave) for item in CATALOGO if item.grupo == grupo_id]
        grupos.append({'id': grupo_id, 'nombre': nombre, 'bloques': bloques})
    return grupos


def hay_borrador():
    return BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).exists()


def leer_valores(post):
    """Arma el formulario y avisa si un valor no se puede guardar.

    Si falta una clave, se conserva lo que ya muestra el editor. Un enlace
    vacío vuelve al anterior. Un enlace inválido o un texto demasiado largo
    no se recorta: se devuelve tal cual para mostrarlo otra vez.
    """
    base = resolver(preferir_borrador=True)
    valores = {}
    errores = []
    for definicion in CATALOGO:
        actual = getattr(base, definicion.clave)
        clave_texto = f'texto__{definicion.clave}'
        if clave_texto in post:
            texto = _normalizar_texto(post.get(clave_texto))
            if len(texto) > MAX_TEXTO:
                errores.append(
                    f'«{definicion.etiqueta}» admite como máximo {MAX_TEXTO} caracteres.'
                )
        else:
            texto = actual.texto

        if definicion.tipo == TEXTO:
            enlace = ''
        else:
            clave_enlace = f'enlace__{definicion.clave}'
            respaldo = actual.enlace or enlace_predeterminado(definicion)
            if clave_enlace in post:
                enlace, error = _interpretar_enlace(
                    post.get(clave_enlace),
                    respaldo,
                    enlace_predeterminado(definicion),
                    definicion.etiqueta,
                )
                if error:
                    errores.append(error)
            else:
                enlace = respaldo
        valores[definicion.clave] = (texto, enlace)
    return valores, errores


def guardar_borrador(valores):
    """Persiste el borrador. No toca lo publicado."""
    _escribir(valores, BloquePortada.Estado.BORRADOR)


def publicar(valores):
    """Copia el contenido del editor a lo que ve el visitante y borra el borrador."""
    with transaction.atomic():
        _escribir(valores, BloquePortada.Estado.PUBLICADO)
        BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).delete()


def descartar_borrador():
    """Borra el borrador. Lo publicado queda igual."""
    BloquePortada.objects.filter(estado=BloquePortada.Estado.BORRADOR).delete()


def _escribir(valores, estado):
    with transaction.atomic():
        for definicion in CATALOGO:
            texto, enlace = valores[definicion.clave]
            BloquePortada.objects.update_or_create(
                clave=definicion.clave,
                estado=estado,
                defaults={
                    'texto': texto,
                    'enlace': enlace,
                    'orden': definicion.orden,
                },
            )


def _enlace_de_fila(definicion, enlace):
    if definicion.tipo == TEXTO:
        return ''
    limpio = (enlace or '').strip()
    if _es_enlace_seguro(limpio):
        return limpio
    return enlace_predeterminado(definicion)


def _normalizar_texto(valor):
    return str(valor or '').replace('\r\n', '\n').replace('\r', '\n').strip()


def _interpretar_enlace(valor, respaldo, predeterminado, etiqueta):
    candidato = str(valor or '').strip()
    if not candidato:
        if _es_enlace_seguro(respaldo):
            return respaldo, None
        return predeterminado, None
    if not _es_enlace_seguro(candidato):
        return candidato, (
            f'El enlace de «{etiqueta}» debe ser una ruta que empiece por / '
            'o una dirección http(s).'
        )
    if len(candidato) > MAX_ENLACE:
        return candidato, (
            f'El enlace de «{etiqueta}» admite como máximo {MAX_ENLACE} caracteres.'
        )
    return candidato, None


def _es_enlace_seguro(enlace):
    if not enlace or any(caracter.isspace() for caracter in enlace):
        return False
    # «//sitio» es una URL de otro dominio, no una ruta del sitio.
    if enlace.startswith('//'):
        return False
    bajo = enlace.lower()
    if bajo.startswith(_ESQUEMAS):
        return False
    return enlace.startswith('/') or bajo.startswith(('https://', 'http://'))
