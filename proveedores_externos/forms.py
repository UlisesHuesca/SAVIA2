from django import forms
from compras.models import Proveedor



class CSFForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['csf']