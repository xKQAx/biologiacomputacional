from django import forms
from django.contrib.auth import get_user_model

from contacto.models import MensajeContacto


class SeguimientoMensajeForm(forms.Form):
    """Estado y responsable que el equipo puede actualizar desde la bandeja."""

    estado = forms.ChoiceField(
        label='Estado', choices=MensajeContacto.Estado.choices,
    )
    asignado_a = forms.ModelChoiceField(
        label='Responsable',
        queryset=get_user_model().objects.none(),
        required=False,
        empty_label='Sin asignar',
    )

    def __init__(self, *args, mensaje=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asignado_a'].queryset = get_user_model().objects.filter(
            is_staff=True,
            is_active=True,
        ).order_by('username')
        if mensaje is not None and not self.is_bound:
            self.initial.setdefault('estado', mensaje.estado)
            self.initial.setdefault('asignado_a', mensaje.asignado_a_id)
