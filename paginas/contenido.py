"""Resuelve y guarda los bloques de una página pública.

Lo publicado es lo que ve el visitante. El borrador solo lo ve el lienzo
del editor de esa página. Publicar copia el borrador encima de lo publicado
y no toca el borrador de las demás.
"""

import re

from django.db import transaction
from django.template.defaultfilters import linebreaksbr

from paginas.catalogo import (
    IMAGEN,
    TEXTO,
    enlace_predeterminado,
    html_subtitulo_visitante,
    nombre_legible,
)
from paginas.imagenes import (
    almacenar,
    archivo_util,
    enlaces_subidos,
    olvidar,
    validar_subida,
)
from paginas.models import BloquePortada
from paginas.registro import INICIO, INDICES
from paginas.saneo import PLANO, html_para_plantilla, preparar_texto, sin_marcas

MAX_TEXTO = 4000
MAX_ALT = 200
MAX_ENLACE = 500
_ESQUEMAS = ('javascript:', 'data:', 'vbscript:')
_ANCLA = re.compile(r'^#[A-Za-z][A-Za-z0-9_-]*$')
# Cada sección ocupa un millar. El resto del número conserva el campo dentro de ella.
_PASO_SECCION = 1000


class BloqueVista:
    """Bloque listo para la plantilla: texto publicado, borrador o el de fábrica."""

    def __init__(self, definicion, texto, enlace, nombres):
        self.clave = definicion.clave
        self.grupo = definicion.grupo
        self.etiqueta = definicion.etiqueta
        self.nombre = nombre_legible(definicion, nombres)
        self.tipo = definicion.tipo
        self.vista = definicion.vista
        self.area = definicion.area
        self.texto = texto
        self.enlace = enlace
        self.predeterminado = definicion.texto
        self.perfil = definicion.perfil
        self.enriquecido = definicion.perfil != PLANO
        self.usa_rico = bool(definicion.rico and texto == definicion.texto)
        self.html_rico = html_subtitulo_visitante() if definicion.rico else ''
        self.errores = {}

    @property
    def contenido(self):
        """HTML del bloque.

        El subtítulo de fábrica conserva sus marcas. El texto enriquecido
        solo se pinta si salió de sanear_html. Lo demás se escapa: un «<»
        antiguo sigue viéndose como texto.
        """
        if self.usa_rico:
            return self.html_rico
        seguro = html_para_plantilla(self.texto, self.perfil)
        if seguro is not None:
            return seguro
        if self.area or '\n' in self.texto:
            return linebreaksbr(self.texto)
        return self.texto

    @property
    def plano(self):
        """Texto sin etiquetas, para aria-label, tooltip o placeholder."""
        return sin_marcas(self.texto, self.perfil)

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


def fusionar(base, extra):
    """Junta dos mapas. Las claves de `extra` pisan a las de `base`."""
    mapa = dict(base._mapa)
    mapa.update(extra._mapa)
    return MapaBloques(mapa)


def _indice(pagina):
    return INDICES[pagina]


def _filas(preferir_borrador, pagina):
    estados = [BloquePortada.Estado.PUBLICADO]
    if preferir_borrador:
        estados.append(BloquePortada.Estado.BORRADOR)
    publicados = {}
    borradores = {}
    filas = BloquePortada.objects.filter(pagina=pagina, estado__in=estados)
    for fila in filas:
        destino = borradores if fila.estado == BloquePortada.Estado.BORRADOR else publicados
        destino[fila.clave] = fila
    return publicados, borradores


def resolver(preferir_borrador=False, pagina=INICIO):
    """Arma cada bloque. El borrador tapa a lo publicado, y eso al texto de fábrica."""
    indice = _indice(pagina)
    publicados, borradores = _filas(preferir_borrador, pagina)
    return _mapa_desde(indice, publicados, borradores if preferir_borrador else {})


def resolver_orden(preferir_borrador=False, pagina=INICIO):
    """Orden de las secciones de contenido. Sin filas, el de la plantilla."""
    indice = _indice(pagina)
    if not indice.secciones:
        return ()
    publicados, borradores = _filas(preferir_borrador, pagina)
    if preferir_borrador and borradores:
        return _ordenar(indice, borradores, publicados)
    return _ordenar(indice, publicados, {})


def secciones_en_orden(preferir_borrador=False, pagina=INICIO):
    indice = _indice(pagina)
    if not indice.secciones:
        return []
    return [indice.plantillas[grupo] for grupo in resolver_orden(preferir_borrador, pagina)]


def _bloques_para(pagina, preferir_borrador):
    """La portada trae barra y pie. El resto suma esos publicados a su propio contenido."""
    propios = resolver(preferir_borrador=preferir_borrador, pagina=pagina)
    if pagina == INICIO:
        return propios
    return fusionar(resolver(preferir_borrador=False, pagina=INICIO), propios)


def contexto_publico(pagina=INICIO, request=None):
    indice = _indice(pagina)
    contexto = {
        'bloques': _bloques_para(pagina, preferir_borrador=False),
        'secciones': secciones_en_orden(preferir_borrador=False, pagina=pagina),
        'modo_editor': False,
    }
    if indice.datos is not None:
        contexto.update(indice.datos(request))
    return contexto


def contexto_lienzo(pagina=INICIO, request=None):
    indice = _indice(pagina)
    contexto = {
        'bloques': _bloques_para(pagina, preferir_borrador=True),
        'secciones': secciones_en_orden(preferir_borrador=True, pagina=pagina),
        'modo_editor': True,
        'catalogo_lienzo': indice.por_clave,
    }
    if indice.datos is not None:
        contexto.update(indice.datos(request))
    return contexto


def grupos_editor(valores=None, orden=None, errores_campo=None, pagina=INICIO):
    """Partes de la página. Con valores, el formulario muestra lo recién enviado.

    En la portada, la barra va primero y el pie al final. En medio, las secciones
    en `orden`. Las demás páginas no reordenan: listan sus partes fijas.
    """
    indice = _indice(pagina)
    if valores is None:
        mapa = resolver(preferir_borrador=True, pagina=pagina)
    else:
        mapa = MapaBloques({
            definicion.clave: BloqueVista(
                definicion,
                valores[definicion.clave][0],
                valores[definicion.clave][1],
                indice.nombres,
            )
            for definicion in indice.catalogo
        })
    if orden is None:
        orden = resolver_orden(preferir_borrador=True, pagina=pagina)
    por_id = {}
    for grupo_id, nombre in indice.grupos:
        por_id[grupo_id] = {
            'id': grupo_id,
            'nombre': nombre,
            'bloques': [getattr(mapa, clave) for clave in indice.claves_por_grupo.get(grupo_id, ())],
            'ordenable': grupo_id in indice.secciones_set,
        }
    if indice.secciones:
        grupos = [por_id['barra'], *[por_id[grupo_id] for grupo_id in orden], por_id['pie']]
    else:
        grupos = [por_id[grupo_id] for grupo_id, _nombre in indice.grupos]
    _marcar_zonas(grupos)
    errores_campo = errores_campo or {}
    for grupo in grupos:
        for bloque in grupo['bloques']:
            bloque.errores = errores_campo.get(bloque.clave, {})
    return grupos


def hay_borrador(pagina=INICIO):
    return BloquePortada.objects.filter(
        pagina=pagina, estado=BloquePortada.Estado.BORRADOR,
    ).exists()


class FormularioPortada:
    """Lo que el editor envió, listo para guardar o para volver a mostrar."""

    def __init__(self, valores, orden, errores, por_campo, imagenes):
        self.valores = valores
        self.orden = orden
        self.errores = errores
        self.por_campo = por_campo
        self.imagenes = imagenes


def leer_valores(post, archivos=None, pagina=INICIO):
    """Arma el formulario y avisa si un valor no se puede guardar.

    Si falta una clave, se conserva lo que ya muestra el editor. Un enlace
    vacío vuelve al anterior. Un enlace inválido, un texto demasiado largo
    o una imagen que no sirve no se recortan ni se guardan: se devuelven
    para mostrarlos otra vez. Sin archivo nuevo, la imagen actual sigue.
    """
    indice = _indice(pagina)
    base = resolver(preferir_borrador=True, pagina=pagina)
    valores = {}
    errores = []
    por_campo = {}
    imagenes = {}
    orden, error_orden = _leer_orden(post, indice)
    if error_orden:
        _anotar(errores, por_campo, 'orden', '', error_orden)
    for definicion in indice.catalogo:
        actual = getattr(base, definicion.clave)
        nombre = nombre_legible(definicion, indice.nombres)
        clave_texto = f'texto__{definicion.clave}'
        if clave_texto in post:
            bruto = post.get(clave_texto)
            # El perfil del bloque elige la lista blanca. Alt, teléfono y correo siguen planos.
            if definicion.perfil == PLANO:
                texto = _normalizar_texto(bruto)
            else:
                texto = preparar_texto(bruto, definicion.perfil)
            if definicion.tipo == IMAGEN and len(texto) > MAX_ALT:
                _anotar(
                    errores, por_campo, definicion.clave, 'texto',
                    f'El texto alternativo de «{nombre}» admite como máximo {MAX_ALT} caracteres.',
                )
            elif len(texto) > MAX_TEXTO:
                _anotar(
                    errores, por_campo, definicion.clave, 'texto',
                    f'«{nombre}» admite como máximo {MAX_TEXTO} caracteres.',
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
                    nombre,
                )
                if error:
                    _anotar(errores, por_campo, definicion.clave, 'enlace', error)
            else:
                enlace = respaldo

        if definicion.tipo == IMAGEN and archivos is not None:
            archivo = archivos.get(f'imagen__{definicion.clave}')
            if archivo_util(archivo):
                detalle = validar_subida(archivo)
                if detalle:
                    _anotar(
                        errores, por_campo, definicion.clave, 'imagen',
                        f'«{nombre}»: {detalle}',
                    )
                else:
                    # El archivo sustituye a la dirección. No se escribe hasta guardar.
                    imagenes[definicion.clave] = archivo
        valores[definicion.clave] = (texto, enlace)
    return FormularioPortada(valores, orden, errores, por_campo, imagenes)


def estado_guardado(pagina=INICIO):
    """Texto, enlaces y orden tal como quedaron la última vez que se guardó."""
    indice = _indice(pagina)
    mapa = resolver(preferir_borrador=True, pagina=pagina)
    textos = {}
    enlaces = {}
    for definicion in indice.catalogo:
        bloque = getattr(mapa, definicion.clave)
        textos[definicion.clave] = bloque.texto
        if definicion.tipo != TEXTO:
            enlaces[definicion.clave] = bloque.enlace
    return {
        'textos': textos,
        'enlaces': enlaces,
        'orden': ','.join(resolver_orden(preferir_borrador=True, pagina=pagina)),
    }


def primer_grupo_con_error(por_campo, pagina=INICIO):
    """Grupo del primer campo rechazado, para abrirlo al volver a pintar."""
    if not por_campo:
        return None
    indice = _indice(pagina)
    for definicion in indice.catalogo:
        if por_campo.get(definicion.clave):
            return definicion.grupo
    return None


def guardar_borrador(valores, orden, imagenes=None, pagina=INICIO):
    """Persiste el borrador, incluido el orden y las fotos nuevas. No toca lo publicado."""
    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    _escribir(_con_imagenes(valores, imagenes), BloquePortada.Estado.BORRADOR, orden, pagina)
    olvidar(anteriores)


def publicar(valores, orden, imagenes=None, pagina=INICIO):
    """Copia el contenido del editor a lo que ve el visitante y borra el borrador de esta página."""
    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    anteriores.extend(enlaces_subidos(BloquePortada.Estado.PUBLICADO, pagina))
    with transaction.atomic():
        _escribir(_con_imagenes(valores, imagenes), BloquePortada.Estado.PUBLICADO, orden, pagina)
        BloquePortada.objects.filter(
            pagina=pagina, estado=BloquePortada.Estado.BORRADOR,
        ).delete()
    olvidar(anteriores)


def descartar_borrador(pagina=INICIO):
    """Borra el borrador de esta página. Lo publicado, fotos incluidas, queda igual."""
    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    BloquePortada.objects.filter(
        pagina=pagina, estado=BloquePortada.Estado.BORRADOR,
    ).delete()
    olvidar(anteriores)


def _con_imagenes(valores, imagenes):
    """La foto nueva pasa a ser la dirección del bloque. Sin archivo, queda la de ahora."""
    if not imagenes:
        return valores
    ajustados = dict(valores)
    for clave, archivo in imagenes.items():
        texto, _enlace = ajustados[clave]
        ajustados[clave] = (texto, almacenar(archivo))
    return ajustados


def _anotar(errores, por_campo, clave, campo, mensaje):
    errores.append(mensaje)
    if not campo:
        por_campo[clave] = mensaje
        return
    por_campo.setdefault(clave, {})
    por_campo[clave][campo] = mensaje


def _escribir(valores, estado, orden, pagina):
    indice = _indice(pagina)
    posicion = {grupo_id: i for i, grupo_id in enumerate(orden)}
    with transaction.atomic():
        for definicion in indice.catalogo:
            texto, enlace = valores[definicion.clave]
            BloquePortada.objects.update_or_create(
                pagina=pagina,
                clave=definicion.clave,
                estado=estado,
                defaults={
                    'texto': texto,
                    'enlace': enlace,
                    'orden': _orden_fila(definicion, posicion, indice),
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
            f'El enlace de «{etiqueta}» debe ser una ruta que empiece por /, '
            'una dirección http(s) o un ancla de la misma página.'
        )
    if len(candidato) > MAX_ENLACE:
        return candidato, (
            f'El enlace de «{etiqueta}» admite como máximo {MAX_ENLACE} caracteres.'
        )
    return candidato, None


def _mapa_desde(indice, publicados, borradores):
    mapa = {}
    for definicion in indice.catalogo:
        fuente = borradores.get(definicion.clave) or publicados.get(definicion.clave)
        if fuente is None:
            texto = definicion.texto
            enlace = enlace_predeterminado(definicion)
        else:
            texto = fuente.texto
            enlace = _enlace_de_fila(definicion, fuente.enlace)
        mapa[definicion.clave] = BloqueVista(definicion, texto, enlace, indice.nombres)
    return MapaBloques(mapa)


def _ordenar(indice, primarias, secundarias):
    if not _hay_seccion(indice, primarias) and not _hay_seccion(indice, secundarias):
        return indice.secciones

    def clave(grupo_id):
        if _tiene_grupo(indice, grupo_id, primarias):
            return _min_orden(indice, grupo_id, primarias)
        if _tiene_grupo(indice, grupo_id, secundarias):
            return _min_orden(indice, grupo_id, secundarias)
        return _orden_catalogo(indice, grupo_id)

    return tuple(sorted(indice.secciones, key=clave))


def _hay_seccion(indice, filas):
    return any(_tiene_grupo(indice, grupo_id, filas) for grupo_id in indice.secciones)


def _tiene_grupo(indice, grupo_id, filas):
    return any(clave in filas for clave in indice.claves_por_grupo.get(grupo_id, ()))


def _min_orden(indice, grupo_id, filas):
    return min(
        filas[clave].orden
        for clave in indice.claves_por_grupo[grupo_id]
        if clave in filas
    )


def _orden_catalogo(indice, grupo_id):
    for definicion in indice.catalogo:
        if definicion.grupo == grupo_id:
            return definicion.orden
    return 0


def _orden_fila(definicion, posicion, indice):
    if definicion.grupo not in posicion:
        return definicion.orden
    return (posicion[definicion.grupo] + 1) * _PASO_SECCION + indice.indice_en_grupo[definicion.clave]


def _leer_orden(post, indice):
    """Permite solo una permutación de las secciones de contenido."""
    if not indice.secciones:
        return [], None
    respaldo = list(resolver_orden(preferir_borrador=True, pagina=indice.slug))
    if 'orden_secciones' not in post:
        return respaldo, None
    partes = [
        parte.strip()
        for parte in str(post.get('orden_secciones') or '').split(',')
        if parte.strip()
    ]
    if len(partes) != len(indice.secciones) or set(partes) != set(indice.secciones):
        return respaldo, (
            'El orden de las secciones no es válido. '
            'Solo se pueden reordenar las secciones del contenido.'
        )
    return partes, None


def _marcar_zonas(grupos):
    """Separa la barra, las secciones con flechas y el pie. Sin secciones, una sola lista."""
    indices = [i for i, grupo in enumerate(grupos) if grupo['ordenable']]
    if not indices:
        for grupo in grupos:
            grupo['zona'] = 'lista'
        return
    primero = indices[0]
    for i, grupo in enumerate(grupos):
        if grupo['ordenable']:
            grupo['zona'] = 'seccion'
        elif i < primero:
            grupo['zona'] = 'antes'
        else:
            grupo['zona'] = 'despues'


def _es_enlace_seguro(enlace):
    if not enlace or any(caracter.isspace() for caracter in enlace):
        return False
    # Los iconos de redes y dos enlaces legales salen de fábrica con «#».
    # «#seccion1» es un ancla de la misma página.
    if enlace == '#' or _ANCLA.fullmatch(enlace):
        return True
    # «//sitio» es una URL de otro dominio, no una ruta del sitio.
    if enlace.startswith('//'):
        return False
    bajo = enlace.lower()
    if bajo.startswith(_ESQUEMAS):
        return False
    return enlace.startswith('/') or bajo.startswith(('https://', 'http://'))
