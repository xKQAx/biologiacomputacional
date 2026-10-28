"""Páginas públicas que reutilizan el editor de inicio.

Cada entrada describe textos que la plantilla ya pinta. No crea secciones nuevas.
La barra y el pie solo se editan en la portada.
"""

from django.urls import reverse

from paginas.catalogo import (
    CATALOGO,
    COMUN,
    GRUPOS,
    PLANTILLA_SECCION,
    SECCIONES,
)
from paginas.catalogos import (
    CATALOGO_BASES,
    CATALOGO_CONTACTO,
    CATALOGO_INVESTIGACION,
    CATALOGO_PROFESIONALES,
    CATALOGO_SERVICIOS,
)

INICIO = 'inicio'

_AYUDA = (
    'Pasa el cursor por el lienzo: lo que se puede editar se resalta. '
    'Haz clic para ver aquí su nombre y cambiar el texto al momento.'
)
_AYUDA_FORMATO = (
    ' En el texto que se lee, la barra admite negrita, cursiva, subrayado y enlace. '
    'En un párrafo o una introducción, también lista con viñetas y lista numerada.'
)
_AYUDA_TEXTO = _AYUDA + _AYUDA_FORMATO
_AYUDA_FOTO = (
    _AYUDA + ' En una foto puedes subir otra imagen y escribir su texto alternativo.'
    + _AYUDA_FORMATO
)
_AYUDA_INICIO = (
    _AYUDA_FOTO + ' Sube o baja las secciones; la barra y el pie se quedan en su sitio.'
)
_AVISO_GUARDADO = 'Borrador guardado. La página pública no cambió.'
_AVISO_DESCARTADO = 'Borrador descartado. Lo publicado sigue igual.'
_ESTADO_BORRADOR = 'Hay un borrador. La página pública sigue mostrando lo publicado.'
_ESTADO_LIMPIO = 'No hay borrador. El lienzo parte de lo que ve el visitante.'


class Pagina:
    """Catálogo, plantilla y textos de una página que ya existe en el sitio."""

    def __init__(
        self, slug, titulo, nombre, nota, plantilla, grupos, catalogo, *,
        secciones=(), plantillas=None, datos=None, ayuda=_AYUDA,
        aviso_guardado=_AVISO_GUARDADO, aviso_publicado, aviso_descartado=_AVISO_DESCARTADO,
        estado_borrador=_ESTADO_BORRADOR, estado_limpio=_ESTADO_LIMPIO,
        enlace_relacionado=None,
    ):
        self.slug = slug
        self.titulo = titulo
        self.nombre = nombre
        self.nota = nota
        self.plantilla = plantilla
        self.grupos = tuple(grupos)
        self.catalogo = tuple(catalogo)
        self.secciones = tuple(secciones)
        self.plantillas = dict(plantillas or {})
        self.datos = datos
        self.ayuda = ayuda
        self.aviso_guardado = aviso_guardado
        self.aviso_publicado = aviso_publicado
        self.aviso_descartado = aviso_descartado
        self.estado_borrador = estado_borrador
        self.estado_limpio = estado_limpio
        self.enlace_relacionado = enlace_relacionado
        self.nombres = dict(self.grupos)
        self.por_clave = {item.clave: item for item in self.catalogo}
        if len(self.por_clave) != len(self.catalogo):
            raise RuntimeError(f'Hay claves repetidas en {slug}.')
        self.claves_por_grupo = {}
        self.indice_en_grupo = {}
        for definicion in self.catalogo:
            if definicion.grupo not in self.nombres:
                raise RuntimeError(f'Grupo desconocido en {definicion.clave}.')
            lista = self.claves_por_grupo.setdefault(definicion.grupo, [])
            self.indice_en_grupo[definicion.clave] = len(lista)
            lista.append(definicion.clave)
        for grupo_id, _nombre in self.grupos:
            if grupo_id not in self.claves_por_grupo:
                raise RuntimeError(f'{slug} tiene la parte {grupo_id} sin textos.')
        self.secciones_set = frozenset(self.secciones)
        if self.secciones:
            if set(self.plantillas) != self.secciones_set:
                raise RuntimeError(f'Cada sección ordenable de {slug} necesita su plantilla.')
            if 'barra' not in self.nombres or 'pie' not in self.nombres:
                raise RuntimeError(f'{slug} reordena secciones y necesita barra y pie.')
            for seccion in self.secciones:
                if seccion not in self.nombres:
                    raise RuntimeError(f'Sección desconocida en {slug}: {seccion}.')
        elif self.plantillas:
            raise RuntimeError(f'{slug} no reordena secciones.')
        self.hay_vistas = any(item.vista != COMUN for item in self.catalogo)

    def url_editor(self):
        if self.slug == INICIO:
            return reverse('admin:pagina_inicio')
        return reverse('admin:pagina_editor', kwargs={'pagina': self.slug})

    def url_lienzo(self):
        if self.slug == INICIO:
            return reverse('admin:pagina_inicio_lienzo')
        return reverse('admin:pagina_lienzo', kwargs={'pagina': self.slug})


def _datos_investigacion(request):
    from investigacion.views import contexto_pagina
    return contexto_pagina(request)


def _datos_profesionales(request):
    from profesionales.views import contexto_pagina
    return contexto_pagina(request)


def _datos_servicios(request):
    from servicios.views import contexto_herramientas
    return contexto_herramientas(request)


def _datos_bases(request):
    from servicios.views import contexto_bases
    return contexto_bases(request)


def _aviso(nombre):
    return f'{nombre} publicada. Los visitantes ya ven estos cambios.'


INDICES = {}
_USADAS = set()
ORDEN = (
    INICIO,
    'investigacion',
    'profesionales',
    'servicios',
    'bases-de-datos',
    'contacto',
)


def _registrar(pagina):
    if pagina.slug in INDICES:
        raise RuntimeError(f'Página repetida: {pagina.slug}.')
    cruce = _USADAS & set(pagina.por_clave)
    if cruce:
        raise RuntimeError(f'Claves repetidas entre páginas: {sorted(cruce)}.')
    _USADAS.update(pagina.por_clave)
    INDICES[pagina.slug] = pagina


_registrar(Pagina(
    INICIO,
    'Editar página de inicio',
    'Página de inicio',
    'Portada del sitio, con el editor en vivo.',
    'inicio.html',
    GRUPOS,
    CATALOGO,
    secciones=SECCIONES,
    plantillas=PLANTILLA_SECCION,
    ayuda=_AYUDA_INICIO,
    aviso_guardado='Borrador guardado. La portada pública no cambió.',
    aviso_publicado='Página de inicio publicada. Los visitantes ya ven estos cambios.',
    aviso_descartado='Borrador descartado. La portada publicada sigue igual.',
    estado_borrador='Hay un borrador. La portada pública sigue mostrando lo publicado.',
))

_registrar(Pagina(
    'investigacion',
    'Editar página de investigación',
    'Investigación',
    'Títulos, introducciones e imágenes. El carrusel se edita aparte.',
    'investigacion/investigacion.html',
    (
        ('introduccion', 'Introducción'),
        ('contenidos', 'Contenidos virtuales'),
    ),
    CATALOGO_INVESTIGACION,
    datos=_datos_investigacion,
    ayuda=_AYUDA_FOTO,
    aviso_publicado=_aviso('Página de investigación'),
    enlace_relacionado={
        'nombre': 'investigacion_editar_carrusel',
        'texto': 'Editar carrusel',
        'nota': 'El carrusel tiene su propio borrador y se publica en su pantalla.',
    },
))

_registrar(Pagina(
    'profesionales',
    'Editar página de profesionales',
    'Profesionales',
    'Título, introducción y textos vacíos. Cada ficha sigue en su registro.',
    'profesionales/busquedaProfesional.html',
    (
        ('encabezado', 'Encabezado'),
        ('introduccion', 'Introducción'),
        ('listado', 'Listado'),
    ),
    CATALOGO_PROFESIONALES,
    datos=_datos_profesionales,
    ayuda=_AYUDA_FOTO,
    aviso_publicado=_aviso('Página de profesionales'),
))

_registrar(Pagina(
    'servicios',
    'Editar página de servicios',
    'Servicios',
    'Títulos, búsqueda y catálogo vacío. Cada herramienta sigue en su registro.',
    'servicios/herramientas.html',
    (
        ('intro', 'Introducción'),
        ('menu', 'Menú'),
        ('busqueda', 'Búsqueda'),
    ),
    CATALOGO_SERVICIOS,
    datos=_datos_servicios,
    ayuda=_AYUDA_TEXTO,
    aviso_publicado=_aviso('Página de servicios'),
))

_registrar(Pagina(
    'bases-de-datos',
    'Editar página de bases de datos',
    'Bases de datos',
    'Títulos, búsqueda y catálogo vacío. Cada base de datos sigue en su registro.',
    'servicios/bases_de_datos.html',
    (
        ('intro', 'Introducción'),
        ('menu', 'Menú'),
        ('busqueda', 'Búsqueda'),
    ),
    CATALOGO_BASES,
    datos=_datos_bases,
    ayuda=_AYUDA_TEXTO,
    aviso_publicado=_aviso('Página de bases de datos'),
))

_registrar(Pagina(
    'contacto',
    'Editar página de contacto',
    'Contacto',
    'Textos de la página, alrededor del formulario.',
    'contacto/contacto.html',
    (
        ('presentacion', 'Presentación'),
        ('datos', 'Datos de contacto'),
        ('formulario', 'Formulario'),
    ),
    CATALOGO_CONTACTO,
    ayuda=_AYUDA + _AYUDA_FORMATO,
    aviso_publicado=_aviso('Página de contacto'),
))

if tuple(INDICES) != ORDEN:
    raise RuntimeError('El orden de páginas no coincide con el registro.')


def obtener(slug):
    return INDICES.get(slug)


def editores_admin():
    """Nombre corto del índice, para qué sirve la página y su editor."""
    editores = []
    for slug in ORDEN:
        pagina = INDICES[slug]
        editores.append({
            'titulo': pagina.titulo,
            'nombre': 'Inicio' if slug == INICIO else pagina.nombre,
            'nota': pagina.nota,
            'url': pagina.url_editor(),
        })
    return editores
