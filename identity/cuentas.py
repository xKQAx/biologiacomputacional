"""Pantalla de cuentas del admin.

Reutiliza las comprobaciones del registro (nombre, correo y contraseña).
No sigue el alta pública: allí la cuenta nace inactiva y espera un correo.
Aquí el personal deja la cuenta lista para entrar, o la cierra.

Dar o quitar el acceso al panel sigue siendo de superusuario. Un miembro
del personal no modifica cuentas de personal. Nadie desactiva ni elimina
la suya. Si borrar falla, la transacción no deja la cuenta a medias.
"""

from django.contrib import admin, messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db import router, transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django import forms

from BiologiaComputacional.forms import RegisterCustomForm
from identity.accounts import (
    email_taken,
    marcar_suspension,
    normalize_email,
    normalize_username,
    username_taken,
)

User = get_user_model()

_ETIQUETAS = {
    "username": "Usuario",
    "first_name": "Nombre",
    "last_name": "Apellidos",
    "email": "Correo",
    "password1": "Contraseña",
    "password2": "Repetir contraseña",
}

# Lo que se va con la cuenta, en español. El resto usa el nombre del modelo.
_RELACIONES = {
    "identity.profileadditionalinfo": "El perfil, con la foto y el teléfono",
    "identity.additionaluserinfo": "El perfil anterior",
    "admin.logentry": "Los registros de actividad en el panel",
}

_AYUDA_ACTIVA = (
    "Si se quita, la persona no puede entrar. "
    "El correo de activación del sitio no vuelve a abrir la cuenta."
)
_AYUDA_SOLO_SUPER = "Solo un superusuario puede cambiar esto."


def puede_editar_cuenta(actor, cuenta):
    """Superusuario: cualquiera. Personal: solo cuentas que no son de personal."""
    if not getattr(actor, "is_authenticated", False):
        return False
    if not actor.is_active or not actor.is_staff:
        return False
    if actor.is_superuser:
        return True
    return not cuenta.is_staff and not cuenta.is_superuser


def puede_cerrar_cuenta(actor, cuenta):
    """Desactivar o eliminar. La propia cuenta queda fuera."""
    if not puede_editar_cuenta(actor, cuenta):
        return False
    return cuenta.pk != actor.pk


def nombre_visible(usuario):
    partes = [usuario.first_name or "", usuario.last_name or ""]
    return " ".join(parte.strip() for parte in partes if parte.strip())


def _preparar_campos(form, actor, instancia):
    """Etiquetas en español y los interruptores de acceso en el mismo formulario."""
    for nombre, etiqueta in _ETIQUETAS.items():
        if nombre in form.fields:
            form.fields[nombre].label = etiqueta
    if "last_name" in form.fields:
        form.fields["last_name"].help_text = "Ingresa tus apellidos."
    if "is_active" in form.fields:
        form.fields["is_active"].label = "Activa"
        form.fields["is_active"].help_text = _AYUDA_ACTIVA

    # El personal ve el detalle, pero no puede ascender cuentas.
    puede = bool(getattr(actor, "is_superuser", False))
    interruptores = (
        (
            "is_staff",
            "Personal del panel",
            "Puede entrar al panel y editar las páginas.",
            bool(getattr(instancia, "is_staff", False)),
        ),
        (
            "is_superuser",
            "Superusuario",
            "Tiene todos los permisos del panel, sin asignarlos uno a uno.",
            bool(getattr(instancia, "is_superuser", False)),
        ),
    )
    for nombre, etiqueta, ayuda, inicial in interruptores:
        form.fields[nombre] = forms.BooleanField(
            required=False,
            label=etiqueta,
            help_text=ayuda if puede else _AYUDA_SOLO_SUPER,
            initial=inicial,
            disabled=not puede,
        )
    form.order_fields([
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "password1",
        "password2",
    ])


def _validar_acceso(form, cleaned):
    if cleaned.get("is_superuser") and not cleaned.get("is_staff"):
        form.add_error(
            "is_staff",
            "Un superusuario también tiene que ser personal del panel para poder entrar.",
        )


def _validar_no_cerrarse_la_puerta(form, cleaned):
    actor = form.actor
    if not actor or not form.instance.pk or form.instance.pk != actor.pk:
        return
    if "is_active" in cleaned and not cleaned.get("is_active"):
        form.add_error("is_active", "No puedes desactivar tu propia cuenta.")
    if "is_staff" in form.fields and not cleaned.get("is_staff"):
        form.add_error("is_staff", "No puedes quitarte el acceso al panel.")
    if "is_superuser" in form.fields and not cleaned.get("is_superuser"):
        form.add_error("is_superuser", "No puedes quitarte el acceso de superusuario.")


class AltaCuentaForm(RegisterCustomForm):
    """Misma validación que el registro. La cuenta entra si queda activa."""

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

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        _preparar_campos(self, actor, instancia=None)

    def clean(self):
        cleaned = super().clean()
        _validar_acceso(self, cleaned)
        return cleaned


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

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        _preparar_campos(self, actor, instancia=self.instance)
        self.fields["password1"].label = "Nueva contraseña"
        self.fields["password1"].help_text = "Déjala en blanco para no cambiarla."
        self.fields["password2"].label = "Repetir contraseña"

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
        _validar_no_cerrarse_la_puerta(self, cleaned)
        _validar_acceso(self, cleaned)
        self._validar_clave_nueva(cleaned)
        return cleaned

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
            "nombre": nombre_visible(usuario),
            "email": usuario.email,
            "is_staff": usuario.is_staff,
            "is_active": usuario.is_active,
            "puede_editar": puede_editar_cuenta(request.user, usuario),
            "puede_cerrar": puede_cerrar_cuenta(request.user, usuario),
        })
    return _render(request, "admin/cuentas/lista.html", {
        "title": "Cuentas",
        "filas": filas,
        "es_superusuario": request.user.is_superuser,
    })


def nueva_cuenta(request):
    if request.method == "POST":
        form = AltaCuentaForm(request.POST, actor=request.user)
        if form.is_valid():
            usuario = form.save(commit=False)
            _aplicar_acceso(usuario, form, request.user, alta=True)
            _guardar_cuenta(usuario)
            messages.success(request, f"Cuenta {usuario.username} creada.")
            return redirect("admin:cuentas")
    else:
        form = AltaCuentaForm(actor=request.user)
    return _render(request, "admin/cuentas/formulario.html", {
        "title": "Nueva cuenta",
        "form": form,
        "volver": "admin:cuentas",
        "cuenta": None,
    })


def editar_cuenta(request, pk):
    cuenta = get_object_or_404(User, pk=pk)
    if not puede_editar_cuenta(request.user, cuenta):
        raise PermissionDenied
    if request.method == "POST":
        form = EdicionCuentaForm(request.POST, instance=cuenta, actor=request.user)
        if form.is_valid():
            usuario = form.save(commit=False)
            _aplicar_acceso(usuario, form, request.user, alta=False)
            _guardar_cuenta(usuario)
            if form.cleaned_data.get("password1") and usuario.pk == request.user.pk:
                update_session_auth_hash(request, usuario)
            messages.success(request, f"Cuenta {usuario.username} actualizada.")
            return redirect("admin:cuentas")
    else:
        form = EdicionCuentaForm(instance=cuenta, actor=request.user)
    return _render(request, "admin/cuentas/formulario.html", {
        "title": "Editar cuenta",
        "form": form,
        "volver": "admin:cuentas",
        "cuenta": cuenta,
        "puede_cerrar": puede_cerrar_cuenta(request.user, cuenta),
    })


def desactivar_cuenta(request, pk):
    return _confirmar_cierre(
        request,
        pk,
        titulo="Desactivar cuenta",
        boton="Desactivar cuenta",
        aviso=lambda cuenta: (
            f"Vas a desactivar la cuenta {_etiqueta(cuenta)}. "
            "No podrá entrar al sitio ni al panel. La cuenta no se borra "
            "y podrás activarla otra vez desde aquí."
        ),
        aplicar=lambda cuenta: _fijar_activa(cuenta, False),
        hecho=lambda cuenta: f"Cuenta {cuenta.username} desactivada. Ya no puede entrar.",
    )


def activar_cuenta(request, pk):
    return _confirmar_cierre(
        request,
        pk,
        titulo="Activar cuenta",
        boton="Activar cuenta",
        aviso=lambda cuenta: (
            f"Vas a activar la cuenta {_etiqueta(cuenta)}. "
            "Podrá entrar con su usuario y contraseña, sin el correo "
            "de activación del sitio público."
        ),
        aplicar=lambda cuenta: _fijar_activa(cuenta, True),
        hecho=lambda cuenta: f"Cuenta {cuenta.username} activada. Ya puede entrar.",
    )


def eliminar_cuenta(request, pk):
    cuenta = _cuenta_que_se_puede_cerrar(request, pk)
    consecuencias, protegidos = _consecuencias_de_borrar(cuenta)
    if request.method == "POST" and request.POST.get("confirmar") == "si":
        if protegidos:
            messages.error(
                request,
                f"No se pudo eliminar la cuenta {cuenta.username}. Sigue existiendo.",
            )
            return redirect("admin:cuentas")
        nombre = cuenta.username
        try:
            with transaction.atomic():
                cuenta.delete()
        except ProtectedError:
            messages.error(
                request,
                f"No se pudo eliminar la cuenta {nombre}. Sigue existiendo.",
            )
            return redirect("admin:cuentas")
        messages.success(request, f"Cuenta {nombre} eliminada.")
        return redirect("admin:cuentas")
    return _render(request, "admin/cuentas/confirmar.html", {
        "title": "Eliminar cuenta",
        "aviso": (
            f"Vas a eliminar la cuenta {_etiqueta(cuenta)}. "
            "No se puede deshacer."
        ),
        "boton": "Eliminar cuenta",
        "peligro": True,
        "volver": "admin:cuentas",
        "consecuencias": consecuencias,
        "protegidos": protegidos,
    })


def _confirmar_cierre(request, pk, *, titulo, boton, aviso, aplicar, hecho):
    cuenta = _cuenta_que_se_puede_cerrar(request, pk)
    if request.method == "POST" and request.POST.get("confirmar") == "si":
        nombre = cuenta.username
        try:
            with transaction.atomic():
                aplicar(cuenta)
        except ProtectedError:
            messages.error(
                request,
                f"No se pudo completar la acción sobre {nombre}. La cuenta sigue igual.",
            )
            return redirect("admin:cuentas")
        messages.success(request, hecho(cuenta))
        return redirect("admin:cuentas")
    return _render(request, "admin/cuentas/confirmar.html", {
        "title": titulo,
        "aviso": aviso(cuenta),
        "boton": boton,
        "peligro": False,
        "volver": "admin:cuentas",
        "consecuencias": [],
        "protegidos": [],
    })


def _cuenta_que_se_puede_cerrar(request, pk):
    cuenta = get_object_or_404(User, pk=pk)
    if not puede_cerrar_cuenta(request.user, cuenta):
        raise PermissionDenied
    return cuenta


def _aplicar_acceso(usuario, form, actor, *, alta):
    """Solo un superusuario cambia personal y superusuario. El alta no se asciende sola."""
    if actor.is_superuser:
        usuario.is_staff = bool(form.cleaned_data.get("is_staff"))
        usuario.is_superuser = bool(form.cleaned_data.get("is_superuser"))
        return
    if alta:
        usuario.is_staff = False
        usuario.is_superuser = False


def _guardar_cuenta(usuario):
    """Guarda la cuenta y la marca de suspensión juntas. Si falla, no queda a medias."""
    with transaction.atomic():
        usuario.save()
        marcar_suspension(usuario, not usuario.is_active)


def _fijar_activa(cuenta, activa):
    cuenta.is_active = activa
    cuenta.save(update_fields=["is_active"])
    marcar_suspension(cuenta, not activa)


def _etiqueta(cuenta):
    detalle = nombre_visible(cuenta)
    if cuenta.email:
        detalle = f"{detalle}, {cuenta.email}".strip(", ")
    if detalle:
        return f"{cuenta.username} ({detalle})"
    return cuenta.username


def _consecuencias_de_borrar(cuenta):
    """Qué más se iría con la cuenta, y qué lo impide."""
    collector = NestedObjects(using=router.db_for_write(cuenta.__class__))
    collector.collect([cuenta])
    lineas = []
    for modelo, objetos in collector.model_objs.items():
        if modelo._meta.label_lower == "auth.user":
            continue
        texto = _RELACIONES.get(modelo._meta.label_lower)
        if texto is None:
            texto = str(modelo._meta.verbose_name_plural).capitalize()
        lineas.append(f"{texto} ({len(objetos)})")
    protegidos = [
        f"{obj._meta.verbose_name}: {obj}" for obj in collector.protected
    ]
    return lineas, protegidos


def _render(request, plantilla, contexto):
    datos = admin.site.each_context(request)
    datos.update(contexto)
    return render(request, plantilla, datos)
