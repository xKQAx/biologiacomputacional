from django import forms

from investigacion.carrusel import CAMPOS_IMAGEN, imagen_disponible


def _campo_texto(numero):
    return forms.CharField(
        max_length=100,
        label=f'Texto de la diapositiva {numero}',
        error_messages={
            'required': f'Escribe el texto de la diapositiva {numero}.',
            'max_length': (
                f'El texto de la diapositiva {numero} admite como máximo 100 caracteres.'
            ),
        },
    )


class CarruselBorradorForm(forms.Form):
    """Textos e imágenes del borrador. No guarda el carrusel publicado."""

    titulo = forms.CharField(
        max_length=50,
        required=False,
        label='Título',
        error_messages={
            'max_length': 'El título admite como máximo 50 caracteres.',
        },
    )
    texto1 = _campo_texto(1)
    texto2 = _campo_texto(2)
    texto3 = _campo_texto(3)
    imagen1 = forms.ImageField(required=False, label='Imagen de la diapositiva 1')
    imagen2 = forms.ImageField(required=False, label='Imagen de la diapositiva 2')
    imagen3 = forms.ImageField(required=False, label='Imagen de la diapositiva 3')

    def __init__(self, *args, borrador=None, publicado=None, **kwargs):
        self.borrador = borrador
        self.publicado = publicado
        super().__init__(*args, **kwargs)
        for campo in ('imagen1', 'imagen2', 'imagen3'):
            self.fields[campo].error_messages['invalid_image'] = (
                'Sube un archivo de imagen válido.'
            )

    def clean(self):
        cleaned = super().clean()
        for numero, campo in enumerate(CAMPOS_IMAGEN, start=1):
            if campo in self.errors:
                continue
            if not self._imagen_resuelta(campo, cleaned):
                self.add_error(
                    campo,
                    f'Sube una imagen para la diapositiva {numero}.',
                )
        return cleaned

    def _imagen_resuelta(self, campo, cleaned):
        if cleaned.get(campo):
            return True
        for fuente in (self.borrador, self.publicado):
            if fuente is None:
                continue
            if imagen_disponible(getattr(fuente, campo)):
                return True
        return False


def filas_del_formulario(form, urls):
    filas = []
    for numero in (1, 2, 3):
        filas.append({
            'numero': numero,
            'texto': form[f'texto{numero}'],
            'imagen': form[f'imagen{numero}'],
            'url': urls.get(f'imagen{numero}', ''),
        })
    return filas
