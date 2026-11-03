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
from paginas.piezas import (
    CLAVE_COMPOSICION,
    REF_PROPIA,
    TIPOS,
    TOKEN_PROPIA,
    CamposPieza,
    CasillaVista,
    CeldaVista,
    Composicion,
    DiaVista,
    Pieza,
    SeccionVista,
    casillas_de,
    con_columnas,
    con_nombres,
    con_visibilidad,
    elegir,
    en_rejilla,
    materializar,
    materializar_todas,
    nombres_de_fabrica,
    nombres_piezas,
    serializar,
)
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
        self.solo_enlace = definicion.solo_enlace
        self.dia = definicion.dia
        self.trozo = definicion.trozo
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
    publicados, borradores, comp = _capa(preferir_borrador, pagina)
    return _mapa_desde(indice, publicados, borradores, comp)


def resolver_orden(preferir_borrador=False, pagina=INICIO):
    """Orden de las secciones de contenido. Sin filas, el de la plantilla."""
    indice = _indice(pagina)
    if not indice.secciones:
        return ()
    publicados, borradores, comp = _capa(preferir_borrador, pagina)
    if preferir_borrador and borradores:
        return _ordenar(indice, borradores, publicados, comp)
    return _ordenar(indice, publicados, {}, comp)


def secciones_en_orden(preferir_borrador=False, pagina=INICIO, incluir_ocultas=False):
    """Plantillas en el orden visible. Una sección oculta no sale en la página pública."""
    indice = _indice(pagina)
    if not indice.secciones:
        return []
    publicados, borradores, comp = _capa(preferir_borrador, pagina)
    mapa = _mapa_desde(indice, publicados, borradores, comp)
    if preferir_borrador and borradores:
        orden = _ordenar(indice, borradores, publicados, comp)
    else:
        orden = _ordenar(indice, publicados, {}, comp)
    return _vistas(indice, comp, mapa, orden, incluir_ocultas)


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
        'secciones': secciones_en_orden(
            preferir_borrador=False, pagina=pagina, incluir_ocultas=False,
        ),
        'modo_editor': False,
    }
    if indice.datos is not None:
        contexto.update(indice.datos(request))
    return contexto


def contexto_lienzo(pagina=INICIO, request=None):
    indice = _indice(pagina)
    contexto = {
        'bloques': _bloques_para(pagina, preferir_borrador=True),
        # La vista previa es el borrador como lo vería el visitante: oculta no va en el HTML.
        'secciones': secciones_en_orden(
            preferir_borrador=True, pagina=pagina, incluir_ocultas=False,
        ),
        'modo_editor': True,
        'catalogo_lienzo': _catalogo_de(pagina, preferir_borrador=True),
    }
    if indice.datos is not None:
        contexto.update(indice.datos(request))
    return contexto


def grupos_editor(
    valores=None, orden=None, errores_campo=None, pagina=INICIO, composicion=None,
):
    """Partes de la página. Con valores, el formulario muestra lo recién enviado.

    En la portada, la barra va primero y el pie al final. En medio, las secciones
    de la plantilla y las agregadas, en `orden`. Las demás páginas no reordenan.
    """
    indice = _indice(pagina)
    if not indice.permite_piezas:
        composicion = Composicion()
    elif composicion is None:
        composicion = _composicion_actual(True, pagina)
    extras = materializar_todas(composicion)
    nombres = dict(indice.nombres)
    nombres.update(nombres_piezas(composicion))
    fabricas = nombres_de_fabrica(composicion)
    if valores is None:
        mapa = resolver(preferir_borrador=True, pagina=pagina)
    else:
        mapa = MapaBloques({
            definicion.clave: BloqueVista(
                definicion,
                valores[definicion.clave][0],
                valores[definicion.clave][1],
                nombres,
            )
            for definicion in list(indice.catalogo) + extras
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
            'agregada': False,
            'oculta': grupo_id in composicion.ocultas,
            'tipo': '',
            'columnas': 1,
            'casillas': (),
            'internas': (),
        }
    for pieza in composicion.piezas:
        defs = materializar(pieza)
        por_id[pieza.id] = {
            'id': pieza.id,
            'nombre': nombres[pieza.id],
            'bloques': [getattr(mapa, definicion.clave) for definicion in defs],
            'ordenable': True,
            'agregada': True,
            'oculta': not pieza.visible,
            'tipo': pieza.tipo,
            'nombre_propio': pieza.nombre,
            'nombre_fabrica': fabricas.get(pieza.id, ''),
            'columnas': pieza.columnas,
            'casillas': _casillas_editor(pieza),
            'internas': _internas_editor(pieza),
        }
    if indice.secciones:
        grupos = [por_id['barra']]
        grupos.extend(por_id[grupo_id] for grupo_id in orden if grupo_id in por_id)
        grupos.append(por_id['pie'])
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

    def __init__(self, valores, orden, errores, por_campo, imagenes, composicion=None):
        self.valores = valores
        self.orden = orden
        self.errores = errores
        self.por_campo = por_campo
        self.imagenes = imagenes
        self.composicion = composicion if composicion is not None else Composicion()


def leer_valores(post, archivos=None, pagina=INICIO):
    """Arma el formulario y avisa si un valor no se puede guardar.

    Si falta una clave, se conserva lo que ya muestra el editor. Un enlace
    vacío vuelve al anterior. Un enlace inválido, un texto demasiado largo
    o una imagen que no sirve no se recortan ni se guardan: se devuelven
    para mostrarlos otra vez. Sin archivo nuevo, la imagen actual sigue.
    """
    indice = _indice(pagina)
    publicados, borradores, comp = _capa(True, pagina)
    errores_nombre = []
    if indice.permite_piezas:
        comp = con_visibilidad(comp, post)
        comp, errores_nombre = con_nombres(comp, post)
        comp = con_columnas(comp, post)
    else:
        comp = Composicion()
    base = _mapa_desde(indice, publicados, borradores, comp)
    valores = {}
    errores = list(errores_nombre)
    por_campo = {}
    imagenes = {}
    orden, error_orden = _leer_orden(post, indice, comp)
    if error_orden:
        _anotar(errores, por_campo, 'orden', '', error_orden)
    definiciones = list(indice.catalogo) + materializar_todas(comp)
    nombres = dict(indice.nombres)
    nombres.update(nombres_piezas(comp))
    for definicion in definiciones:
        actual = getattr(base, definicion.clave)
        nombre = nombre_legible(definicion, nombres)
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
    return FormularioPortada(valores, orden, errores, por_campo, imagenes, comp)


def estado_guardado(pagina=INICIO):
    """Texto, enlaces y orden tal como quedaron la última vez que se guardó."""
    indice = _indice(pagina)
    mapa = resolver(preferir_borrador=True, pagina=pagina)
    comp = _composicion_actual(True, pagina) if indice.permite_piezas else Composicion()
    textos = {}
    enlaces = {}
    definiciones = list(indice.catalogo)
    if indice.permite_piezas:
        definiciones.extend(materializar_todas(comp))
    for definicion in definiciones:
        bloque = getattr(mapa, definicion.clave)
        textos[definicion.clave] = bloque.texto
        if definicion.tipo != TEXTO:
            enlaces[definicion.clave] = bloque.enlace
    return {
        'textos': textos,
        'enlaces': enlaces,
        'orden': ','.join(resolver_orden(preferir_borrador=True, pagina=pagina)),
        'nombres': {pieza.id: pieza.nombre for pieza in comp.piezas},
    }


def primer_grupo_con_error(por_campo, pagina=INICIO):
    """Grupo del primer campo rechazado, para abrirlo al volver a pintar."""
    if not por_campo:
        return None
    indice = _indice(pagina)
    comp = _composicion_actual(True, pagina) if indice.permite_piezas else Composicion()
    for definicion in list(indice.catalogo) + materializar_todas(comp):
        if por_campo.get(definicion.clave):
            return definicion.grupo
    return None


def guardar_borrador(valores, orden, imagenes=None, pagina=INICIO, composicion=None):
    """Persiste el borrador, incluido el orden y las fotos nuevas. No toca lo publicado."""
    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    _escribir(
        _con_imagenes(valores, imagenes),
        BloquePortada.Estado.BORRADOR,
        orden,
        pagina,
        composicion,
    )
    olvidar(anteriores)


def publicar(valores, orden, imagenes=None, pagina=INICIO, composicion=None, usuario=None):
    """Copia el contenido del editor a lo que ve el visitante y borra el borrador de esta página.

    Después guarda una copia en el historial de esta página, no en el de las demás.
    """
    from paginas.historial import archivar

    anteriores = enlaces_subidos(BloquePortada.Estado.BORRADOR, pagina)
    anteriores.extend(enlaces_subidos(BloquePortada.Estado.PUBLICADO, pagina))
    with transaction.atomic():
        _escribir(
            _con_imagenes(valores, imagenes),
            BloquePortada.Estado.PUBLICADO,
            orden,
            pagina,
            composicion,
        )
        BloquePortada.objects.filter(
            pagina=pagina, estado=BloquePortada.Estado.BORRADOR,
        ).delete()
        archivar(pagina, usuario)
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


def _escribir(valores, estado, orden, pagina, composicion=None):
    indice = _indice(pagina)
    if not indice.permite_piezas or composicion is None:
        composicion = Composicion()
    extras = materializar_todas(composicion) if indice.permite_piezas else []
    posicion = {grupo_id: i for i, grupo_id in enumerate(orden)}
    with transaction.atomic():
        for definicion in list(indice.catalogo) + extras:
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
        if indice.permite_piezas:
            # La composición es un bloque más: mismo estado, no otro borrador.
            BloquePortada.objects.update_or_create(
                pagina=pagina,
                clave=CLAVE_COMPOSICION,
                estado=estado,
                defaults={'texto': serializar(composicion), 'enlace': '', 'orden': 0},
            )
            conservar = {definicion.clave for definicion in indice.catalogo}
            conservar.update(definicion.clave for definicion in extras)
            conservar.add(CLAVE_COMPOSICION)
            BloquePortada.objects.filter(
                pagina=pagina, estado=estado,
            ).exclude(clave__in=conservar).delete()


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


def _mapa_desde(indice, publicados, borradores, composicion=None):
    composicion = composicion or Composicion()
    nombres = dict(indice.nombres)
    nombres.update(nombres_piezas(composicion))
    mapa = {}
    for definicion in list(indice.catalogo) + materializar_todas(composicion):
        fuente = borradores.get(definicion.clave) or publicados.get(definicion.clave)
        if fuente is None:
            texto = definicion.texto
            enlace = enlace_predeterminado(definicion)
        else:
            texto = fuente.texto
            enlace = _enlace_de_fila(definicion, fuente.enlace)
        mapa[definicion.clave] = BloqueVista(definicion, texto, enlace, nombres)
    return MapaBloques(mapa)


def _ordenar(indice, primarias, secundarias, composicion=None):
    composicion = composicion or Composicion()
    grupos = list(indice.secciones) + [pieza.id for pieza in composicion.piezas]
    if (
        not _hay_seccion(indice, primarias)
        and not _hay_seccion(indice, secundarias)
        and not _hay_piezas(composicion, primarias)
        and not _hay_piezas(composicion, secundarias)
    ):
        return tuple(grupos)

    def clave(grupo_id):
        orden = _min_en(indice, grupo_id, primarias, composicion)
        if orden is not None:
            return orden
        orden = _min_en(indice, grupo_id, secundarias, composicion)
        if orden is not None:
            return orden
        return _respaldo_orden(indice, grupo_id, composicion)

    return tuple(sorted(grupos, key=clave))


def _hay_seccion(indice, filas):
    return any(_tiene_grupo(indice, grupo_id, filas) for grupo_id in indice.secciones)


def _tiene_grupo(indice, grupo_id, filas):
    return any(clave in filas for clave in indice.claves_por_grupo.get(grupo_id, ()))


def _hay_piezas(composicion, filas):
    for pieza in composicion.piezas:
        if any(definicion.clave in filas for definicion in materializar(pieza)):
            return True
    return False


def _min_en(indice, grupo_id, filas, composicion):
    if grupo_id in indice.secciones_set:
        presentes = [
            filas[clave].orden
            for clave in indice.claves_por_grupo.get(grupo_id, ())
            if clave in filas
        ]
        return min(presentes) if presentes else None
    pieza = composicion.por_id(grupo_id)
    if pieza is None:
        return None
    presentes = [
        filas[definicion.clave].orden
        for definicion in materializar(pieza)
        if definicion.clave in filas
    ]
    return min(presentes) if presentes else None


def _respaldo_orden(indice, grupo_id, composicion):
    if grupo_id in indice.secciones_set:
        return _orden_catalogo(indice, grupo_id)
    for indice_pieza, pieza in enumerate(composicion.piezas):
        if pieza.id == grupo_id:
            return 100000 + indice_pieza
    return 1000000


def _orden_catalogo(indice, grupo_id):
    for definicion in indice.catalogo:
        if definicion.grupo == grupo_id:
            return definicion.orden
    return 0


def _orden_fila(definicion, posicion, indice):
    if definicion.grupo not in posicion:
        return definicion.orden
    if definicion.clave in indice.indice_en_grupo:
        dentro = indice.indice_en_grupo[definicion.clave]
    else:
        dentro = max(definicion.orden // 10 - 1, 0)
    return (posicion[definicion.grupo] + 1) * _PASO_SECCION + dentro


def _leer_orden(post, indice, composicion=None):
    """Permite una permutación de la plantilla más las secciones agregadas."""
    if not indice.secciones:
        return [], None
    composicion = composicion or Composicion()
    respaldo = list(resolver_orden(preferir_borrador=True, pagina=indice.slug))
    if 'orden_secciones' not in post:
        return respaldo, None
    partes = [
        parte.strip()
        for parte in str(post.get('orden_secciones') or '').split(',')
        if parte.strip()
    ]
    esperadas = list(indice.secciones) + [pieza.id for pieza in composicion.piezas]
    if len(partes) != len(esperadas) or set(partes) != set(esperadas):
        return respaldo, (
            'El orden de las secciones no es válido. '
            'Solo se pueden reordenar las secciones del contenido.'
        )
    return partes, None


def _capa(preferir_borrador, pagina):
    publicados, borradores = _filas(preferir_borrador, pagina)
    return publicados, borradores, _composicion(pagina, publicados, borradores, preferir_borrador)


def _composicion(pagina, publicados, borradores, preferir_borrador):
    if not _indice(pagina).permite_piezas:
        return Composicion()
    return elegir(publicados, borradores, preferir_borrador)


def _composicion_actual(preferir_borrador, pagina):
    _publicados, _borradores, comp = _capa(preferir_borrador, pagina)
    return comp


def _catalogo_de(pagina, preferir_borrador):
    indice = _indice(pagina)
    comp = _composicion_actual(preferir_borrador, pagina)
    definiciones = list(indice.catalogo) + materializar_todas(comp)
    return {item.clave: item for item in definiciones}


def _vistas(indice, comp, mapa, orden, incluir_ocultas):
    vistas = []
    for grupo_id in orden:
        if grupo_id in indice.secciones_set:
            oculta = grupo_id in comp.ocultas
            if oculta and not incluir_ocultas:
                continue
            vistas.append(SeccionVista(
                grupo_id, indice.plantillas[grupo_id], oculta=oculta,
            ))
            continue
        pieza = comp.por_id(grupo_id)
        if pieza is None or (not pieza.visible and not incluir_ocultas):
            continue
        if en_rejilla(pieza):
            vistas.append(_vista_compuesta(pieza, mapa))
            continue
        if pieza.tipo == 'carrusel':
            vistas.append(_vista_carrusel(pieza, mapa))
            continue
        vistas.append(SeccionVista(
            pieza.id,
            TIPOS[pieza.tipo].plantilla,
            libre=True,
            oculta=not pieza.visible,
            campos=_campos_de(pieza, mapa),
        ))
    return vistas


def _vista_carrusel(pieza, mapa):
    """Cada diapositiva reúne la imagen y, si lo hay, su enlace opcional."""
    return SeccionVista(
        pieza.id,
        TIPOS[pieza.tipo].plantilla,
        libre=True,
        oculta=not pieza.visible,
        diapositivas=_dias_de(pieza, mapa),
    )


def _vista_compuesta(pieza, mapa):
    """La cuadrícula y, dentro de cada casilla, las piezas en el orden guardado."""
    casillas = []
    for indice, refs in enumerate(casillas_de(pieza)):
        piezas = []
        for ref in refs:
            if ref == REF_PROPIA:
                piezas.append(_celda_nativa(pieza, mapa))
                continue
            bloque = next(item for item in pieza.bloques if item.id == ref)
            piezas.append(_celda_interna(pieza, bloque, mapa))
        casillas.append(CasillaVista(indice, tuple(piezas)))
    return SeccionVista(
        pieza.id,
        'inicio/secciones/pieza_compuesta.html',
        libre=True,
        oculta=not pieza.visible,
        columnas=pieza.columnas,
        casillas=tuple(casillas),
    )


def _celda_interna(seccion, bloque, mapa):
    ancla = f'{seccion.id}-{bloque.id}'
    fantasma = Pieza(
        id=ancla, tipo=bloque.tipo, diapositivas=bloque.diapositivas,
    )
    return CeldaVista(
        bloque.tipo,
        ancla,
        None if bloque.tipo == 'carrusel' else _campos_de(fantasma, mapa),
        _dias_de(fantasma, mapa) if bloque.tipo == 'carrusel' else (),
    )


def _celda_nativa(pieza, mapa):
    if pieza.tipo == 'carrusel':
        return CeldaVista(pieza.tipo, pieza.id, None, _dias_de(pieza, mapa))
    return CeldaVista(pieza.tipo, pieza.id, _campos_de(pieza, mapa), ())


def _campos_de(pieza, mapa):
    campos = {}
    for definicion in materializar(pieza):
        if definicion.trozo:
            continue
        sufijo = definicion.clave[len(pieza.id) + 1:]
        campos[sufijo] = getattr(mapa, definicion.clave)
    return CamposPieza(campos)


def _dias_de(pieza, mapa):
    if pieza.tipo != 'carrusel':
        return ()
    return tuple(
        DiaVista(
            dia,
            getattr(mapa, f'{pieza.id}-d{dia}'),
            getattr(mapa, f'{pieza.id}-r{dia}'),
        )
        for dia in (pieza.diapositivas or ('01',))
    )


def _casillas_editor(pieza):
    """Lo que el inspector arrastra. El token «propia» es el contenido de la sección."""
    nombres = {item['id']: item for item in _internas_editor(pieza)}
    casillas = []
    for indice, refs in enumerate(casillas_de(pieza)):
        piezas = []
        for ref in refs:
            if ref == REF_PROPIA:
                piezas.append({
                    'ref': TOKEN_PROPIA,
                    'tipo': pieza.tipo,
                    'nombre': TIPOS[pieza.tipo].nombre,
                })
                continue
            interno = nombres.get(ref)
            if interno is None:
                continue
            piezas.append({
                'ref': ref,
                'tipo': interno['tipo'],
                'nombre': interno['nombre'],
            })
        casillas.append({'indice': indice, 'piezas': piezas})
    return tuple(casillas)


def _internas_editor(pieza):
    """Nombre de cada pieza interna. Si hay dos del mismo tipo, se numeran."""
    conteo = {}
    for bloque in pieza.bloques:
        conteo[bloque.tipo] = conteo.get(bloque.tipo, 0) + 1
    vistos = {}
    lista = []
    for bloque in pieza.bloques:
        base = TIPOS[bloque.tipo].nombre
        if conteo[bloque.tipo] > 1:
            vistos[bloque.tipo] = vistos.get(bloque.tipo, 0) + 1
            nombre = f'{base} {vistos[bloque.tipo]}'
        else:
            nombre = base
        lista.append({'id': bloque.id, 'tipo': bloque.tipo, 'nombre': nombre})
    return tuple(lista)


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
