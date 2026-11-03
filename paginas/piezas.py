"""Secciones que se agregan a una página que ya existe.

Fábrica: cada tipo del catálogo produce DefinicionBloque, el mismo registro
que la plantilla. No hay otro borrador. La fila `composicion` guarda qué
secciones hay y cuáles están ocultas, con el mismo estado (borrador o
publicado) que el resto de los bloques. Si el borrador no tiene esa fila,
se hereda la publicada.
"""

import json
import re
import uuid
from dataclasses import dataclass, replace

from paginas.catalogo import (
    BLOQUE,
    ENLACE,
    IMAGEN,
    LINEA,
    PLANO,
    SECCIONES,
    TEXTO,
    DefinicionBloque,
)

CLAVE_COMPOSICION = 'composicion'
MAX_PIEZAS = 24
MAX_DIAPOSITIVAS = 8
MAX_BLOQUES = 8
MAX_NOMBRE = 80
MAX_COLUMNAS = 3
PREFIJO_ID = 'pz'
# El contenido propio de la sección, dentro de la cuadrícula. No es un bloque interno.
REF_PROPIA = ''
TOKEN_PROPIA = 'propia'
# Piezas que caben dentro de una sección agregada. El encabezado sigue siendo una sección.
TIPOS_INTERNOS = ('texto', 'imagen', 'carrusel', 'boton')
# Borradores viejos: el diseño fijo pasa a un número de columnas iguales.
_COLUMNAS_DE_DISENO = {
    'una': 1,
    'dos': 2,
    'imagen-texto': 2,
    'texto-imagen': 2,
    'tres': 3,
}

_ID = re.compile(r'^pz[0-9a-f]{8}$')
_DIA = re.compile(r'^[0-9]{2}$')
_BLOQUE = re.compile(r'^b[0-9]{2}$')


@dataclass(frozen=True)
class Puesto:
    """Dónde se sienta una pieza. ref vacío es el contenido propio de la sección.

    Patrón Composite: la sección agrupa casillas y cada casilla agrupa piezas.
    Cambiar el número de columnas reparte las piezas que ya estaban.
    """

    ref: str
    celda: int


@dataclass(frozen=True)
class CampoTipo:
    sufijo: str
    etiqueta: str
    texto: str
    tipo: str = TEXTO
    formato: str = ''
    enlace: str = ''
    multilinea: bool = False


@dataclass(frozen=True)
class TipoSeccion:
    """Un tipo del catálogo y la plantilla con la que se pinta."""

    id: str
    nombre: str
    plantilla: str
    campos: tuple


@dataclass(frozen=True)
class BloqueInterno:
    """Pieza dentro de una sección agregada. La fábrica de bloques es la misma."""

    id: str
    tipo: str
    diapositivas: tuple = ()


@dataclass(frozen=True)
class Pieza:
    id: str
    tipo: str
    visible: bool = True
    diapositivas: tuple = ()
    nombre: str = ''
    columnas: int = 1
    puestos: tuple = ()
    bloques: tuple = ()


@dataclass(frozen=True)
class Composicion:
    ocultas: tuple = ()
    piezas: tuple = ()

    def por_id(self, pieza_id):
        for pieza in self.piezas:
            if pieza.id == pieza_id:
                return pieza
        return None


def _construir_fijos(pieza):
    """Copia los campos del tipo y les pone la clave de esta instancia."""
    tipo = TIPOS[pieza.tipo]
    definiciones = []
    for indice, campo in enumerate(tipo.campos):
        definiciones.append(DefinicionBloque(
            clave=f'{pieza.id}-{campo.sufijo}',
            grupo=pieza.id,
            etiqueta=campo.etiqueta,
            texto=campo.texto,
            tipo=campo.tipo,
            enlace=campo.enlace,
            formato=campo.formato,
            multilinea=campo.multilinea,
            orden=(indice + 1) * 10,
        ))
    return definiciones


def _construir_carrusel(pieza):
    """Una diapositiva es un bloque de imagen más otro solo para el enlace.

    No usa investigacion.Carrusel: aquel tiene tres fotos fijas y su propio
    borrador. Aquí el archivo, el alt y el enlace pasan por el mismo bloque.
    """
    diapositivas = pieza.diapositivas or ('01',)
    definiciones = []
    for indice, dia in enumerate(diapositivas):
        definiciones.append(DefinicionBloque(
            clave=f'{pieza.id}-d{dia}',
            grupo=pieza.id,
            etiqueta=f'Diapositiva {indice + 1}',
            texto='',
            tipo=IMAGEN,
            orden=(indice + 1) * 10,
            dia=dia,
        ))
        definiciones.append(DefinicionBloque(
            clave=f'{pieza.id}-r{dia}',
            grupo=pieza.id,
            etiqueta=f'Diapositiva {indice + 1}: enlace',
            texto='',
            tipo=ENLACE,
            formato=PLANO,
            solo_enlace=True,
            orden=(indice + 1) * 10 + 1,
        ))
    return definiciones


TIPOS = {
    'encabezado': TipoSeccion(
        'encabezado',
        'Encabezado',
        'inicio/secciones/pieza_encabezado.html',
        (
            CampoTipo('titulo', 'Título', 'Nuevo encabezado', formato=LINEA),
            CampoTipo(
                'bajada', 'Bajada', '', formato=BLOQUE, multilinea=True,
            ),
        ),
    ),
    'texto': TipoSeccion(
        'texto',
        'Texto',
        'inicio/secciones/pieza_texto.html',
        (
            CampoTipo(
                'cuerpo', 'Texto', 'Nuevo texto.', formato=BLOQUE, multilinea=True,
            ),
        ),
    ),
    'imagen': TipoSeccion(
        'imagen',
        'Imagen',
        'inicio/secciones/pieza_imagen.html',
        (
            CampoTipo('foto', 'Imagen', '', tipo=IMAGEN),
        ),
    ),
    'boton': TipoSeccion(
        'boton',
        'Botón',
        'inicio/secciones/pieza_boton.html',
        (
            CampoTipo(
                'boton', 'Botón', 'Nuevo botón', tipo=ENLACE, formato=LINEA, enlace='#',
            ),
        ),
    ),
    'carrusel': TipoSeccion(
        'carrusel',
        'Carrusel',
        'inicio/secciones/pieza_carrusel.html',
        (),
    ),
}

_CONSTRUCTORES = {tipo_id: _construir_fijos for tipo_id in TIPOS}
_CONSTRUCTORES['carrusel'] = _construir_carrusel
# El fragmento pinta la pieza dentro de la rejilla. La plantilla de TIPOS la pinta sola.
FRAGMENTOS = {
    'encabezado': 'inicio/secciones/fragmentos/encabezado.html',
    'texto': 'inicio/secciones/fragmentos/texto.html',
    'imagen': 'inicio/secciones/fragmentos/imagen.html',
    'boton': 'inicio/secciones/fragmentos/boton.html',
    'carrusel': 'inicio/secciones/fragmentos/carrusel.html',
}
_NOMBRE_PANEL = {
    'encabezado': 'Encabezado agregado',
    'texto': 'Texto agregado',
    'imagen': 'Imagen agregada',
    'boton': 'Botón agregado',
    'carrusel': 'Carrusel agregado',
}


class SeccionVista:
    """Lo que el bucle de la portada incluye: plantilla fija o sección agregada."""

    def __init__(
        self, id_seccion, plantilla, *, libre=False, oculta=False,
        campos=None, diapositivas=(), columnas=1, casillas=(),
    ):
        self.id = id_seccion
        self.plantilla = plantilla
        self.libre = libre
        self.oculta = oculta
        self.campos = campos
        self.diapositivas = diapositivas
        self.columnas = columnas if columnas in (1, 2, 3) else 1
        self.casillas = casillas

    @property
    def variante(self):
        """Clase de la portada: una, dos o tres columnas iguales."""
        return {1: 'una', 2: 'dos', 3: 'tres'}[self.columnas]


class CasillaVista:
    """Una columna de la cuadrícula. Sin piezas, el hueco queda libre."""

    def __init__(self, indice, piezas):
        self.indice = indice
        self.piezas = piezas
        self.vacia = not piezas


class CeldaVista:
    """Una pieza dentro de una casilla. Varias pueden compartir la misma."""

    def __init__(self, tipo, ancla, campos=None, diapositivas=()):
        self.tipo = tipo
        self.ancla = ancla
        self.campos = campos
        self.diapositivas = diapositivas
        self.plantilla = FRAGMENTOS[tipo]


class DiaVista:
    """Imagen de una diapositiva y el bloque de su enlace opcional."""

    def __init__(self, id_dia, foto, destino):
        self.id = id_dia
        self.foto = foto
        self.destino = destino


class CamposPieza:
    def __init__(self, campos):
        for nombre, bloque in campos.items():
            setattr(self, nombre, bloque)


def tipos_editor():
    return tuple(TIPOS[tipo_id] for tipo_id in TIPOS)


def tipos_internos():
    """Catálogo que se puede meter dentro de una sección agregada."""
    return tuple(TIPOS[tipo_id] for tipo_id in TIPOS_INTERNOS)


def materializar(pieza):
    """Bloques de la sección y, si los hay, los de cada pieza interna."""
    construir = _CONSTRUCTORES.get(pieza.tipo, _construir_fijos)
    definiciones = list(construir(pieza))
    for bloque in pieza.bloques:
        definiciones.extend(_materializar_interno(pieza, bloque))
    return definiciones


def _materializar_interno(seccion, bloque):
    """Misma fábrica, con la clave de la pieza y el grupo de la sección."""
    ancla = f'{seccion.id}-{bloque.id}'
    fantasma = Pieza(id=ancla, tipo=bloque.tipo, diapositivas=bloque.diapositivas)
    definiciones = []
    for item in _CONSTRUCTORES[bloque.tipo](fantasma):
        definiciones.append(replace(
            item,
            grupo=seccion.id,
            etiqueta=f'{TIPOS[bloque.tipo].nombre} · {item.etiqueta}',
            trozo=bloque.id,
        ))
    return definiciones


def en_rejilla(pieza):
    """La plantilla suelta se conserva en una columna y sin piezas internas."""
    return bool(pieza.bloques) or pieza.columnas != 1


def materializar_todas(composicion):
    definiciones = []
    for pieza in composicion.piezas:
        definiciones.extend(materializar(pieza))
    return definiciones


def nombres_de_fabrica(composicion):
    """Nombre de la lista si el admin no escribió otro. No repite el de la plantilla."""
    conteo = {}
    for pieza in composicion.piezas:
        conteo[pieza.tipo] = conteo.get(pieza.tipo, 0) + 1
    vistos = {}
    nombres = {}
    for pieza in composicion.piezas:
        base = _NOMBRE_PANEL[pieza.tipo]
        if conteo[pieza.tipo] == 1:
            nombres[pieza.id] = base
            continue
        vistos[pieza.tipo] = vistos.get(pieza.tipo, 0) + 1
        nombres[pieza.id] = f'{base} {vistos[pieza.tipo]}'
    return nombres


def nombres_piezas(composicion):
    """Lo que ve el admin en la lista. El nombre escrito gana; si no, el de fábrica.

    No es el título público: ese sigue en el campo de la sección, si lo tiene.
    """
    fabrica = nombres_de_fabrica(composicion)
    return {
        pieza.id: pieza.nombre or fabrica[pieza.id]
        for pieza in composicion.piezas
    }


def elegir(publicados, borradores, preferir_borrador):
    """La composición del borrador tapa a la publicada. Sin filas, no hay piezas."""
    if preferir_borrador and CLAVE_COMPOSICION in borradores:
        return parsear(borradores[CLAVE_COMPOSICION].texto)
    if CLAVE_COMPOSICION in publicados:
        return parsear(publicados[CLAVE_COMPOSICION].texto)
    return Composicion()


def parsear(texto):
    try:
        datos = json.loads(texto or '')
    except (TypeError, ValueError):
        return Composicion()
    if not isinstance(datos, dict):
        return Composicion()
    ocultas_brutas = datos.get('ocultas') or []
    if not isinstance(ocultas_brutas, list):
        ocultas_brutas = []
    ocultas = {item for item in ocultas_brutas if item in SECCIONES}
    piezas = []
    vistas = set()
    for item in datos.get('piezas') or []:
        pieza = _pieza(item, vistas)
        if pieza is None:
            continue
        vistas.add(pieza.id)
        piezas.append(pieza)
    return Composicion(
        tuple(seccion for seccion in SECCIONES if seccion in ocultas),
        tuple(piezas),
    )


def serializar(composicion):
    return json.dumps(
        {
            'ocultas': list(composicion.ocultas),
            'piezas': [_serializar_pieza(pieza) for pieza in composicion.piezas],
        },
        ensure_ascii=False,
        separators=(',', ':'),
    )


def con_nombres(composicion, post):
    """Lee nombre__id. Vacío vuelve al de fábrica. Si la clave no vino, no cambia.

    Devuelve la composición y los avisos. Un nombre demasiado largo no se guarda.
    """
    if post is None:
        return composicion, []
    errores = []
    piezas = []
    for pieza in composicion.piezas:
        clave = f'nombre__{pieza.id}'
        if clave not in post:
            piezas.append(pieza)
            continue
        texto = ' '.join(str(post.get(clave) or '').split())
        if len(texto) > MAX_NOMBRE:
            errores.append(
                f'El nombre de la sección admite como máximo {MAX_NOMBRE} caracteres.'
            )
        piezas.append(replace(pieza, nombre=texto))
    return Composicion(composicion.ocultas, tuple(piezas)), errores


def con_columnas(composicion, post):
    """Lee columnas__id si vino en un guardado. El mismo reparto que la acción en vivo."""
    if post is None:
        return composicion
    piezas = []
    for pieza in composicion.piezas:
        clave = f'columnas__{pieza.id}'
        if clave not in post:
            piezas.append(pieza)
            continue
        bruto = str(post.get(clave) or '')
        if bruto not in ('1', '2', '3'):
            piezas.append(pieza)
            continue
        piezas.append(_pieza_con_columnas(pieza, int(bruto)))
    return Composicion(composicion.ocultas, tuple(piezas))


def con_visibilidad(composicion, post):
    """Lee visible__id si vino en el formulario. Si falta, conserva la actual."""
    if post is None:
        return composicion
    ocultas = set(composicion.ocultas)
    for seccion in SECCIONES:
        clave = f'visible__{seccion}'
        if clave not in post:
            continue
        if str(post.get(clave)) == '0':
            ocultas.add(seccion)
        else:
            ocultas.discard(seccion)
    piezas = []
    for pieza in composicion.piezas:
        clave = f'visible__{pieza.id}'
        visible = pieza.visible
        if clave in post:
            visible = str(post.get(clave)) != '0'
        piezas.append(replace(pieza, visible=visible))
    return Composicion(
        tuple(seccion for seccion in SECCIONES if seccion in ocultas),
        tuple(piezas),
    )


def mutar(composicion, orden, valores, accion, tipo_pedido):
    """Aplica agregar, ocultar, mostrar, quitar, piezas internas o diapositivas."""
    if accion == 'agregar':
        return _agregar(composicion, orden, valores, tipo_pedido)
    if accion.startswith('ocultar:'):
        return _visible(composicion, orden, valores, accion.split(':', 1)[1], False)
    if accion.startswith('mostrar:'):
        return _visible(composicion, orden, valores, accion.split(':', 1)[1], True)
    if accion.startswith('quitar:'):
        return _quitar(composicion, orden, valores, accion.split(':', 1)[1])
    if accion.startswith('pieza-agregar:'):
        partes = accion.split(':')
        if len(partes) != 3:
            return composicion, orden, valores, 'No se reconoció la acción.'
        return _agregar_interno(composicion, orden, valores, partes[1], partes[2])
    if accion.startswith('pieza-quitar:'):
        partes = accion.split(':')
        if len(partes) != 3:
            return composicion, orden, valores, 'No se reconoció la acción.'
        return _quitar_interno(composicion, orden, valores, partes[1], partes[2])
    if accion.startswith('pieza-ubicar:'):
        partes = accion.split(':')
        if len(partes) != 5:
            return composicion, orden, valores, 'No se reconoció la acción.'
        return _ubicar_pieza(
            composicion, orden, valores, partes[1], partes[2], partes[3], partes[4],
        )
    if accion.startswith('columnas:'):
        partes = accion.split(':')
        if len(partes) != 3:
            return composicion, orden, valores, 'No se reconoció la acción.'
        return _poner_columnas(composicion, orden, valores, partes[1], partes[2])
    if accion.startswith('dia-'):
        return _mutar_dia(composicion, orden, valores, accion)
    return composicion, orden, valores, 'No se reconoció la acción.'


def es_estructural(accion):
    if accion == 'agregar':
        return True
    return accion.startswith((
        'ocultar:', 'mostrar:', 'quitar:',
        'pieza-agregar:', 'pieza-quitar:', 'pieza-ubicar:', 'columnas:',
        'dia-agregar:', 'dia-quitar:', 'dia-orden:',
    ))


def pendientes_de_imagen(composicion, valores, imagenes=None):
    """Una imagen visible no se publica sin archivo. El borrador sí puede quedar vacío."""
    imagenes = imagenes or {}
    pendientes = []
    for pieza in composicion.piezas:
        if not pieza.visible:
            continue
        for indice, clave in enumerate(_claves_imagen(pieza), start=1):
            _texto, enlace = valores.get(clave, ('', ''))
            if clave in imagenes or str(enlace or '').strip():
                continue
            nombre = nombres_piezas(composicion)[pieza.id]
            if pieza.tipo == 'carrusel':
                detalle = f'«{nombre}», diapositiva {indice}, necesita una imagen'
            else:
                detalle = f'«{nombre}» necesita una imagen'
            pendientes.append((
                clave,
                f'{detalle} antes de publicarse. Súbela o quita la sección.',
            ))
    return pendientes


def valores_de_fabrica(pieza):
    from paginas.catalogo import enlace_predeterminado

    return {
        definicion.clave: (definicion.texto, enlace_predeterminado(definicion))
        for definicion in materializar(pieza)
    }


def _agregar(composicion, orden, valores, tipo_pedido):
    if tipo_pedido not in TIPOS:
        return composicion, orden, valores, 'Esa sección no está en el catálogo.'
    if len(composicion.piezas) >= MAX_PIEZAS:
        return (
            composicion, orden, valores,
            f'Se pueden agregar como máximo {MAX_PIEZAS} secciones.',
        )
    diapositivas = ('01',) if tipo_pedido == 'carrusel' else ()
    pieza = Pieza(
        id=_nuevo_id(composicion),
        tipo=tipo_pedido,
        visible=True,
        diapositivas=diapositivas,
        puestos=(Puesto(REF_PROPIA, 0),),
    )
    valores = dict(valores)
    valores.update(valores_de_fabrica(pieza))
    return (
        Composicion(composicion.ocultas, composicion.piezas + (pieza,)),
        list(orden) + [pieza.id],
        valores,
        None,
    )


def _visible(composicion, orden, valores, pieza_id, visible):
    if pieza_id in ('barra', 'pie'):
        return composicion, orden, valores, 'La barra y el pie se quedan fijos.'
    if pieza_id in SECCIONES:
        ocultas = set(composicion.ocultas)
        if visible:
            ocultas.discard(pieza_id)
        else:
            ocultas.add(pieza_id)
        return (
            Composicion(
                tuple(seccion for seccion in SECCIONES if seccion in ocultas),
                composicion.piezas,
            ),
            orden,
            valores,
            None,
        )
    if composicion.por_id(pieza_id) is None:
        return composicion, orden, valores, 'Esa sección no está en la página.'
    piezas = tuple(
        replace(pieza, visible=visible) if pieza.id == pieza_id else pieza
        for pieza in composicion.piezas
    )
    return Composicion(composicion.ocultas, piezas), orden, valores, None


def _quitar(composicion, orden, valores, pieza_id):
    if pieza_id in SECCIONES or pieza_id in ('barra', 'pie'):
        return (
            composicion, orden, valores,
            'Esa sección pertenece a la plantilla. Puedes ocultarla; '
            'la barra y el pie se quedan fijos.',
        )
    if composicion.por_id(pieza_id) is None:
        return composicion, orden, valores, 'Esa sección no está en la página.'
    piezas = tuple(pieza for pieza in composicion.piezas if pieza.id != pieza_id)
    return (
        Composicion(composicion.ocultas, piezas),
        [grupo for grupo in orden if grupo != pieza_id],
        valores,
        None,
    )


def _pieza(item, vistas):
    if not isinstance(item, dict):
        return None
    pieza_id = item.get('id')
    tipo = item.get('tipo')
    if not isinstance(pieza_id, str) or _ID.fullmatch(pieza_id) is None:
        return None
    if tipo not in TIPOS or pieza_id in vistas:
        return None
    return Pieza(
        id=pieza_id,
        tipo=tipo,
        visible=bool(item.get('visible', True)),
        diapositivas=_diapositivas(item, tipo),
        nombre=_nombre_guardado(item.get('nombre')),
        columnas=_columnas_de(item),
        bloques=_bloques(item),
        puestos=_puestos_de_item(item, _columnas_de(item), _bloques(item)),
    )


def _serializar_pieza(pieza):
    datos = {'id': pieza.id, 'tipo': pieza.tipo, 'visible': pieza.visible}
    if pieza.nombre:
        datos['nombre'] = pieza.nombre
    if pieza.tipo == 'carrusel':
        datos['diapositivas'] = list(pieza.diapositivas or ('01',))
    if pieza.columnas != 1:
        datos['columnas'] = pieza.columnas
    puestos = puestos_de(pieza)
    if not _puestos_son_herencia(pieza, puestos):
        datos['puestos'] = [
            {'celda': puesto.celda} if puesto.ref == REF_PROPIA
            else {'ref': puesto.ref, 'celda': puesto.celda}
            for puesto in puestos
        ]
    if pieza.bloques:
        datos['bloques'] = [_serializar_bloque(bloque) for bloque in pieza.bloques]
    return datos


def _serializar_bloque(bloque):
    datos = {'id': bloque.id, 'tipo': bloque.tipo}
    if bloque.tipo == 'carrusel':
        datos['diapositivas'] = list(bloque.diapositivas or ('01',))
    return datos


def _nombre_guardado(valor):
    if not isinstance(valor, str):
        return ''
    return ' '.join(valor.split())[:MAX_NOMBRE].rstrip()


def _diapositivas(item, tipo):
    if tipo != 'carrusel':
        return ()
    brutas = item.get('diapositivas')
    if not isinstance(brutas, list):
        return ('01',)
    vistas = []
    vistos = set()
    for dia in brutas:
        if not isinstance(dia, str) or _DIA.fullmatch(dia) is None or dia in vistos:
            continue
        vistos.add(dia)
        vistas.append(dia)
        if len(vistas) >= MAX_DIAPOSITIVAS:
            break
    return tuple(vistas) or ('01',)


def _claves_imagen(pieza):
    claves = []
    if pieza.tipo == 'imagen':
        claves.append(f'{pieza.id}-foto')
    elif pieza.tipo == 'carrusel':
        claves.extend(f'{pieza.id}-d{dia}' for dia in (pieza.diapositivas or ('01',)))
    for bloque in pieza.bloques:
        prefijo = f'{pieza.id}-{bloque.id}'
        if bloque.tipo == 'imagen':
            claves.append(f'{prefijo}-foto')
        elif bloque.tipo == 'carrusel':
            claves.extend(
                f'{prefijo}-d{dia}' for dia in (bloque.diapositivas or ('01',))
            )
    return tuple(claves)


def _exigir_agregada(composicion, pieza_id):
    if pieza_id in SECCIONES or pieza_id in ('barra', 'pie'):
        return None, (
            'La distribución y las piezas solo aplican a una sección agregada.'
        )
    pieza = composicion.por_id(pieza_id)
    if pieza is None:
        return None, 'Esa sección no está en la página.'
    return pieza, None


def _agregar_interno(composicion, orden, valores, pieza_id, tipo):
    pieza, error = _exigir_agregada(composicion, pieza_id)
    if error:
        return composicion, orden, valores, error
    if tipo not in TIPOS_INTERNOS:
        return composicion, orden, valores, 'Esa pieza no está en el catálogo de la sección.'
    if len(pieza.bloques) >= MAX_BLOQUES:
        return (
            composicion, orden, valores,
            f'Una sección admite como máximo {MAX_BLOQUES} piezas.',
        )
    bloque_id = _nuevo_bloque_id(pieza)
    if bloque_id is None:
        return composicion, orden, valores, 'No se puede agregar otra pieza.'
    diapositivas = ('01',) if tipo == 'carrusel' else ()
    bloque = BloqueInterno(bloque_id, tipo, diapositivas)
    fantasma = Pieza(
        id=f'{pieza.id}-{bloque.id}', tipo=tipo, diapositivas=diapositivas,
    )
    valores = dict(valores)
    valores.update(valores_de_fabrica(fantasma))
    puestos = _agregar_ref(puestos_de(pieza), pieza.columnas, bloque_id)
    nueva = replace(pieza, bloques=pieza.bloques + (bloque,), puestos=puestos)
    return _reemplazar(composicion, nueva), orden, valores, None


def _quitar_interno(composicion, orden, valores, pieza_id, bloque_id):
    pieza, error = _exigir_agregada(composicion, pieza_id)
    if error:
        return composicion, orden, valores, error
    if not any(bloque.id == bloque_id for bloque in pieza.bloques):
        return composicion, orden, valores, 'Esa pieza no está en la sección.'
    nueva = replace(
        pieza,
        bloques=tuple(bloque for bloque in pieza.bloques if bloque.id != bloque_id),
        puestos=tuple(puesto for puesto in puestos_de(pieza) if puesto.ref != bloque_id),
    )
    return _reemplazar(composicion, nueva), orden, valores, None


def _poner_columnas(composicion, orden, valores, pieza_id, bruto):
    pieza, error = _exigir_agregada(composicion, pieza_id)
    if error:
        return composicion, orden, valores, error
    if str(bruto) not in ('1', '2', '3'):
        return composicion, orden, valores, 'La cuadrícula admite 1, 2 o 3 columnas.'
    return (
        _reemplazar(composicion, _pieza_con_columnas(pieza, int(bruto))),
        orden,
        valores,
        None,
    )


def _ubicar_pieza(composicion, orden, valores, pieza_id, token, celda_bruta, indice_bruto):
    """Suelta una pieza en una casilla. El índice es el lugar después de quitarla."""
    pieza, error = _exigir_agregada(composicion, pieza_id)
    if error:
        return composicion, orden, valores, error
    ref = _ref_de_token(token)
    if ref is None or not _ref_conocida(pieza, ref):
        return composicion, orden, valores, 'Esa pieza no está en la sección.'
    if not str(celda_bruta).isdigit() or not str(indice_bruto).isdigit():
        return composicion, orden, valores, 'No se reconoció la casilla.'
    celda = int(celda_bruta)
    indice = int(indice_bruto)
    if celda < 0 or celda >= pieza.columnas:
        return composicion, orden, valores, 'Esa casilla no está en la cuadrícula.'
    grupos = _grupos_de(puestos_de(pieza), pieza.columnas)
    for grupo in grupos:
        if ref in grupo:
            grupo.remove(ref)
    destino = grupos[celda]
    destino.insert(min(indice, len(destino)), ref)
    return (
        _reemplazar(composicion, replace(pieza, puestos=_puestos_desde_grupos(grupos))),
        orden,
        valores,
        None,
    )


def _mutar_dia(composicion, orden, valores, accion):
    verbo, _, resto = accion.partition(':')
    pieza_id, _, cola = resto.partition(':')
    pieza = composicion.por_id(pieza_id)
    if pieza is None:
        return composicion, orden, valores, 'Ese carrusel no está en la página.'
    trozo, dia = _partir_objetivo(cola)
    if trozo:
        return _mutar_dia_interno(composicion, orden, valores, pieza, trozo, verbo, dia)
    if pieza.tipo != 'carrusel':
        return composicion, orden, valores, 'Ese carrusel no está en la página.'
    nuevas, valores, error = _cambiar_diapositivas(
        pieza.diapositivas, verbo, dia, pieza.id, valores,
    )
    if error:
        return composicion, orden, valores, error
    return _reemplazar(composicion, replace(pieza, diapositivas=nuevas)), orden, valores, None


def _mutar_dia_interno(composicion, orden, valores, pieza, trozo, verbo, dia):
    bloque = next((item for item in pieza.bloques if item.id == trozo), None)
    if bloque is None or bloque.tipo != 'carrusel':
        return composicion, orden, valores, 'Ese carrusel no está en la página.'
    nuevas, valores, error = _cambiar_diapositivas(
        bloque.diapositivas, verbo, dia, f'{pieza.id}-{bloque.id}', valores,
    )
    if error:
        return composicion, orden, valores, error
    bloques = tuple(
        replace(item, diapositivas=nuevas) if item.id == bloque.id else item
        for item in pieza.bloques
    )
    return _reemplazar(composicion, replace(pieza, bloques=bloques)), orden, valores, None


def _partir_objetivo(cola):
    """b01 es una pieza interna. 01 es una diapositiva del carrusel de la sección."""
    if not cola:
        return '', ''
    primero, _, segundo = cola.partition(':')
    if _BLOQUE.fullmatch(primero):
        return primero, segundo
    return '', cola


def _cambiar_diapositivas(diapositivas, verbo, dia, prefijo, valores):
    diapositivas = diapositivas or ('01',)
    if verbo == 'dia-agregar':
        if len(diapositivas) >= MAX_DIAPOSITIVAS:
            return diapositivas, valores, (
                f'Un carrusel admite como máximo {MAX_DIAPOSITIVAS} diapositivas.'
            )
        siguiente = max(int(item) for item in diapositivas) + 1
        if siguiente > 99:
            return diapositivas, valores, 'No se puede agregar otra diapositiva.'
        nuevo = f'{siguiente:02d}'
        valores = dict(valores)
        valores[f'{prefijo}-d{nuevo}'] = ('', '')
        valores[f'{prefijo}-r{nuevo}'] = ('', '')
        return diapositivas + (nuevo,), valores, None
    if verbo == 'dia-orden':
        ordenadas = _orden_de_dias(diapositivas, dia)
        if ordenadas is None:
            return diapositivas, valores, (
                'Ese orden no corresponde a las diapositivas del carrusel.'
            )
        return ordenadas, valores, None
    if _DIA.fullmatch(dia or '') is None or dia not in diapositivas:
        return diapositivas, valores, 'Esa diapositiva no está en el carrusel.'
    if verbo == 'dia-quitar':
        if len(diapositivas) <= 1:
            return diapositivas, valores, (
                'El carrusel necesita al menos una diapositiva. Puedes quitar la sección.'
            )
        return tuple(item for item in diapositivas if item != dia), valores, None
    return diapositivas, valores, 'No se reconoció la acción.'


def _orden_de_dias(diapositivas, bruto):
    """Una permutación de las diapositivas que ya existen. No agrega ni quita."""
    partes = [item for item in str(bruto or '').split(',') if item]
    if len(partes) != len(diapositivas):
        return None
    if any(_DIA.fullmatch(item) is None for item in partes):
        return None
    if set(partes) != set(diapositivas) or len(set(partes)) != len(partes):
        return None
    return tuple(partes)


def puestos_de(pieza):
    """Casillas ya guardadas, o el reparto heredado de un borrador sin puestos."""
    if pieza.puestos:
        return _normalizar_puestos(pieza.puestos, pieza.columnas, pieza.bloques)
    return _puestos_heredados(pieza.bloques, pieza.columnas)


def casillas_de(pieza):
    """Refs por columna, en el orden de lectura. '' es el contenido propio."""
    return _grupos_de(puestos_de(pieza), pieza.columnas)


def _columnas_de(item):
    """1, 2 o 3. Acepta la cuadrícula nueva y el diseño fijo de un borrador viejo."""
    bruto = item.get('columnas')
    if bruto in (1, 2, 3):
        return bruto
    if isinstance(bruto, str) and bruto in ('1', '2', '3'):
        return int(bruto)
    diseno = item.get('diseno')
    if isinstance(diseno, str) and diseno in _COLUMNAS_DE_DISENO:
        return _COLUMNAS_DE_DISENO[diseno]
    return 1


def _puestos_de_item(item, columnas, bloques):
    brutos = item.get('puestos')
    if isinstance(brutos, list):
        puestos = []
        for bruto in brutos:
            puesto = _puesto_bruto(bruto, columnas)
            if puesto is not None:
                puestos.append(puesto)
        return _normalizar_puestos(tuple(puestos), columnas, bloques)
    return _puestos_heredados(bloques, columnas)


def _puesto_bruto(bruto, columnas):
    if not isinstance(bruto, dict):
        return None
    celda = bruto.get('celda', 0)
    if isinstance(celda, str) and celda.isdigit():
        celda = int(celda)
    if not isinstance(celda, int) or isinstance(celda, bool):
        return None
    if celda < 0 or celda >= columnas:
        celda = 0
    ref = bruto.get('ref', REF_PROPIA)
    if ref in ('', TOKEN_PROPIA, None):
        return Puesto(REF_PROPIA, celda)
    if isinstance(ref, str) and _BLOQUE.fullmatch(ref):
        return Puesto(ref, celda)
    return None


def _puestos_heredados(bloques, columnas):
    """Reparte en orden: la propia, luego cada bloque. Así un diseño viejo no se pierde."""
    refs = [REF_PROPIA] + [bloque.id for bloque in bloques]
    return tuple(Puesto(ref, indice % columnas) for indice, ref in enumerate(refs))


def _normalizar_puestos(puestos, columnas, bloques):
    grupos = _grupos_de(puestos, columnas)
    vistos = set()
    for grupo in grupos:
        limpio = []
        for ref in grupo:
            if ref in vistos:
                continue
            if ref != REF_PROPIA and not any(bloque.id == ref for bloque in bloques):
                continue
            vistos.add(ref)
            limpio.append(ref)
        grupo[:] = limpio
    if REF_PROPIA not in vistos:
        grupos[0].insert(0, REF_PROPIA)
        vistos.add(REF_PROPIA)
    for bloque in bloques:
        if bloque.id not in vistos:
            grupos[0].append(bloque.id)
    return _puestos_desde_grupos(grupos)


def _puestos_son_herencia(pieza, puestos):
    return puestos == _puestos_heredados(pieza.bloques, pieza.columnas)


def _pieza_con_columnas(pieza, columnas):
    if columnas == pieza.columnas:
        return pieza
    plano = _orden_lectura(puestos_de(pieza), pieza.columnas)
    grupos = [[] for _ in range(columnas)]
    for indice, ref in enumerate(plano):
        grupos[indice % columnas].append(ref)
    return replace(pieza, columnas=columnas, puestos=_puestos_desde_grupos(grupos))


def _agregar_ref(puestos, columnas, ref):
    grupos = _grupos_de(puestos, columnas)
    grupos[0].append(ref)
    return _puestos_desde_grupos(grupos)


def _orden_lectura(puestos, columnas):
    """Fila a fila, de izquierda a derecha, para no dejar el orden viejo al repartir."""
    grupos = _grupos_de(puestos, columnas)
    plano = []
    fila = 0
    while True:
        alguno = False
        for grupo in grupos:
            if fila < len(grupo):
                plano.append(grupo[fila])
                alguno = True
        if not alguno:
            return plano
        fila += 1


def _grupos_de(puestos, columnas):
    grupos = [[] for _ in range(max(columnas, 1))]
    for puesto in puestos:
        celda = puesto.celda if 0 <= puesto.celda < columnas else 0
        grupos[celda].append(puesto.ref)
    return grupos


def _puestos_desde_grupos(grupos):
    return tuple(
        Puesto(ref, celda)
        for celda, grupo in enumerate(grupos)
        for ref in grupo
    )


def _ref_de_token(token):
    if token == TOKEN_PROPIA:
        return REF_PROPIA
    if isinstance(token, str) and _BLOQUE.fullmatch(token):
        return token
    return None


def _ref_conocida(pieza, ref):
    if ref == REF_PROPIA:
        return True
    return any(bloque.id == ref for bloque in pieza.bloques)


def _bloques(item):
    brutos = item.get('bloques') or []
    if not isinstance(brutos, list):
        return ()
    vistos = set()
    bloques = []
    for bruto in brutos:
        bloque = _bloque_interno(bruto, vistos)
        if bloque is None:
            continue
        vistos.add(bloque.id)
        bloques.append(bloque)
        if len(bloques) >= MAX_BLOQUES:
            break
    return tuple(bloques)


def _bloque_interno(item, vistos):
    if not isinstance(item, dict):
        return None
    bloque_id = item.get('id')
    tipo = item.get('tipo')
    if not isinstance(bloque_id, str) or _BLOQUE.fullmatch(bloque_id) is None:
        return None
    if tipo not in TIPOS_INTERNOS or bloque_id in vistos:
        return None
    return BloqueInterno(
        bloque_id,
        tipo,
        _diapositivas(item, tipo) if tipo == 'carrusel' else (),
    )


def _nuevo_bloque_id(pieza):
    usados = set()
    for bloque in pieza.bloques:
        if _BLOQUE.fullmatch(bloque.id):
            usados.add(int(bloque.id[1:]))
    for numero in range(1, 100):
        if numero not in usados:
            return f'b{numero:02d}'
    return None


def _reemplazar(composicion, nueva):
    piezas = tuple(nueva if pieza.id == nueva.id else pieza for pieza in composicion.piezas)
    return Composicion(composicion.ocultas, piezas)


def _nuevo_id(composicion):
    ocupados = {pieza.id for pieza in composicion.piezas}
    for _intento in range(8):
        candidato = PREFIJO_ID + uuid.uuid4().hex[:8]
        if candidato not in ocupados:
            return candidato
    raise RuntimeError('No se pudo crear un identificador de sección.')
