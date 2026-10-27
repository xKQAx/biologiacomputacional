"""Textos actuales de la portada y qué se puede editar.

Si no hay fila publicada, la portada usa estos valores: es el mismo contenido
que tenía la plantilla. No define secciones nuevas.
"""

from dataclasses import dataclass, replace

from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html

TEXTO = 'texto'
ENLACE = 'enlace'
IMAGEN = 'imagen'

COMUN = 'comun'
VISITANTE = 'visitante'
SESION = 'sesion'

# El subtítulo del visitante resalta dos palabras. El texto plano y el HTML
# salen de las mismas piezas para que publicar sin cambios no altere la portada.
_SUB_ANTES = 'Descubra cómo nuestras'
_SUB_HERRAMIENTAS = 'herramientas'
_SUB_Y = 'y'
_SUB_RECURSOS = 'recursos'
_SUB_DESPUES = 'pueden impulsar su investigación en biología computacional.'
TEXTO_SUBTITULO_VISITANTE = (
    f'{_SUB_ANTES} {_SUB_HERRAMIENTAS} {_SUB_Y} {_SUB_RECURSOS} {_SUB_DESPUES}'
)

GRUPOS = (
    ('barra', 'Barra de navegación'),
    ('encabezado', 'Encabezado'),
    ('instituciones', 'Instituciones'),
    ('caracteristicas', 'Características'),
    ('encontrar', 'Qué encontrar'),
    ('nosotros', 'Nosotros'),
    ('beneficios', 'Beneficios'),
    ('llamado', 'Llamado a la acción'),
    ('pie', 'Pie de página'),
)

# La barra queda arriba y el pie abajo. Solo estas secciones se reordenan.
SECCIONES = (
    'encabezado',
    'instituciones',
    'caracteristicas',
    'encontrar',
    'nosotros',
    'beneficios',
    'llamado',
)

PLANTILLA_SECCION = {
    'encabezado': 'inicio/secciones/encabezado.html',
    'instituciones': 'inicio/secciones/instituciones.html',
    'caracteristicas': 'inicio/secciones/caracteristicas.html',
    'encontrar': 'inicio/secciones/encontrar.html',
    'nosotros': 'inicio/secciones/nosotros.html',
    'beneficios': 'inicio/secciones/beneficios.html',
    'llamado': 'inicio/secciones/llamado.html',
}

NOMBRES_GRUPO = dict(GRUPOS)


@dataclass(frozen=True)
class DefinicionBloque:
    clave: str
    grupo: str
    etiqueta: str
    texto: str
    tipo: str = TEXTO
    enlace: str = ''
    enlace_nombre: str = ''
    enlace_estatico: str = ''
    vista: str = COMUN
    multilinea: bool = False
    rico: bool = False
    orden: int = 0

    @property
    def area(self):
        """Párrafos largos usan un área de texto; el resto, un campo corto."""
        return self.multilinea or len(self.texto) > 80


def html_subtitulo_visitante():
    """HTML fijo del subtítulo original. No incluye texto escrito por el editor."""
    return format_html(
        '{} <strong class="text-warning fw-bold">{}</strong> {} '
        '<strong class="text-warning fw-bold">{}</strong> {}',
        _SUB_ANTES,
        _SUB_HERRAMIENTAS,
        _SUB_Y,
        _SUB_RECURSOS,
        _SUB_DESPUES,
    )


def _b(clave, grupo, etiqueta, texto, **extra):
    return DefinicionBloque(clave=clave, grupo=grupo, etiqueta=etiqueta, texto=texto, **extra)


_BASE = (
    _b('hero_etiqueta', 'encabezado', 'Etiqueta', 'Laboratorio de Biología Computacional'),
    _b('hero_titulo', 'encabezado', 'Título', 'Ciencia e Innovación'),
    _b('hero_titulo_acento', 'encabezado', 'Título destacado', 'al alcance de todos'),
    _b(
        'hero_subtitulo_visitante', 'encabezado', 'Subtítulo del visitante',
        TEXTO_SUBTITULO_VISITANTE, vista=VISITANTE, rico=True,
    ),
    _b(
        'hero_cta_registro', 'encabezado', 'Botón de registro', 'Regístrate gratis',
        tipo=ENLACE, enlace_nombre='register', vista=VISITANTE,
    ),
    _b(
        'hero_cta_sesion', 'encabezado', 'Botón de iniciar sesión', 'Iniciar sesión',
        tipo=ENLACE, enlace_nombre='signin', vista=VISITANTE,
    ),
    _b(
        'hero_subtitulo_sesion', 'encabezado', 'Subtítulo de quien ya entró',
        '¿Tienes alguna pregunta, comentario o sugerencia?\n'
        'Estamos siempre disponibles y listos para atenderte.',
        vista=SESION, multilinea=True,
    ),
    _b(
        'hero_cta_contacto', 'encabezado', 'Botón de contacto', 'Contáctanos',
        tipo=ENLACE, enlace_nombre='contactos', vista=SESION,
    ),
    _b(
        'hero_cta_profesionales', 'encabezado', 'Botón de profesionales', 'Ver profesionales',
        tipo=ENLACE, enlace_nombre='buscarProfesional', vista=SESION,
    ),
    _b('partners_etiqueta', 'instituciones', 'Texto', 'Respaldado por'),
    _b(
        'partner_biocom', 'instituciones', 'Logo del laboratorio',
        'Logo Biología Computacional', tipo=IMAGEN,
        enlace='https://sigiip.udes.edu.co/Image/Grupo/6',
    ),
    _b(
        'partner_udes', 'instituciones', 'Logo de la universidad',
        'Logo Universidad de Santander', tipo=IMAGEN,
        enlace='https://udes.edu.co/images/logo/udes-logo-principal.svg',
    ),
    _b('highlight_comunidad_titulo', 'caracteristicas', 'Comunidad: título', 'Comunidad activa'),
    _b(
        'highlight_comunidad_texto', 'caracteristicas', 'Comunidad: texto',
        'Investigadores, académicos y estudiantes colaborando.',
    ),
    _b(
        'highlight_investigacion_titulo', 'caracteristicas', 'Investigación: título',
        'Investigación de punta',
    ),
    _b(
        'highlight_investigacion_texto', 'caracteristicas', 'Investigación: texto',
        'Publicaciones en genómica, proteómica y más.',
    ),
    _b('highlight_datos_titulo', 'caracteristicas', 'Datos: título', 'Herramientas y datos'),
    _b(
        'highlight_datos_texto', 'caracteristicas', 'Datos: texto',
        'Bases de datos y software para tu trabajo.',
    ),
    _b('highlight_acceso_titulo', 'caracteristicas', 'Acceso: título', 'Acceso libre'),
    _b(
        'highlight_acceso_texto', 'caracteristicas', 'Acceso: texto',
        'Recursos disponibles para toda la comunidad.',
    ),
    _b('encontrar_titulo', 'encontrar', 'Título de la sección', '¿Qué puedo encontrar en BioCOM?'),
    _b(
        'encontrar_subtitulo', 'encontrar', 'Subtítulo de la sección',
        'Todo lo que necesitas para tu investigación en un solo lugar',
    ),
    _b(
        'tarjeta_profesionales_imagen', 'encontrar', 'Profesionales: imagen', 'Profesionales',
        tipo=IMAGEN, enlace_estatico='images/profesional.jpg',
    ),
    _b(
        'tarjeta_profesionales_titulo', 'encontrar', 'Profesionales: título', 'Profesionales',
        tipo=ENLACE, enlace_nombre='buscarProfesional',
    ),
    _b(
        'tarjeta_profesionales_texto', 'encontrar', 'Profesionales: texto',
        'Investigadores, científicos e ingenieros unidos por la biología computacional.',
    ),
    _b(
        'tarjeta_investigacion_imagen', 'encontrar', 'Investigación: imagen', 'Investigación',
        tipo=IMAGEN, enlace_estatico='images/investigacion.jpg',
    ),
    _b(
        'tarjeta_investigacion_titulo', 'encontrar', 'Investigación: título', 'Investigación',
        tipo=ENLACE, enlace_nombre='investigacion',
    ),
    _b(
        'tarjeta_investigacion_texto', 'encontrar', 'Investigación: texto',
        'Resultados en genómica, proteómica y biología de sistemas disponibles para todos.',
    ),
    _b(
        'tarjeta_servicios_imagen', 'encontrar', 'Servicios: imagen', 'Servicios',
        tipo=IMAGEN, enlace_estatico='images/herramientas.jpg',
    ),
    _b(
        'tarjeta_servicios_titulo', 'encontrar', 'Servicios: título', 'Servicios',
        tipo=ENLACE, enlace_nombre='servicios',
    ),
    _b(
        'tarjeta_servicios_texto', 'encontrar', 'Servicios: texto',
        'Herramientas y bases de datos especializadas para el análisis de datos biológicos.',
    ),
    _b('nosotros_etiqueta', 'nosotros', 'Etiqueta', 'Quiénes somos'),
    _b('nosotros_titulo', 'nosotros', 'Título', 'Conectando Ciencia e Innovación'),
    _b(
        'nosotros_parrafo_1', 'nosotros', 'Primer párrafo',
        'En Biología Computacional, fomentamos la intersección entre la '
        'biología y la informática. Nuestra plataforma nació para brindar un '
        'espacio inclusivo donde profesionales, investigadores y entusiastas '
        'pueden reunirse, colaborar y acceder a recursos especializados.',
    ),
    _b(
        'nosotros_parrafo_2', 'nosotros', 'Segundo párrafo',
        'Con enfoque en la innovación científica, trabajamos para proporcionar '
        'herramientas de vanguardia e investigaciones actualizadas.',
    ),
    _b(
        'nosotros_cta_visitante', 'nosotros', 'Botón del visitante', 'Únete a la comunidad',
        tipo=ENLACE, enlace_nombre='register', vista=VISITANTE,
    ),
    _b(
        'nosotros_cta_sesion', 'nosotros', 'Botón de quien ya entró', 'Conoce a los profesionales',
        tipo=ENLACE, enlace_nombre='buscarProfesional', vista=SESION,
    ),
    _b('beneficios_etiqueta', 'beneficios', 'Etiqueta', 'Por qué elegirnos'),
    _b('beneficios_titulo', 'beneficios', 'Título', 'Beneficios de Nuestra Plataforma'),
    _b('beneficio_acceso_titulo', 'beneficios', 'Acceso: título', 'Acceso centralizado'),
    _b(
        'beneficio_acceso_texto', 'beneficios', 'Acceso: texto',
        'Recursos y herramientas especializadas disponibles en un solo lugar.',
    ),
    _b('beneficio_comunidad_titulo', 'beneficios', 'Comunidad: título', 'Comunidad activa'),
    _b(
        'beneficio_comunidad_texto', 'beneficios', 'Comunidad: texto',
        'Profesionales y expertos para colaboración y networking científico.',
    ),
    _b(
        'beneficio_investigacion_titulo', 'beneficios', 'Investigación: título',
        'Investigación actualizada',
    ),
    _b(
        'beneficio_investigacion_texto', 'beneficios', 'Investigación: texto',
        'Acceso a las últimas investigaciones y desarrollos en el campo.',
    ),
    _b('beneficio_soporte_titulo', 'beneficios', 'Soporte: título', 'Soporte personalizado'),
    _b(
        'beneficio_soporte_texto', 'beneficios', 'Soporte: texto',
        'Servicios adaptados a las necesidades específicas de cada usuario.',
    ),
    _b(
        'cta_titulo', 'llamado', 'Título', '¿Listo para comenzar?', vista=VISITANTE,
    ),
    _b(
        'cta_subtitulo', 'llamado', 'Subtítulo',
        'Únete a nuestra comunidad de investigadores y accede a todos los recursos '
        'del laboratorio.',
        vista=VISITANTE,
    ),
    _b(
        'cta_cuenta', 'llamado', 'Botón de crear cuenta', 'Crear cuenta gratuita',
        tipo=ENLACE, enlace_nombre='register', vista=VISITANTE,
    ),
    _b(
        'cta_contacto', 'llamado', 'Botón de contactar', 'Contactar al equipo',
        tipo=ENLACE, enlace_nombre='contactos', vista=VISITANTE,
    ),
    _b('nav_inicio', 'barra', 'Inicio', 'Inicio', tipo=ENLACE, enlace_nombre='inicio'),
    _b(
        'nav_profesionales', 'barra', 'Profesionales', 'Profesionales',
        tipo=ENLACE, enlace_nombre='buscarProfesional',
    ),
    _b(
        'nav_investigacion', 'barra', 'Investigación', 'Investigación',
        tipo=ENLACE, enlace_nombre='investigacion',
    ),
    _b('nav_servicios', 'barra', 'Servicios', 'Servicios', tipo=ENLACE, enlace_nombre='servicios'),
    _b('nav_contacto', 'barra', 'Contacto', 'Contacto', tipo=ENLACE, enlace_nombre='contactos'),
    _b(
        'nav_registro', 'barra', 'Registrarme', 'Registrarme',
        tipo=ENLACE, enlace_nombre='register', vista=VISITANTE,
    ),
    _b(
        'nav_sesion', 'barra', 'Iniciar sesión', 'Iniciar sesión',
        tipo=ENLACE, enlace_nombre='signin', vista=VISITANTE,
    ),
    _b(
        'nav_perfil', 'barra', 'Mi perfil', 'Mi perfil',
        tipo=ENLACE, enlace_nombre='perfil', vista=SESION,
    ),
    _b(
        'nav_clave', 'barra', 'Cambiar contraseña', 'Cambiar contraseña',
        tipo=ENLACE, enlace_nombre='cambio_contrasena', vista=SESION,
    ),
    _b(
        'nav_gestion', 'barra', 'Gestionar usuarios', 'Gestionar usuarios',
        tipo=ENLACE, enlace_nombre='gestion_usuarios', vista=SESION,
    ),
    _b('nav_salir', 'barra', 'Cerrar sesión', 'Cerrar sesión', vista=SESION),
    _b(
        'pie_descripcion', 'pie', 'Descripción',
        'Laboratorio de Biología Computacional - Conectando Ciencia e Innovación',
    ),
    _b('pie_facebook', 'pie', 'Facebook', 'Facebook', tipo=ENLACE, enlace='#'),
    _b('pie_instagram', 'pie', 'Instagram', 'Instagram', tipo=ENLACE, enlace='#'),
    _b('pie_x', 'pie', 'Twitter / X', 'Twitter / X', tipo=ENLACE, enlace='#'),
    _b('pie_linkedin', 'pie', 'LinkedIn', 'LinkedIn', tipo=ENLACE, enlace='#'),
    _b('pie_recursos_titulo', 'pie', 'Título de recursos', 'Recursos'),
    _b(
        'pie_recursos_inicio', 'pie', 'Recursos: Inicio', 'Inicio',
        tipo=ENLACE, enlace_nombre='inicio',
    ),
    _b(
        'pie_recursos_profesionales', 'pie', 'Recursos: Profesionales', 'Profesionales',
        tipo=ENLACE, enlace_nombre='buscarProfesional',
    ),
    _b(
        'pie_recursos_investigacion', 'pie', 'Recursos: Investigación', 'Investigación',
        tipo=ENLACE, enlace_nombre='investigacion',
    ),
    _b(
        'pie_recursos_servicios', 'pie', 'Recursos: Servicios', 'Servicios',
        tipo=ENLACE, enlace_nombre='servicios',
    ),
    _b(
        'pie_recursos_contacto', 'pie', 'Recursos: Contacto', 'Contacto',
        tipo=ENLACE, enlace_nombre='contactos',
    ),
    _b('pie_legal_titulo', 'pie', 'Título legal', 'Información Legal'),
    _b(
        'pie_legal_privacidad', 'pie', 'Políticas de Privacidad', 'Políticas de Privacidad',
        tipo=ENLACE, enlace_nombre='politicas_privacidad',
    ),
    _b(
        'pie_legal_terminos', 'pie', 'Términos de Servicio', 'Términos de Servicio',
        tipo=ENLACE, enlace='#',
    ),
    _b('pie_legal_aviso', 'pie', 'Aviso Legal', 'Aviso Legal', tipo=ENLACE, enlace='#'),
    _b('pie_contacto_titulo', 'pie', 'Título de contacto', 'Contacto'),
    _b('pie_direccion_1', 'pie', 'Dirección', 'Campus Universitario Lagos del Cacique'),
    _b('pie_direccion_2', 'pie', 'Calle', 'Calle 70 No. 55-210'),
    _b('pie_direccion_3', 'pie', 'Ciudad', 'Bucaramanga, Colombia'),
    _b('pie_telefono', 'pie', 'Teléfono', 'PBX: +57 607 6516500'),
)

CATALOGO = tuple(
    replace(item, orden=(indice + 1) * 10) for indice, item in enumerate(_BASE)
)
POR_CLAVE = {item.clave: item for item in CATALOGO}

if len(POR_CLAVE) != len(CATALOGO):
    raise RuntimeError('Hay claves repetidas en la portada.')

_GRUPOS_VALIDOS = {grupo_id for grupo_id, _nombre in GRUPOS}
for _item in CATALOGO:
    if _item.grupo not in _GRUPOS_VALIDOS:
        raise RuntimeError(f'Grupo desconocido en {_item.clave}.')

if set(PLANTILLA_SECCION) != set(SECCIONES):
    raise RuntimeError('Cada sección ordenable necesita su plantilla.')

for _seccion in SECCIONES:
    if _seccion not in _GRUPOS_VALIDOS:
        raise RuntimeError(f'Sección desconocida: {_seccion}.')


def nombre_legible(definicion):
    """Parte y campo en español, para el panel del editor."""
    return f'{NOMBRES_GRUPO[definicion.grupo]} · {definicion.etiqueta}'


def enlace_predeterminado(definicion):
    """Ruta, archivo estático o URL externa que trae el bloque de fábrica."""
    if definicion.tipo == TEXTO:
        return ''
    if definicion.enlace_estatico:
        return static(definicion.enlace_estatico)
    if definicion.enlace_nombre:
        return reverse(definicion.enlace_nombre)
    return definicion.enlace
