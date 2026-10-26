from django import template
from django.utils.html import format_html_join

from paginas.catalogo import IMAGEN, POR_CLAVE

register = template.Library()


@register.simple_tag(takes_context=True)
def edit_attrs(context, clave):
    """Marca el bloque en el lienzo. En la portada pública no escribe nada."""
    if not context.get('modo_editor'):
        return ''
    definicion = POR_CLAVE.get(clave)
    if definicion is None:
        return ''

    partes = [('data-edit-id', clave), ('data-edit-grupo', definicion.grupo)]
    # El área de texto admite saltos de línea; el lienzo tiene que pintarlos.
    if definicion.area:
        partes.append(('data-edit-multilinea', '1'))
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
