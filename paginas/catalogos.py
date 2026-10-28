"""Textos que ya pintan las páginas públicas, aparte de la portada.

No define secciones nuevas: cada clave es un texto, enlace o imagen de la plantilla.
"""

from dataclasses import replace

from paginas.catalogo import BLOQUE, ENLACE, IMAGEN, PLANO, _b

_INTRO_SERVICIOS = (
    'Bienvenido a nuestra sección de servicios. Aquí encontrarás una variedad de '
    'herramientas y bases de datos que pueden ser útiles para tus investigaciones '
    'en biología computacional. Estos recursos están disponibles para que los '
    'estudiantes las utilicen en sus proyectos académicos. Explora las opciones que '
    'ofrecemos a continuación y aprovecha al máximo estas herramientas para '
    'potenciar tu trabajo en el laboratorio.'
)
_TEXTO_HERRAMIENTAS = (
    'Disponemos una amplia variedad de herramientas para '
    'apoyar tus investigaciones en biología computacional.'
)
_TEXTO_BASES = (
    'Disponemos de una amplia variedad de bases de datos para respaldar tus '
    'investigaciones en biología computacional.'
)


def con_orden(items):
    return tuple(replace(item, orden=(indice + 1) * 10) for indice, item in enumerate(items))


CATALOGO_INVESTIGACION = con_orden((
    _b('inv_titulo', 'introduccion', 'Título', 'INVESTIGACIÓN'),
    _b(
        'inv_texto', 'introduccion', 'Introducción',
        'En esta sección se encuentran los resultados obtenidos durante el desarrollo '
        'del proyecto de investigación titulado Docking molecular en la búsqueda de '
        'inhibidores potenciales de la oligomerización de α-sinucleina en la enfermedad '
        'de Parkinson y otras investigaciones.',
        formato=BLOQUE,
    ),
    _b(
        'inv_ver_mas', 'introduccion', 'Botón', 'Ver más',
        tipo=ENLACE, enlace='#seccion1',
    ),
    _b(
        'inv_microscopio', 'introduccion', 'Imagen', 'Microscopio de laboratorio',
        tipo=IMAGEN, enlace_estatico='investigacion/images/microscopio.jpg',
    ),
    _b('inv_contenidos_titulo', 'contenidos', 'Título', 'CONTENIDOS VIRTUALES'),
    _b(
        'inv_contenidos_texto', 'contenidos', 'Introducción',
        'El Proyecto Alpha-Sinucleína investiga la relación clave entre la proteína '
        'alpha-sinucleína y la enfermedad de Parkinson. Mientras tanto, la familia Cry11 '
        'de Bacillus thuringiensis ofrece proteínas insecticidas que desempeñan un papel '
        'vital en el control de plagas agrícolas, especialmente mosquitos transmisores de '
        'enfermedades como el dengue y la malaria.',
        formato=BLOQUE,
    ),
    _b(
        'inv_contenidos_imagen', 'contenidos', 'Imagen', 'Imagen de investigación',
        tipo=IMAGEN, enlace_estatico='investigacion/images/seccion1.jpg',
    ),
    _b('inv_sin_resultados', 'contenidos', 'Sin resultados', 'Sin resultados'),
))

CATALOGO_PROFESIONALES = con_orden((
    _b('prof_etiqueta', 'encabezado', 'Etiqueta', 'Comunidad BioCOM'),
    _b('prof_titulo', 'encabezado', 'Título', 'Nuestros Profesionales'),
    _b(
        'prof_subtitulo', 'encabezado', 'Introducción',
        'Investigadores, científicos e ingenieros unidos por la biología computacional. '
        'Explora sus perfiles y contribuciones.',
        formato=BLOQUE,
    ),
    _b(
        'prof_intro', 'introduccion', 'Texto',
        '¡Bienvenido a nuestra comunidad de biología computacional! '
        'Nuestros miembros son una mezcla diversa de investigadores, '
        'científicos de datos, ingenieros informáticos, académicos y '
        'estudiantes, todos unidos por su dedicación compartida a la '
        'integración de la biología y la informática en sus prácticas '
        'profesionales.\n\n'
        'Cada uno de nuestros miembros aporta una perspectiva única y valiosa al '
        'campo. Desde el diseño de algoritmos hasta el análisis de datos biológicos '
        'y la creación de modelos computacionales, nuestros profesionales impulsan '
        'el avance de la ciencia. Te invitamos a explorar sus perfiles.',
        multilinea=True, formato=BLOQUE,
    ),
    _b(
        'prof_imagen', 'introduccion', 'Imagen', 'Profesionales de biología computacional',
        tipo=IMAGEN, enlace_estatico='images/profesionales1.jpeg',
    ),
    _b('prof_vacio', 'listado', 'Catálogo vacío', 'No hay profesionales registrados aún.'),
    _b('prof_ver_perfil', 'listado', 'Botón de la ficha', 'Ver perfil'),
))

CATALOGO_SERVICIOS = con_orden((
    _b('srv_titulo', 'intro', 'Título', 'Servicios'),
    _b('srv_intro', 'intro', 'Introducción', _INTRO_SERVICIOS, formato=BLOQUE),
    _b('srv_herr_titulo', 'menu', 'Herramientas: título', 'Herramientas'),
    _b('srv_herr_texto', 'menu', 'Herramientas: texto', _TEXTO_HERRAMIENTAS, formato=BLOQUE),
    _b('srv_herr_tooltip', 'menu', 'Herramientas: ayuda', 'Herramientas disponibles', formato=PLANO),
    _b('srv_db_titulo', 'menu', 'Bases de datos: título', 'Bases de datos'),
    _b('srv_db_texto', 'menu', 'Bases de datos: texto', _TEXTO_BASES, formato=BLOQUE),
    _b('srv_db_tooltip', 'menu', 'Bases de datos: ayuda', 'Bases de datos disponibles', formato=PLANO),
    _b('srv_lista_titulo', 'busqueda', 'Título del listado', 'Herramientas disponibles'),
    _b('srv_buscar', 'busqueda', 'Placeholder de búsqueda', 'Buscar', formato=PLANO),
    _b('srv_buscar_etiqueta', 'busqueda', 'Etiqueta de búsqueda', 'Buscar herramientas'),
    _b('srv_buscar_boton', 'busqueda', 'Botón de búsqueda', 'Buscar'),
    _b('srv_resultados', 'busqueda', 'Resultados', 'fuentes encontradas para'),
    _b('srv_restablecer', 'busqueda', 'Restablecer búsqueda', 'Restablecer búsqueda'),
    _b(
        'srv_vacio_busqueda', 'busqueda', 'Búsqueda sin resultados',
        'No se encontraron herramientas para esta búsqueda.',
    ),
    _b('srv_vacio', 'busqueda', 'Catálogo vacío', 'Aún no hay herramientas publicadas.'),
))

CATALOGO_BASES = con_orden((
    _b('db_titulo', 'intro', 'Título', 'Servicios'),
    _b('db_intro', 'intro', 'Introducción', _INTRO_SERVICIOS, formato=BLOQUE),
    _b('db_herr_titulo', 'menu', 'Herramientas: título', 'Herramientas'),
    _b('db_herr_texto', 'menu', 'Herramientas: texto', _TEXTO_HERRAMIENTAS, formato=BLOQUE),
    _b('db_herr_tooltip', 'menu', 'Herramientas: ayuda', 'Herramientas disponibles', formato=PLANO),
    _b('db_db_titulo', 'menu', 'Bases de datos: título', 'Bases de datos'),
    _b('db_db_texto', 'menu', 'Bases de datos: texto', _TEXTO_BASES, formato=BLOQUE),
    _b('db_db_tooltip', 'menu', 'Bases de datos: ayuda', 'Bases de datos disponibles', formato=PLANO),
    _b('db_lista_titulo', 'busqueda', 'Título del listado', 'Bases de datos disponibles'),
    _b('db_buscar', 'busqueda', 'Placeholder de búsqueda', 'Buscar', formato=PLANO),
    _b('db_buscar_etiqueta', 'busqueda', 'Etiqueta de búsqueda', 'Buscar bases de datos'),
    _b('db_buscar_boton', 'busqueda', 'Botón de búsqueda', 'Buscar'),
    _b('db_resultados', 'busqueda', 'Resultados', 'fuentes encontradas para'),
    _b('db_restablecer', 'busqueda', 'Restablecer búsqueda', 'Restablecer búsqueda'),
    _b(
        'db_vacio_busqueda', 'busqueda', 'Búsqueda sin resultados',
        'No se encontraron bases de datos para esta búsqueda.',
    ),
    _b('db_vacio', 'busqueda', 'Catálogo vacío', 'Aún no hay bases de datos publicadas.'),
))

CATALOGO_CONTACTO = con_orden((
    _b('cto_etiqueta', 'presentacion', 'Etiqueta', 'Contáctanos'),
    _b('cto_titulo', 'presentacion', 'Título', '¿Cómo podemos ayudarte?'),
    # Vive dentro de un <p> de la plantilla, que no se modifica: solo formato en línea.
    _b(
        'cto_subtitulo', 'presentacion', 'Introducción',
        '¿Tienes alguna pregunta, comentario o sugerencia? '
        'Estamos siempre disponibles y listos para atenderte.',
    ),
    _b('cto_info_titulo', 'datos', 'Título', 'Información de contacto'),
    _b('cto_tel_etiqueta', 'datos', 'Teléfono: etiqueta', 'Teléfono'),
    _b('cto_tel', 'datos', 'Teléfono', 'PBX: +57 607 6516500', formato=PLANO),
    _b('cto_correo_etiqueta', 'datos', 'Correo: etiqueta', 'Correo electrónico'),
    _b('cto_correo', 'datos', 'Correo', 'biocomp@udes.edu.co', formato=PLANO),
    _b('cto_lugar_etiqueta', 'datos', 'Ubicación: etiqueta', 'Ubicación'),
    _b(
        'cto_lugar', 'datos', 'Ubicación',
        'Campus Lagos del Cacique\nCalle 70 No. 55-210\nBucaramanga, Colombia',
        multilinea=True,
    ),
    _b('cto_form_titulo', 'formulario', 'Título', 'Envíanos un mensaje'),
    _b('cto_nombres', 'formulario', 'Nombres', 'Nombres', formato=PLANO),
    _b('cto_apellidos', 'formulario', 'Apellidos', 'Apellidos', formato=PLANO),
    _b('cto_email', 'formulario', 'Correo electrónico', 'Correo electrónico', formato=PLANO),
    _b('cto_telefono', 'formulario', 'Teléfono', 'Teléfono', formato=PLANO),
    _b('cto_mensaje', 'formulario', 'Mensaje', 'Mensaje', formato=PLANO),
    _b('cto_obligatorio', 'formulario', 'Campo obligatorio', 'Este campo es obligatorio.', formato=PLANO),
    _b('cto_enviar', 'formulario', 'Botón de envío', 'Enviar mensaje'),
))
