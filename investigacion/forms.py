from django import forms

from investigacion.carrusel import CAMPOS_IMAGEN, imagen_disponible
from investigacion.models import Investigacion


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


class InvestigacionForm(forms.ModelForm):
    """Formulario de ficha con metadatos opcionales para facilitar su búsqueda."""

    class Meta:
        model = Investigacion
        fields = [
            'categoria', 'nombre', 'descrip', 'anio', 'organismo', 'metodos',
            'palabras_clave', 'publicacion_url', 'datos_url', 'codigo_url',
            'imagen_investigacion', 'imagen_tif', 'pdf', 'mejores_pdf',
            'imagen_extra_1', 'imagen_extra_2', 'imagen_extra_3',
        ]
        widgets = {
            'anio': forms.NumberInput(attrs={'min': 1900, 'max': 2100}),
            'metodos': forms.TextInput(attrs={
                'placeholder': 'p. ej. modelado molecular, análisis estadístico',
            }),
            'palabras_clave': forms.TextInput(attrs={
                'placeholder': 'Separadas por comas',
            }),
        }
        help_texts = {
            'organismo': 'Es opcional; ayuda a encontrar proyectos relacionados.',
            'metodos': 'Puedes escribir varias técnicas separadas por comas.',
            'palabras_clave': 'Usa términos breves separados por comas.',
            'publicacion_url': 'Enlace a artículo, DOI o página de publicación.',
            'datos_url': 'Enlace a datos públicos o repositorio.',
            'codigo_url': 'Enlace al código fuente o repositorio.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            clase = 'form-select' if isinstance(campo.widget, forms.Select) else 'form-control'
            clases_previas = campo.widget.attrs.get('class', '')
            campo.widget.attrs['class'] = f'{clases_previas} {clase}'.strip()
