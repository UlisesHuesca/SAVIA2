from django import forms
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo

class EntradaArticuloForm(forms.ModelForm):
    class Meta:
        model = EntradaArticulo
        fields = ['cantidad','referencia']

class Reporte_CalidadForm(forms.ModelForm):
    class Meta:
        model = Reporte_Calidad
        fields = ['cantidad','comentarios','autorizado']

class NoConformidadForm(forms.ModelForm):
    class Meta:
        model = No_Conformidad
        fields = ['comentario']

class NC_ArticuloForm(forms.ModelForm):
    class Meta:
        model = NC_Articulo
        fields = ['articulo_comprado','cantidad']


