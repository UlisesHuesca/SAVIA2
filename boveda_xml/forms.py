from django import forms
from django.core.validators import FileExtensionValidator

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            'widget',
            MultipleFileInput(),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpieza_individual = super().clean

        if isinstance(data, (list, tuple)):
            return [
                limpieza_individual(archivo, initial)
                for archivo in data
            ]

        return [
            limpieza_individual(data, initial)
        ]


class CargaMasivaXMLForm(forms.Form):

    archivos_xml = MultipleFileField(
        label='Seleccione archivos XML o ZIP',
        help_text=(
            'Puede seleccionar varios archivos XML o ZIP '
            'al mismo tiempo.'
        ),
        validators=[
            FileExtensionValidator(
                allowed_extensions=['xml', 'zip']
            )
        ],
        error_messages={
            'required': (
                'Debe seleccionar al menos un archivo XML o ZIP.'
            ),
        },
        widget=MultipleFileInput(
            attrs={
                'accept': '.xml,.zip',
                'class': 'form-control',
            }
        ),
    )