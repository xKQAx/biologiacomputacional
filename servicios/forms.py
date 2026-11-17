"""Formularios propios para las fichas de herramientas y bases de datos."""

from django import forms

from BiologiaComputacional.forms import ServicioForm as FormularioBaseServicio


class ServicioForm(FormularioBaseServicio):
    class Meta(FormularioBaseServicio.Meta):
        fields = FormularioBaseServicio.Meta.fields + [
            'version',
            'compatibilidad',
            'requisitos',
            'instrucciones',
            'documentacion_url',
            'citacion',
            'fecha_actualizacion',
        ]
        widgets = {
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'compatibilidad': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requisitos': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'instrucciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'documentacion_url': forms.URLInput(attrs={'class': 'form-control'}),
            'citacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fecha_actualizacion': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_actualizacion'].input_formats = ['%Y-%m-%d']
