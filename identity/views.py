from typing import Any
from urllib.parse import urlparse

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from django.contrib import messages
from identity.models import AdditionalUserInfoForm
from BiologiaComputacional.forms import UsuarioForm, RegisterCustomForm, ProfileForm, ProfileAdditionalInfo
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.views import PasswordChangeView, PasswordResetDoneView
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse, reverse_lazy
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.views.generic import TemplateView
from django.http.response import JsonResponse
from django.utils.http import (
    url_has_allowed_host_and_scheme,
    urlsafe_base64_encode,
    urlsafe_base64_decode,
)
from BiologiaComputacional.mail import send_project_mail
from django.utils.encoding import force_str, force_bytes
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from BiologiaComputacional.permissions import staff_required, superuser_required
from identity.accounts import (
    ACTIVATION_RESEND_SESSION_KEY,
    login_candidates,
    username_taken,
    email_taken,
)
from identity.signals import ensure_user_profile

# Create your views here.

# Logica para mostrar un profesional


@method_decorator(login_required, name='dispatch')
class ProfileView(View):

    template_name = "identity/profile.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        additional_info, _created = ensure_user_profile(user)

        usuario_form = UsuarioForm(instance=user)
        additional_info_form = AdditionalUserInfoForm(instance=additional_info)
        return render(request, self.template_name, {'usuario_form': usuario_form, 'additional_info_form': additional_info_form})

    def post(self, request, *args, **kwargs):
        user = request.user
        additional_info, _created = ensure_user_profile(user)

        usuario_form = UsuarioForm(request.POST, instance=user)
        additional_info_form = AdditionalUserInfoForm(
            request.POST, request.FILES, instance=additional_info)

        if usuario_form.is_valid() and additional_info_form.is_valid():
            phone_number = additional_info_form.cleaned_data['phone_number']
            first_name = usuario_form.cleaned_data['first_name']
            last_name = usuario_form.cleaned_data['last_name']
            email = usuario_form.cleaned_data['email']

            if not phone_number:
                messages.error(
                    request, 'El campo Teléfono no puede estar vacío.')
            elif not phone_number.isdigit():
                messages.error(
                    request, 'El número de teléfono solo debe contener dígitos.')
            elif len(first_name) < 3:
                messages.error(
                    request, 'El nombre debe tener al menos 3 caracteres.')
            elif len(last_name) < 3:
                messages.error(
                    request, 'El apellido debe tener al menos 3 caracteres.')

            else:
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(
                        request, 'Ingrese una dirección de correo electrónico válida.')
                    return redirect('perfil')

                usuario_form.save()
                additional_info_form.save()
                messages.success(request, 'Información actualizada con éxito.')
        else:
            print("Errores de usuario_form:", usuario_form.errors)
            print("Errores de additional_info_form:",
                  additional_info_form.errors)
            messages.error(request, 'Error al actualizar la información.')

        return redirect('perfil')


def activation_page_context(request, email, **extra):
    """Datos comunes de la pantalla «revisa tu correo»."""
    extra["email"] = email
    extra["console_email"] = settings.EMAIL_BACKEND.endswith("console.EmailBackend")
    return extra


def send_activation_mail(request, user):
    """Arma el enlace con el mismo host de esta petición y lo envía."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    activation_url = request.build_absolute_uri(
        reverse("activate", kwargs={"uidb64": uid, "token": token})
    )
    message = render_to_string("identity/acc_active_email.html", {
        "user": user,
        "activation_url": activation_url,
    })
    return send_project_mail("Activa tu cuenta", message, [user.email])


def register(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        user_form = RegisterCustomForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.is_active = False
            user.save()

            # La señal ya creó la fila; aquí solo se copian los datos del formulario.
            profile, _created = ensure_user_profile(user)
            profile.phone_number = profile_form.cleaned_data.get('phone_number') or ''
            profile.gender = profile_form.cleaned_data.get('gender') or ''
            image = profile_form.cleaned_data.get('image')
            if image:
                profile.image = image
            profile.save()

            mail_ok = send_activation_mail(request, user)
            return render(
                request,
                'identity/look_email.html',
                activation_page_context(request, user.email, mail_failed=not mail_ok),
            )
    else:
        user_form = RegisterCustomForm()
        profile_form = ProfileForm()

    return render(request, 'identity/register.html', {
        'form': user_form,
        'profile_form': profile_form,
    })


def account_availability(request):
    """Avisa si el usuario o el correo ya tienen cuenta, antes de enviar el formulario."""
    username = request.GET.get("username", "")
    email = request.GET.get("email", "")
    data = {}
    if username.strip():
        data["username_taken"] = username_taken(username)
    if email.strip():
        data["email_taken"] = email_taken(email)
    return JsonResponse(data)

# Logica para cerrar sesion


def user_logout(request):

    logout(request)

    return redirect('inicio')

# Validaciones para el formulario Login


User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    """No revela si la cuenta existe cuando falla la clave.

    La cuenta inactiva sí se explica, porque quien escribió la contraseña
    correcta ya demostró que es el dueño.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Nombre de usuario o contraseña incorrectos.',
        'inactive': (
            'Tu cuenta todavía no está activada. Revisa el correo de verificación, '
            'incluida la carpeta de spam.'
        ),
        'ambiguous': 'Hay varias cuentas con este correo. Entra con tu nombre de usuario.',
    }

    def clean(self):
        identifier = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        self.offer_resend = False

        if identifier is not None and password:
            matches = login_candidates(identifier)
            # Varias cuentas y clave mala: el aviso genérico. Decir que el
            # correo está repetido confirmaría que existe sin demostrar la clave.
            if len(matches) > 1:
                if any(account.check_password(password) for account in matches):
                    raise forms.ValidationError(
                        self.error_messages['ambiguous'],
                        code='ambiguous',
                    )
                raise self.get_invalid_login_error()

            account = matches[0] if matches else None
            username = account.username if account is not None else identifier
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            if self.user_cache is None:
                if (
                    account is not None
                    and not account.is_active
                    and account.check_password(password)
                ):
                    self.offer_resend = True
                    self.resend_user_id = account.pk
                    raise forms.ValidationError(
                        self.error_messages['inactive'],
                        code='inactive',
                    )
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


def safe_next_url(request):
    """Ruta interna a la que volver tras entrar.

    Ignora destinos de otro sitio y la propia pantalla de login, para no
    abrir un enlace externo ni entrar en un bucle.
    """
    candidate = (request.POST.get("next") or request.GET.get("next") or "").strip()
    allowed = url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if not allowed:
        return ""
    if urlparse(candidate).path.rstrip("/") == reverse("signin").rstrip("/"):
        return ""
    return candidate

# Logica formulario login


def signin(request):
    next_url = safe_next_url(request)
    if request.user.is_authenticated:
        return redirect(next_url or reverse('inicio'))

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, request.POST)

        if form.is_valid():
            request.session.pop(ACTIVATION_RESEND_SESSION_KEY, None)
            login(request, form.get_user())
            if 'remember_me' in request.POST:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            return redirect(next_url or reverse('inicio'))

        request.session.pop(ACTIVATION_RESEND_SESSION_KEY, None)
        if getattr(form, 'offer_resend', False):
            request.session[ACTIVATION_RESEND_SESSION_KEY] = form.resend_user_id
        return render(request, 'identity/signin.html', {
            'form': form,
            'next_url': next_url,
        })

    return render(request, 'identity/signin.html', {
        'form': CustomAuthenticationForm(),
        'next_url': next_url,
    })


@require_POST
def resend_activation(request):
    """Reenvía el enlace si ya se comprobó la contraseña, o si indican el correo."""
    user_id = request.session.pop(ACTIVATION_RESEND_SESSION_KEY, None)
    if user_id:
        user = User.objects.filter(pk=user_id, is_active=False).first()
        if user is not None:
            mail_ok = send_activation_mail(request, user)
            return render(
                request,
                'identity/look_email.html',
                activation_page_context(
                    request, user.email, mail_failed=not mail_ok, resent=True
                ),
            )

    email = (request.POST.get('email') or '').strip()
    if email:
        pending = User.objects.filter(email__iexact=email, is_active=False)[:5]
        for user in pending:
            send_activation_mail(request, user)
    return render(
        request,
        'identity/look_email.html',
        activation_page_context(request, email, generic_resend=True),
    )

# Cambiar contraseña de usuario con sesion iniciada


class ProfilePasswordChangeView(PasswordChangeView):

    template_name = "identity/change_password.html"
    success_url = reverse_lazy('cambio_contrasena')

    def get_context_data(self, **kwargs):
        # Sin ficha, la plantilla rompía y no se podía cambiar la clave.
        ensure_user_profile(self.request.user)
        context = super().get_context_data(**kwargs)
        context['password_changed'] = self.request.session.get(
            'password_changed', False)
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Cambio de contraseña exitoso')
        update_session_auth_hash(self.request, form.user)
        self.request.session['password_changed'] = True
        return super().form_valid(form)


# Cambiar contraseña de usuario sin sesion iniciada
UserModel = get_user_model()


def password_reset_confirm(request, uidb64, token):
    # Decodificar el uid y verificar si es válido
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    # Verificar si el token es válido
    if user is not None and default_token_generator.check_token(user, token):
        # Si el usuario y el token son válidos, procesar el formulario
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        return render(request, 'identity/password_reset_confirm.html', {'form': form})
    else:
        # Si el usuario o el token no son válidos, redireccionar a una página de error o mostrar un mensaje
        return redirect('password_reset_invalid')


class PasswordResetInvalidView(TemplateView):

    template_name = "identity/password_reset_invalid.html"


class PasswordResetSentView(PasswordResetDoneView):
    """La pantalla de «revisa el correo», con el aviso de consola en local."""

    template_name = "identity/password_reset_sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["console_email"] = settings.EMAIL_BACKEND.endswith(
            "console.EmailBackend"
        )
        context["reset_minutes"] = max(settings.PASSWORD_RESET_TIMEOUT // 60, 1)
        return context


@method_decorator(staff_required, name='dispatch')
class ManageUsersView(TemplateView):

    template_name = "identity/manage_users.html"


# Campos que el listado de gestión puede ver. Nunca el hash de la contraseña.
USER_LIST_FIELDS = (
    'id', 'username', 'first_name', 'last_name', 'email',
    'is_staff', 'is_superuser', 'is_active', 'last_login', 'date_joined',
)


@staff_required
def info_usuarios(request):
    info_users = list(User.objects.values(*USER_LIST_FIELDS))
    data = {'info_users': info_users}
    return JsonResponse(data, safe=False)


@staff_required
def detalle_usuarios(request, pk):
    usuarios = get_object_or_404(User, pk=pk)
    usuarios_adicional_info = get_object_or_404(
        ProfileAdditionalInfo, user=usuarios)
    return render(request, 'identity/detalle_usuarios.html', {'usuarios': usuarios, 'usuarios_adicional_info': usuarios_adicional_info})


# Ascender, descender y eliminar siguen siendo de superusuario: la ficha solo
# muestra esos botones a quien ya es superusuario. El resto del personal no puede.
@superuser_required
@require_POST
def ascender_administrador(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    usuario.is_staff = True
    usuario.save()

    messages.success(
        request, f"El usuario {usuario.username} ha sido ascendido a Administrador.")

    return redirect('detalle_usuarios', pk=pk)


@superuser_required
@require_POST
def descender_administrador(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    usuario.is_staff = False
    usuario.save()

    messages.success(
        request, f"El usuario {usuario.username} ha sido descendido a Estudiante.")

    return redirect('detalle_usuarios', pk=pk)


@staff_required
@require_POST
def desactivar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.user.is_superuser or (request.user.is_staff and not usuario.is_staff):
        usuario.is_active = False
        usuario.save()
        messages.success(
            request, f"El usuario {usuario.username} ha sido desactivado correctamente.")
    else:
        messages.error(
            request, f"Imposible desactivar un usuario del mismo rango.")
    return redirect('detalle_usuarios', pk=pk)


@staff_required
@require_POST
def activar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    usuario.is_active = True
    usuario.save()

    messages.success(
        request, f"El usuario {usuario.username} ha sido activado correctamente.")

    return redirect('detalle_usuarios', pk=pk)


@superuser_required
@require_POST
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    usuario.delete()

    messages.success(
        request, f"El usuario {usuario.username} ha sido eliminado correctamente.")

    return redirect('gestion_usuarios')

# Activacion de cuentas por correo


def _user_from_uid(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None


def activate(request, uidb64, token):
    user = _user_from_uid(uidb64)
    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        # Entrar aquí invalida el token (cambia last_login). La pantalla de
        # éxito vive en otra URL para que recargar no parezca un enlace roto.
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("activation_success")
    if user is not None and user.is_active:
        return render(
            request, "identity/activation_success.html", {"already_active": True}
        )
    return render(request, "identity/activation_invalid.html")


@login_required
def activation_success(request):
    return render(request, "identity/activation_success.html")
