from django import forms
from .models import Entrada, EntradaArticulo, Reporte_Calidad

class EntradaArticuloForm(forms.ModelForm):
    class Meta:
        model = EntradaArticulo
        fields = ['cantidad']

class Reporte_CalidadForm(forms.ModelForm):
    class Meta:
        model = Reporte_Calidad
        fields = ['cantidad','comentarios','autorizado']


