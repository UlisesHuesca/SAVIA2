from django import forms
from .models import Exhibit

class ExhibitForm(forms.ModelForm):
    class Meta:
        model = Exhibit
        fields = [
            'tipo',
            'proveedor',
            'solicitud',
            'id_detalle',
            'monto',
            'concepto_flujo',
            'descripcion',
            'observaciones',
            'nombre_proveedor',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
            'monto': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        proveedor = cleaned_data.get("proveedor")

        if tipo == "PROVEEDOR" and not proveedor:
            self.add_error("proveedor", "Debes seleccionar un proveedor si el tipo es PROVEEDOR.")