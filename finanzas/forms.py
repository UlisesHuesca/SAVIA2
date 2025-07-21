from django import forms
from .models import Linea_Exhibit

class Linea_Exhibit_Form(forms.ModelForm):
    class Meta:
        model = Linea_Exhibit
        fields = [
            'tipo',
            'tipo_pago_exhibit',
            'proveedor',
            'monto',
            'descripcion',
            'observaciones',
            'tipo_proveedor',
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