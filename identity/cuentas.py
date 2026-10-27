"""Pantalla de cuentas del admin.

Reutiliza las comprobaciones del registro (nombre, correo y contraseña).
No sigue el alta pública: allí la cuenta nace inactiva y espera un correo.
Aquí el personal deja la cuenta lista para entrar.

Dar o quitar el acceso al panel sigue siendo de superusuario, como
ascender y descender en la gestión del sitio. Un miembro del personal
no modifica cuentas de personal.
"""

from django.contrib import admin, messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django import forms

from BiologiaComputacional.forms import RegisterCustomForm
from identity.accounts import email_taken, normalize_email, normalize_username, username_taken

User = get_user_model()

_ETIQUETAS = {
    "username": "Usuario",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "email": "Correo",
    "password1": "Contraseña",
    "password2": "Repetir contraseña",
}


def puede_editar_cuenta(actor, cuenta):
    """Superusuario: cualquiera. Personal: solo cuentas que no son de personal."""
    if not getattr(actor, "is_authenticated", False):
        return False
    if not actor.is_active or not actor.is_staff:
        return False
    if actor.is_superuser:
        return True
    return not cuenta.is_staff and not cuenta.is_superuser


class AltaCuentaForm(RegisterCustomForm):
    """Misma validación que el registro, con la cuenta activa si así se marca."""

    is_active = forms.BooleanField(required=False, initial=True, label="Activa")

    class Meta(RegisterCustomForm.Meta):
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "password1",
            "password2",
        )

    def __init__(self, *args, puede_asignar_personal=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.puede_asignar_personal = puede_asignar_personal
        for nombre, etiqueta in _ETIQUETAS.items():
            if nombre in self.fields:
                self.fields[nombre].label = etiqueta
        self.fields["is_active"].help_text = "Si se quita, la persona no puede entrar."
        if puede_asignar_personal:
            self.fields["is_staff"] = forms.BooleanField(
                required=False,
                label="Personal del laboratorio",
                help_text="Puede entrar al panel y editar el sitio.",
            )
        self.order_fields([
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "password1",
            "password2",
        ])


class EdicionCuentaForm(forms.ModelForm):
    """Edita la cuenta. La contraseña solo cambia si se escriben las dos."""

    password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Déjala en blanco para no cambiarla.",
    )
    password2 = forms.CharField(
        label="Repetir contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, actor=None, puede_asignar_personal=False, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        for nombre, etiqueta in _ETIQUETAS.items():
            if nombre in self.fields and nombre not in ("password1", "password2"):
                self.fields[nombre].label = etiqueta
        self.fields["email"].required = True
        self.fields["is_active"].label = "Activa"
        self.fields["is_active"].help_text = "Si se quita, la persona no puede entrar."
        if puede_asignar_personal:
            self.fields["is_staff"] = forms.BooleanField(
                required=False,
                label="Personal del laboratorio",
                help_text="Puede entrar al panel y editar el sitio.",
                initial=bool(getattr(self.instance, "is_staff", False)),
            )
        self.order_fields([
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "password1",
            "password2",
        ])

    def clean_username(self):
        username = normalize_username(self.cleaned_data.get("username"))
        if username_taken(username, exclude_pk=self.instance.pk):
            raise forms.ValidationError(
                "Este nombre de usuario ya está registrado. Elige otro.",
                code="unique",
            )
        return username

    def clean_email(self):
        email = normalize_email(self.cleaned_data.get("email"))
        if not email:
            raise forms.ValidationError("El correo es obligatorio.")
        if email_taken(email, exclude_pk=self.instance.pk):
            raise forms.ValidationError(
                "Ya existe una cuenta con este correo.",
                code="unique",
            )
        return email

    def clean(self):
        cleaned = super().clean()
        self._evitar_quitarse_el_acceso(cleaned)
        self._validar_clave_nueva(cleaned)
        return cleaned

    def _evitar_quitarse_el_acceso(self, cleaned):
        # El formulario no toca is_superuser. Tampoco deja cerrar la propia puerta.
        if not self.actor or not self.instance.pk or self.instance.pk != self.actor.pk:
            return
        if "is_active" in cleaned and not cleaned.get("is_active"):
            self.add_error("is_active", "No puedes desactivar tu propia cuenta.")
        if "is_staff" in self.fields and not cleaned.get("is_staff"):
            self.add_error("is_staff", "No puedes quitarte el acceso al panel.")

    def _validar_clave_nueva(self, cleaned):
        clave = cleaned.get("password1") or ""
        repetida = cleaned.get("password2") or ""
        if not clave and not repetida:
            return
        if clave != repetida:
            self.add_error("password2", "Las contraseñas no coinciden.")
            return
        auxiliar = SetPasswordForm(
            self.instance,
            data={"new_password1": clave, "new_password2": repetida},
        )
        if auxiliar.is_valid():
            return
        for nombre in ("new_password1", "new_password2"):
            destino = "password1" if nombre == "new_password1" else "password2"
            for error in auxiliar.errors.get(nombre, []):
                self.add_error(destino, error)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        clave = self.cleaned_data.get("password1")
        if clave:
            usuario.set_password(clave)
        if commit:
            usuario.save()
        return usuario


def lista_cuentas(request):
    filas = []
    for usuario in User.objects.order_by("username"):
        filas.append({
            "pk": usuario.pk,
            "username": usuario.username,
            "email": usuario.email,
            "is_staff": usuario.is_staff,
            "is_active": usuario.is_active,
            "puede_editar": puede_editar_cuenta(request.user, usuario),
        })
    return _render(request, "admin/cuentas/lista.html", {
        "title": "Cuentas",
        "filas": filas,
        "es_superusuario": request.user.is_superuser,
    })


def nueva_cuenta(request):
    puede = request.user.is_superuser
    if request.method == "POST":
        form = AltaCuentaForm(request.POST, puede_asignar_personal=puede)
        if form.is_valid():
            usuario = form.save(commit=False)
            _aplicar_acceso(usuario, form, request.user, alta=True)
            usuario.save()
            messages.success(request, f"Cuenta {usuario.username} creada.")
            return redirect("admin:cuentas")
    else:
        form = AltaCuentaForm(puede_asignar_personal=puede)
    return _render(request, "admin/cuentas/formulario.html", {
        "title": "Nueva cuenta",
        "form": form,
        "volver": "admin:cuentas",
    })


def editar_cuenta(request, pk):
    cuenta = get_object_or_404(User, pk=pk)
    if not puede_editar_cuenta(request.user, cuenta):
        raise PermissionDenied
    puede = request.user.is_superuser
    if request.method == "POST":
        form = EdicionCuentaForm(
            request.POST,
            instance=cuenta,
            actor=request.user,
            puede_asignar_personal=puede,
        )
        if form.is_valid():
            usuario = form.save(commit=False)
            _aplicar_acceso(usuario, form, request.user, alta=False)
            usuario.save()
            if form.cleaned_data.get("password1") and usuario.pk == request.user.pk:
                update_session_auth_hash(request, usuario)
            messages.success(request, f"Cuenta {usuario.username} actualizada.")
            return redirect("admin:cuentas")
    else:
        form = EdicionCuentaForm(
            instance=cuenta,
            actor=request.user,
            puede_asignar_personal=puede,
        )
    return _render(request, "admin/cuentas/formulario.html", {
        "title": "Editar cuenta",
        "form": form,
        "volver": "admin:cuentas",
    })


def _aplicar_acceso(usuario, form, actor, *, alta):
    """El panel no crea superusuarios ni deja que un staff se ascienda solo."""
    if actor.is_superuser:
        usuario.is_staff = bool(form.cleaned_data.get("is_staff"))
    elif alta:
        usuario.is_staff = False
    if alta:
        usuario.is_superuser = False


def _render(request, plantilla, contexto):
    datos = admin.site.each_context(request)
    datos.update(contexto)
    return render(request, plantilla, datos)
