from django import template
from django.utils.html import format_html_join

from paginas.catalogo import ENLACE, IMAGEN, POR_CLAVE
from paginas.contenido import resolver

register = template.Library()


@register.simple_tag(takes_context=True)
def asegurar_bloques(context):
    """Deja en el contexto la barra y el pie que ve el visitante.

    Si la vista ya pasó bloques (portada publicada o lienzo con borrador),
    no los pisa: el borrador solo vive en ese lienzo.
    """
    if context.get('bloques') is None:
        context['bloques'] = resolver(preferir_borrador=False)
    return ''


@register.simple_tag
def editores_sitio():
    """Enlaces del índice: la portada y el resto de páginas con el mismo editor."""
    from paginas.registro import editores_admin
    return editores_admin()


@register.simple_tag(takes_context=True)
def edit_attrs(context, clave):
    """Marca el bloque en el lienzo. En la página pública no escribe nada."""
    if not context.get('modo_editor'):
        return ''
    por_clave = context.get('catalogo_lienzo')
    if por_clave is None:
        por_clave = POR_CLAVE
    definicion = por_clave.get(clave)
    if definicion is None:
        return ''

    partes = [('data-edit-id', clave), ('data-edit-grupo', definicion.grupo)]
    # El área de texto admite saltos de línea; el lienzo tiene que pintarlos.
    if definicion.area:
        partes.append(('data-edit-multilinea', '1'))
    # El href solo se mueve si el bloque es un enlace. Un texto puesto sobre
    # un botón (ver perfil, restablecer) no debe vaciar su dirección.
    if definicion.tipo == ENLACE:
        partes.append(('data-edit-enlace', '1'))
    if definicion.tipo == IMAGEN:
        partes.append(('data-edit-imagen', '1'))
    if definicion.rico:
        partes.append(('data-edit-rico', clave))
        partes.append(('data-edit-predeterminado', definicion.texto))
    return format_html_join(' ', '{}="{}"', partes)


@register.simple_tag
def vista_attrs(vista):
    """Distingue el texto del visitante y el de quien ya inició sesión."""
    if vista not in ('visitante', 'sesion'):
        return ''
    return format_html_join('', '{}="{}"', [('data-vista', vista)])
