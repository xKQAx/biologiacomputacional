"""Cuadrícula libre de una sección agregada, por dispositivo.

La fuente clásica sigue siendo `columnas` + `puestos` (piezas apiladas en
columnas). Aquí solo vive lo que el administrador personalizó: escritorio,
tablet y móvil no se copian entre sí. Si un dispositivo no tiene entrada,
se usa el diseño predeterminado derivado de esas columnas.

Punto de extensión para deshacer: `poner` y `quitar` reciben la tupla
anterior y devuelven otra. Una pila puede guardar ese par (dispositivo,
Rejilla) y volver a aplicarlo. El editor no tiene historial por operación;
las publicaciones siguen en `paginas.historial`.
"""

import re

DISPOSITIVOS = ('escritorio', 'tablet', 'movil')
MAX_COLUMNAS = 4
MAX_FILAS = 6
MAX_EXTENSION = 4
HUECO_MAX = 64
# Mismos tokens que piezas.REF_PROPIA y piezas.TOKEN_PROPIA. No se importa
# piezas para no crear un ciclo.
REF_PROPIA = ''
TOKEN_PROPIA = 'propia'
_REF = re.compile(r'^b[0-9]{2}$')
_ANCLA = re.compile(r'^pz[0-9a-f]{8}$')

# Código, columnas, filas. El orden es el de las miniaturas.
PRESETS = (
    ('1x1', 1, 1),
    ('2x1', 2, 1),
    ('3x1', 3, 1),
    ('4x1', 4, 1),
    ('1x2', 1, 2),
    ('2x2', 2, 2),
    ('3x2', 3, 2),
    ('4x2', 4, 2),
    ('1x3', 1, 3),
    ('2x3', 2, 3),
    ('3x3', 3, 3),
)

_MEDIOS = {
    'escritorio': '@media (min-width:992px)',
    'tablet': '@media (min-width:768px) and (max-width:991.98px)',
    'movil': '@media (max-width:767.98px)',
}


class Posicion:
    """Dónde se sienta una pieza. `filas` y `columnas` son el span, no el índice."""

    __slots__ = ('ref', 'fila', 'columna', 'filas', 'columnas')

    def __init__(self, ref, fila, columna, filas=1, columnas=1):
        self.ref = ref
        self.fila = int(fila)
        self.columna = int(columna)
        self.filas = int(filas)
        self.columnas = int(columnas)

    def __eq__(self, otro):
        return (
            isinstance(otro, Posicion)
            and (self.ref, self.fila, self.columna, self.filas, self.columnas)
            == (otro.ref, otro.fila, otro.columna, otro.filas, otro.columnas)
        )

    def __hash__(self):
        return hash((self.ref, self.fila, self.columna, self.filas, self.columnas))

    def __repr__(self):
        return (
            f'Posicion({self.ref!r}, {self.fila}, {self.columna}, '
            f'{self.filas}, {self.columnas})'
        )


class Rejilla:
    """Grid de un dispositivo. Inmutable de hecho: las operaciones devuelven otra."""

    __slots__ = (
        'columnas', 'filas', 'hueco_columna', 'hueco_fila', 'anchos', 'altos', 'posiciones',
    )

    def __init__(
        self, columnas, filas, hueco_columna=32, hueco_fila=24,
        anchos=(), altos=(), posiciones=(),
    ):
        self.columnas = int(columnas)
        self.filas = int(filas)
        self.hueco_columna = int(hueco_columna)
        self.hueco_fila = int(hueco_fila)
        self.anchos = tuple(anchos)
        self.altos = tuple(altos)
        self.posiciones = tuple(posiciones)

    def __eq__(self, otro):
        if not isinstance(otro, Rejilla):
            return False
        return (
            self.columnas == otro.columnas
            and self.filas == otro.filas
            and self.hueco_columna == otro.hueco_columna
            and self.hueco_fila == otro.hueco_fila
            and self.anchos == otro.anchos
            and self.altos == otro.altos
            and self.posiciones == otro.posiciones
        )


def celdas(posicion):
    """Celdas 1-based que ocupa una pieza, de ancla a ancla+span."""
    return {
        (fila, columna)
        for fila in range(posicion.fila, posicion.fila + posicion.filas)
        for columna in range(posicion.columna, posicion.columna + posicion.columnas)
    }


def preset(codigo):
    for item in PRESETS:
        if item[0] == codigo:
            return item
    return None


def catalogo_miniaturas():
    """Datos de las miniaturas. `celdas` existe para pintar la cuadrícula en la plantilla."""
    return tuple(
        {
            'codigo': codigo,
            'columnas': columnas,
            'filas': filas,
            'celdas': tuple(range(columnas * filas)),
        }
        for codigo, columnas, filas in PRESETS
    )


def derivar_columnas(grupos):
    """Diseño predeterminado de escritorio y tablet: una fila por pieza apilada."""
    grupos = tuple(tuple(grupo) for grupo in (grupos or (('',),)))
    if not grupos:
        grupos = (('',),)
    columnas = len(grupos)
    posiciones = []
    filas = 1
    for columna, refs in enumerate(grupos, start=1):
        for fila, ref in enumerate(refs, start=1):
            filas = max(filas, fila)
            posiciones.append(Posicion(ref, fila, columna, 1, 1))
    if not posiciones:
        posiciones.append(Posicion(REF_PROPIA, 1, 1, 1, 1))
        filas = 1
    if filas > MAX_FILAS:
        return aplicar_preset(
            [pos.ref for pos in _ordenadas(posiciones)], columnas, MAX_FILAS,
        )
    return _cerrar(
        columnas, filas, 32, 24,
        tuple(1 for _ in range(columnas)),
        tuple(0 for _ in range(filas)),
        posiciones,
    )


def derivar_movil(grupos):
    """En ventana estrecha el diseño clásico apila la columna entera y luego la siguiente."""
    grupos = tuple(tuple(grupo) for grupo in (grupos or (('',),)))
    refs = [ref for grupo in grupos for ref in grupo]
    if not refs:
        refs = [REF_PROPIA]
    if len(refs) > MAX_FILAS:
        return aplicar_preset(refs, 1, MAX_FILAS)
    return _cerrar(
        1, len(refs), 16, 16, (1,),
        tuple(0 for _ in refs),
        [Posicion(ref, indice, 1, 1, 1) for indice, ref in enumerate(refs, start=1)],
    )


def resolver(grupos, explicitas):
    """Tres rejillas. La explícita gana; si no hay, el predeterminado de ese dispositivo."""
    explicitas = explicitas or {}
    base = derivar_columnas(grupos)
    return {
        'escritorio': explicitas.get('escritorio') or base,
        'tablet': explicitas.get('tablet') or base,
        'movil': explicitas.get('movil') or derivar_movil(grupos),
    }


def poner(pares, dispositivo, rejilla):
    """Guarda la rejilla de un dispositivo y deja iguales los demás."""
    if dispositivo not in DISPOSITIVOS:
        return tuple(pares)
    mapa = dict(pares)
    mapa[dispositivo] = rejilla
    return tuple((nombre, mapa[nombre]) for nombre in DISPOSITIVOS if nombre in mapa)


def quitar(pares, dispositivo):
    return tuple(par for par in pares if par[0] != dispositivo)


def aplicar_preset(refs, columnas, filas, base=None):
    """Reubica todas las refs en celdas libres, de izquierda a derecha y de arriba abajo.

    Si no caben, crecen las filas y después las columnas. Nadie queda fuera.
    El span vuelve a 1: la cuadrícula cambió de tamaño.
    """
    columnas = _acotar(columnas, 1, MAX_COLUMNAS)
    filas = _acotar(filas, 1, MAX_FILAS)
    refs = tuple(refs)
    while columnas * filas < len(refs) and filas < MAX_FILAS:
        filas += 1
    while columnas * filas < len(refs) and columnas < MAX_COLUMNAS:
        columnas += 1
    posiciones = []
    for indice, ref in enumerate(refs):
        if indice >= columnas * filas:
            break
        posiciones.append(Posicion(
            ref, indice // columnas + 1, indice % columnas + 1, 1, 1,
        ))
    hueco_columna = base.hueco_columna if base is not None else 32
    hueco_fila = base.hueco_fila if base is not None else 24
    return _cerrar(
        columnas, filas, hueco_columna, hueco_fila,
        _tramos(base.anchos if base is not None else (), columnas, 1),
        _tramos(base.altos if base is not None else (), filas, 0),
        posiciones,
    )


def con_medida(rejilla, columnas, filas, hueco_columna, hueco_fila, anchos, altos):
    """Cambia tamaño, huecos y proporciones. Si el tamaño cambia, reubica sin solapes."""
    columnas = _acotar(columnas, 1, MAX_COLUMNAS)
    filas = _acotar(filas, 1, MAX_FILAS)
    hueco_columna = _acotar(hueco_columna, 0, HUECO_MAX)
    hueco_fila = _acotar(hueco_fila, 0, HUECO_MAX)
    anchos = _tramos(anchos, columnas, 1)
    altos = _tramos(altos, filas, 0)
    if columnas == rejilla.columnas and filas == rejilla.filas:
        return _cerrar(
            columnas, filas, hueco_columna, hueco_fila, anchos, altos, rejilla.posiciones,
        ), None
    return aplicar_preset(orden_lectura(rejilla), columnas, filas, Rejilla(
        columnas, filas, hueco_columna, hueco_fila, anchos, altos, (),
    )), None


def con_span(rejilla, ref, filas, columnas):
    actual = _de(rejilla, ref)
    if actual is None:
        return rejilla, 'Esa pieza no está en la cuadrícula.'
    filas = _acotar(filas, 1, MAX_EXTENSION)
    columnas = _acotar(columnas, 1, MAX_EXTENSION)
    nueva = Posicion(actual.ref, actual.fila, actual.columna, filas, columnas)
    otras = [pos for pos in rejilla.posiciones if pos.ref != ref]
    if not _cabe(nueva, rejilla.columnas, rejilla.filas, otras):
        return rejilla, 'Esa pieza no cabe ahí sin salirse o solaparse.'
    return _cerrar(
        rejilla.columnas, rejilla.filas, rejilla.hueco_columna, rejilla.hueco_fila,
        rejilla.anchos, rejilla.altos, otras + [nueva],
    ), None


def soltar(rejilla, ref, fila, columna):
    """Mueve a una celda vacía o intercambia anclas si la celda está ocupada.

    Cada pieza conserva su span. Si el resultado no cabe, la rejilla no cambia.
    """
    actual = _de(rejilla, ref)
    if actual is None:
        return rejilla, 'Esa pieza no está en la cuadrícula.'
    if fila < 1 or columna < 1 or fila > rejilla.filas or columna > rejilla.columnas:
        return rejilla, 'Esa celda no está en la cuadrícula.'
    ocupante = ocupante_en(rejilla, fila, columna)
    if ocupante is None or ocupante.ref == ref:
        nueva = Posicion(actual.ref, fila, columna, actual.filas, actual.columnas)
        otras = [pos for pos in rejilla.posiciones if pos.ref != ref]
        if not _cabe(nueva, rejilla.columnas, rejilla.filas, otras):
            return rejilla, 'No cabe en esa celda sin solaparse.'
        return _misma_medida(rejilla, otras + [nueva]), None
    movida = Posicion(actual.ref, ocupante.fila, ocupante.columna, actual.filas, actual.columnas)
    otra = Posicion(ocupante.ref, actual.fila, actual.columna, ocupante.filas, ocupante.columnas)
    resto = [pos for pos in rejilla.posiciones if pos.ref not in (ref, ocupante.ref)]
    if not _cabe(movida, rejilla.columnas, rejilla.filas, resto + [otra]):
        return rejilla, 'No se pueden intercambiar: no caben sin solaparse.'
    if not _cabe(otra, rejilla.columnas, rejilla.filas, resto + [movida]):
        return rejilla, 'No se pueden intercambiar: no caben sin solaparse.'
    return _misma_medida(rejilla, resto + [movida, otra]), None


def incorporar(rejilla, ref):
    """Primera celda libre. Si no hay, crece una fila y, en el tope, reubica."""
    if _de(rejilla, ref) is not None:
        return rejilla
    for fila in range(1, rejilla.filas + 1):
        for columna in range(1, rejilla.columnas + 1):
            if ocupante_en(rejilla, fila, columna) is None:
                return _misma_medida(
                    rejilla, list(rejilla.posiciones) + [Posicion(ref, fila, columna, 1, 1)],
                )
    if rejilla.filas < MAX_FILAS:
        crecida = _cerrar(
            rejilla.columnas, rejilla.filas + 1, rejilla.hueco_columna, rejilla.hueco_fila,
            rejilla.anchos, rejilla.altos + (0,), rejilla.posiciones,
        )
        return _misma_medida(
            crecida, list(crecida.posiciones) + [Posicion(ref, crecida.filas, 1, 1, 1)],
        )
    return aplicar_preset(orden_lectura(rejilla) + (ref,), rejilla.columnas, rejilla.filas, rejilla)


def retirar(rejilla, ref):
    return _misma_medida(rejilla, [pos for pos in rejilla.posiciones if pos.ref != ref])


def ocupante_en(rejilla, fila, columna):
    for posicion in rejilla.posiciones:
        if (fila, columna) in celdas(posicion):
            return posicion
    return None


def orden_lectura(rejilla):
    return tuple(
        pos.ref for pos in sorted(rejilla.posiciones, key=lambda pos: (pos.fila, pos.columna, pos.ref))
    )


def coincide_preset(rejilla, columnas, filas):
    """La miniatura está activa si el tamaño y las celdas coinciden con ese preset."""
    if rejilla.columnas != columnas or rejilla.filas != filas:
        return False
    if any(pos.filas != 1 or pos.columnas != 1 for pos in rejilla.posiciones):
        return False
    esperada = aplicar_preset(orden_lectura(rejilla), columnas, filas, rejilla)
    return esperada.posiciones == _ordenadas(rejilla.posiciones)


def normalizar(rejilla, refs):
    """Descarta refs desconocidas y solapes. Las que faltan entran en celdas libres."""
    validas = []
    vistos = set()
    ocupadas = set()
    for posicion in rejilla.posiciones:
        if posicion.ref not in refs or posicion.ref in vistos:
            continue
        if not _cabe_celdas(posicion, rejilla.columnas, rejilla.filas, ocupadas):
            continue
        ocupadas |= celdas(posicion)
        vistos.add(posicion.ref)
        validas.append(posicion)
    actual = _misma_medida(rejilla, validas)
    for ref in refs:
        if ref not in vistos:
            actual = incorporar(actual, ref)
            vistos.add(ref)
    return actual


def serializar_rejilla(rejilla):
    return {
        'columnas': rejilla.columnas,
        'filas': rejilla.filas,
        'huecoColumna': rejilla.hueco_columna,
        'huecoFila': rejilla.hueco_fila,
        'anchos': list(rejilla.anchos),
        'altos': list(rejilla.altos),
        'posiciones': [
            {
                'id': TOKEN_PROPIA if pos.ref == REF_PROPIA else pos.ref,
                'fila': pos.fila,
                'columna': pos.columna,
                'filas': pos.filas,
                'columnas': pos.columnas,
            }
            for pos in _ordenadas(rejilla.posiciones)
        ],
    }


def parsear_rejilla(datos, refs):
    """None si el bloque no es una rejilla. Si lo es, se normaliza contra las refs vivas."""
    if not isinstance(datos, dict):
        return None
    columnas = _entero(datos.get('columnas'), 1, MAX_COLUMNAS)
    filas = _entero(datos.get('filas'), 1, MAX_FILAS)
    if columnas is None or filas is None:
        return None
    hueco_columna = _entero(datos.get('huecoColumna', 32), 0, HUECO_MAX)
    hueco_fila = _entero(datos.get('huecoFila', 24), 0, HUECO_MAX)
    if hueco_columna is None or hueco_fila is None:
        return None
    anchos = _lista_tramos(datos.get('anchos'), columnas, 1)
    altos = _lista_tramos(datos.get('altos'), filas, 0)
    posiciones = []
    for bruto in datos.get('posiciones') or []:
        posicion = _posicion_bruta(bruto)
        if posicion is not None:
            posiciones.append(posicion)
    return normalizar(_cerrar(
        columnas, filas, hueco_columna, hueco_fila, anchos, altos, posiciones,
    ), refs)


def parsear_distribucion(datos, refs):
    if not isinstance(datos, dict):
        return ()
    pares = []
    for dispositivo in DISPOSITIVOS:
        if dispositivo not in datos:
            continue
        rejilla = parsear_rejilla(datos.get(dispositivo), refs)
        if rejilla is not None:
            pares.append((dispositivo, rejilla))
    return tuple(pares)


def serializar_distribucion(pares):
    return {
        dispositivo: serializar_rejilla(rejilla)
        for dispositivo, rejilla in pares
        if dispositivo in DISPOSITIVOS
    }


def css_de(ancla, resueltas, *, editor=False):
    """CSS de la cuadrícula. Sin selectores de guías ni de controles.

    La página pública solo lleva media queries. Con `editor`, el lienzo suma
    `html[data-dispositivo]` para forzar el dispositivo del botón, no el ancho.
    """
    if _ANCLA.fullmatch(ancla or '') is None:
        return ''
    sel = f'#mosaico-{ancla}'
    bloques = [f'{sel}{{display:grid;align-items:start;}}']
    for dispositivo in DISPOSITIVOS:
        rejilla = resueltas.get(dispositivo)
        if rejilla is None:
            continue
        reglas = _reglas(sel, rejilla)
        bloques.append(f'{_MEDIOS[dispositivo]}{{{"".join(reglas)}}}')
        if editor:
            prefijo = f'html[data-dispositivo="{dispositivo}"] '
            bloques.append(''.join(prefijo + regla for regla in reglas))
    return ''.join(bloques)


def celdas_guia(rejilla):
    """Una caja por pieza (con su span) y una por celda libre.

    La caja ocupada es el ancla: el elemento vive ahí. Las celdas que el span
    ya cubre no se repiten, para que la guía y la pieza sean la misma área.
    """
    resultado = []
    for posicion in _ordenadas(rejilla.posiciones):
        resultado.append({
            'fila': posicion.fila,
            'columna': posicion.columna,
            'filas': posicion.filas,
            'columnas': posicion.columnas,
            'ocupada': True,
            'token': _token(posicion.ref),
        })
    for fila in range(1, rejilla.filas + 1):
        for columna in range(1, rejilla.columnas + 1):
            if ocupante_en(rejilla, fila, columna) is not None:
                continue
            resultado.append({
                'fila': fila,
                'columna': columna,
                'filas': 1,
                'columnas': 1,
                'ocupada': False,
                'token': '',
            })
    return tuple(resultado)


def mapa_publico(resueltas):
    """Lo que el lienzo lee para validar el arrastre del dispositivo activo."""
    return {
        dispositivo: serializar_rejilla(rejilla)
        for dispositivo, rejilla in resueltas.items()
    }


def _reglas(sel, rejilla):
    columnas = ' '.join(f'minmax(0,{peso}fr)' for peso in rejilla.anchos)
    filas = ' '.join('auto' if peso <= 0 else f'minmax(0,{peso}fr)' for peso in rejilla.altos)
    reglas = [
        (
            f'{sel}{{grid-template-columns:{columnas};grid-template-rows:{filas};'
            f'column-gap:{rejilla.hueco_columna}px;row-gap:{rejilla.hueco_fila}px;}}'
        ),
    ]
    for posicion in rejilla.posiciones:
        token = _token(posicion.ref)
        if not token:
            continue
        reglas.append(
            f'{sel}>.pieza-mosaico-item[data-ref="{token}"]'
            f'{{grid-column:{posicion.columna} / span {posicion.columnas};'
            f'grid-row:{posicion.fila} / span {posicion.filas};}}'
        )
    return reglas


def _token(ref):
    if ref == REF_PROPIA:
        return TOKEN_PROPIA
    if isinstance(ref, str) and _REF.fullmatch(ref):
        return ref
    return ''


def _posicion_bruta(bruto):
    if not isinstance(bruto, dict):
        return None
    ref = bruto.get('id', TOKEN_PROPIA)
    if ref in ('', TOKEN_PROPIA, None):
        ref = REF_PROPIA
    elif not isinstance(ref, str) or _REF.fullmatch(ref) is None:
        return None
    fila = _entero(bruto.get('fila'), 1, MAX_FILAS + MAX_EXTENSION)
    columna = _entero(bruto.get('columna'), 1, MAX_COLUMNAS + MAX_EXTENSION)
    filas = _entero(bruto.get('filas', 1), 1, MAX_EXTENSION)
    columnas = _entero(bruto.get('columnas', 1), 1, MAX_EXTENSION)
    if None in (fila, columna, filas, columnas):
        return None
    return Posicion(ref, fila, columna, filas, columnas)


def _lista_tramos(brutos, cantidad, minimo):
    if not isinstance(brutos, list):
        return tuple(minimo for _ in range(cantidad))
    pesos = []
    for bruto in brutos[:cantidad]:
        peso = _entero(bruto, minimo, 4)
        pesos.append(minimo if peso is None else peso)
    return _tramos(pesos, cantidad, minimo)


def _cerrar(columnas, filas, hueco_columna, hueco_fila, anchos, altos, posiciones):
    return Rejilla(
        _acotar(columnas, 1, MAX_COLUMNAS),
        _acotar(filas, 1, MAX_FILAS),
        _acotar(hueco_columna, 0, HUECO_MAX),
        _acotar(hueco_fila, 0, HUECO_MAX),
        _tramos(anchos, columnas, 1),
        _tramos(altos, filas, 0),
        _ordenadas(posiciones),
    )


def _misma_medida(rejilla, posiciones):
    return _cerrar(
        rejilla.columnas, rejilla.filas, rejilla.hueco_columna, rejilla.hueco_fila,
        rejilla.anchos, rejilla.altos, posiciones,
    )


def _ordenadas(posiciones):
    return tuple(sorted(posiciones, key=lambda pos: (pos.fila, pos.columna, pos.ref)))


def _de(rejilla, ref):
    for posicion in rejilla.posiciones:
        if posicion.ref == ref:
            return posicion
    return None


def _cabe(posicion, columnas, filas, otras):
    ocupadas = set()
    for otra in otras:
        ocupadas |= celdas(otra)
    return _cabe_celdas(posicion, columnas, filas, ocupadas)


def _cabe_celdas(posicion, columnas, filas, ocupadas):
    if posicion.fila < 1 or posicion.columna < 1:
        return False
    if posicion.fila + posicion.filas - 1 > filas:
        return False
    if posicion.columna + posicion.columnas - 1 > columnas:
        return False
    return celdas(posicion).isdisjoint(ocupadas)


def _tramos(pesos, cantidad, minimo):
    cantidad = _acotar(cantidad, 1, MAX_FILAS if minimo == 0 else MAX_COLUMNAS)
    salida = []
    for peso in tuple(pesos)[:cantidad]:
        salida.append(_acotar(peso, minimo, 4))
    while len(salida) < cantidad:
        salida.append(minimo if minimo == 0 else 1)
    return tuple(salida)


def _acotar(valor, minimo, maximo):
    """Recorta al rango. Un valor ilegible cae en el mínimo, no se inventa otro eje."""
    if isinstance(valor, bool):
        return minimo
    if isinstance(valor, str) and valor.isdigit():
        valor = int(valor)
    if not isinstance(valor, int):
        return minimo
    return minimo if valor < minimo else maximo if valor > maximo else valor


def _entero(valor, minimo, maximo):
    if isinstance(valor, bool) or isinstance(valor, float):
        return None
    if isinstance(valor, str) and valor.isdigit():
        valor = int(valor)
    if not isinstance(valor, int):
        return None
    if valor < minimo or valor > maximo:
        return None
    return valor
