from django import forms

from paginas.imagenes import validar_subida
from paginas.models import ImagenBiblioteca


class ImagenBibliotecaForm(forms.ModelForm):
    class Meta:
        model = ImagenBiblioteca
        fields = ('nombre', 'imagen', 'texto_alternativo')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'vTextField'}),
            'imagen': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
            }),
            'texto_alternativo': forms.TextInput(attrs={
                'class': 'vTextField', 'maxlength': 200,
            }),
        }

    def clean_imagen(self):
        imagen = self.cleaned_data['imagen']
        error = validar_subida(imagen)
        if error:
            raise forms.ValidationError(error)
        return imagen

