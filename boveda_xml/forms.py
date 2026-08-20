from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpieza_individual = super().clean

        if isinstance(data, (list, tuple)):
            return [
                limpieza_individual(archivo, initial)
                for archivo in data
            ]

        return [limpieza_individual(data, initial)]


class CargaMasivaXMLForm(forms.Form):

    archivos_xml = MultipleFileField(
        label='Seleccione los archivos XML',
        help_text='Puede seleccionar varios archivos al mismo tiempo.',
        widget=MultipleFileInput(
            attrs={
                'accept': '.xml,text/xml,application/xml',
                'class': 'form-control',
            }
        ),
    )

    def clean_archivos_xml(self):
        archivos = self.cleaned_data['archivos_xml']

        if not archivos:
            raise forms.ValidationError(
                'Debe seleccionar al menos un archivo XML.'
            )

        for archivo in archivos:
            if not archivo.name.lower().endswith('.xml'):
                raise forms.ValidationError(
                    f'El archivo {archivo.name} no tiene extensión XML.'
                )

        return archivos