from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from identity.accounts import email_taken, normalize_email, username_taken
from identity.models import ProfileAdditionalInfo
from profesionales.models import InformacionProfesional, Articulos
from servicios.models import Categoria, Servicio
from django.contrib.auth.forms import UserChangeForm
import re
from investigacion.models import CategoriaI, Investigacion

# Una sola frase para la regla que ya anuncia la ayuda: 10 dígitos.
MENSAJE_TELEFONO = (
    'El teléfono debe tener 10 dígitos, sin espacios ni otros caracteres.'
)


class FormularioContacto(forms.Form):
    nombres = forms.CharField(
        error_messages={'required': 'Indica tus nombres.'},
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
    )
    apellidos = forms.CharField(
        error_messages={'required': 'Indica tus apellidos.'},
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
    )
    email = forms.EmailField(
        error_messages={
            'required': 'Indica tu correo electrónico.',
            'invalid': 'Introduce un correo electrónico válido.',
        },
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Email'}),
    )
    telefono = forms.CharField(
        min_length=10,
        max_length=10,
        help_text='Introduce tu número de teléfono (10 dígitos)',
        error_messages={
            'required': 'Indica tu número de teléfono.',
            'min_length': MENSAJE_TELEFONO,
            'max_length': MENSAJE_TELEFONO,
        },
    )
    opiniones = forms.CharField(
        error_messages={'required': 'Escribe tu mensaje.'},
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Opiniones'}),
    )

    def clean_telefono(self):
        # La longitud ya la limita el campo; aquí solo se rechazan letras y símbolos.
        telefono = self.cleaned_data.get('telefono') or ''
        if not telefono.isdigit():
            raise forms.ValidationError(MENSAJE_TELEFONO)
        return telefono

# Formulario para un Usuario nuevo


class RegisterCustomForm(UserCreationForm):
    error_messages = {
        "password_mismatch": "Las contraseñas no coinciden.",
    }
    first_name = forms.CharField(
        max_length=30, required=False, help_text='Ingresa tu nombre.')
    last_name = forms.CharField(
        max_length=30, required=False, help_text='Ingresa tu apellido.')
    email = forms.EmailField(
        max_length=254, help_text='Requerido. Informa una dirección de correo electrónico válida.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'email', 'password1', 'password2', )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and username_taken(username):
            raise forms.ValidationError(
                "Este nombre de usuario ya está registrado. Inicia sesión o elige otro.",
                code="unique",
            )
        return username

    def clean_email(self):
        email = normalize_email(self.cleaned_data.get("email"))
        if email_taken(email):
            raise forms.ValidationError(
                "Ya existe una cuenta con este correo. Inicia sesión o, si no puedes entrar, usa «¿Olvidaste tu contraseña?».",
                code="unique",
            )
        return email

# Formulario para un Usuario nuevo


class ProfileForm(forms.ModelForm):
    class Meta:
        model = ProfileAdditionalInfo
        fields = ['image', 'phone_number', 'gender']

    gender = forms.ChoiceField(
        choices=ProfileAdditionalInfo.GENDER_CHOICES, required=False)

# Formulario para un Usuario nuevo


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = normalize_email(self.cleaned_data.get("email"))
        if email_taken(email, exclude_pk=getattr(self.instance, "pk", None)):
            raise forms.ValidationError(
                "Ya existe una cuenta con este correo.",
                code="unique",
            )
        return email

# Formulario para crear un nuevo profesional


class ProfileFormProfessional(forms.ModelForm):
    foto = forms.ImageField(
        required=True, help_text='Sube una imagen para tu perfil')
    nombre = forms.CharField(max_length=30, help_text='Introduce tu nombre')
    apellido = forms.CharField(
        max_length=30, help_text='Introduce tu apellido')
    titulo_universitario = forms.CharField(
        max_length=120, help_text='Introduce tu título universitario')
    universidad = forms.CharField(
        max_length=50, help_text='Introduce el nombre de tu universidad')
    email = forms.EmailField(
        help_text='Introduce tu dirección de correo electrónico')
    telefono = forms.CharField(
        max_length=10, help_text='Introduce tu número de teléfono (10 dígitos)')

    class Meta:
        model = InformacionProfesional
        fields = ['enlace_a_scholar', 'foto', 'nombre', 'apellido', 'titulo_universitario', 'universidad', 'email',
                  'telefono', 'campo0', 'campo1', 'campo2', 'campo3', 'campo4', 'campo5', 'campo6', 'facultad', 'grupo_investigacion', 'campus']

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit():
            raise forms.ValidationError(
                'El número de teléfono solo debe contener dígitos.')
        return telefono


class ArticleForm(forms.ModelForm):
    enlace_articulo = forms.CharField(
        label="Enlace al artículo",
        widget=forms.TextInput(attrs={
                               'class': 'form-control', 'placeholder': 'Enlace del artículo (Estructura: https://misitio.com)'})
    )
    titulo = forms.CharField(
        label="Título",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Título de artículo'})
    )
    descripcion = forms.CharField(
        label="Descripción",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Descripción del artículo'})
    )
    anio = forms.CharField(
        label="Año",
        max_length=4, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Año del artículo'})
    )

    class Meta:
        model = Articulos
        fields = ['enlace_articulo', 'titulo', 'descripcion', 'anio']

    def clean_enlace_articulo(self):
        enlace = self.cleaned_data.get('enlace_articulo')

        if not enlace.startswith('http'):
            raise forms.ValidationError(
                "El enlace debe tener la estructura correcta (Ejemplo: https://misitio.com)")

        if not enlace.startswith('https'):
            raise forms.ValidationError(
                "El enlace debe ser seguro y comenzar con 'https://'")

        return enlace

    def clean_anio(self):
        anio = self.cleaned_data.get('anio')
        if not anio.isdigit():
            raise forms.ValidationError(
                'El año solo debe contener dígitos.')
        return anio


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre_categoria']


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['categoria', 'nombre', 'imagen_servicio', 'archivo',
                  'video_enlace', 'descrip', 'desarrollador', 'desarrollador_enlace', 'nombre_licencia', 'nombre_licencia_enlace']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if Servicio.objects.filter(nombre=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                'El nombre del servicio ya existe. Por favor, elige otro nombre.')
        return nombre


class CategoriaInvestigacionForm(forms.ModelForm):
    class Meta:
        model = CategoriaI
        fields = ['nombre_categoria']


class InvestigacionForm(forms.ModelForm):
    class Meta:
        model = Investigacion
        fields = ['categoria', 'nombre', 'descrip', 'imagen_investigacion',
                  'imagen_tif', 'pdf', 'mejores_pdf', 'imagen_extra_1', 'imagen_extra_2', 'imagen_extra_3']

