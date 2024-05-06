from django import forms
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo
from compras.models import ArticuloComprado

class EntradaArticuloForm(forms.ModelForm):
    class Meta:
        model = EntradaArticulo
        fields = ['cantidad','referencia']

class Reporte_CalidadForm(forms.ModelForm):
    class Meta:
        model = Reporte_Calidad
        fields = ['cantidad','comentarios','image','autorizado']

class NoConformidadForm(forms.ModelForm):
    class Meta:
        model = No_Conformidad
        fields = ['comentario','tipo_nc']

class NC_ArticuloForm(forms.ModelForm):
    class Meta:
        model = NC_Articulo
        fields = ['articulo_comprado','cantidad']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['articulo_comprado'].queryset = ArticuloComprado.objects.none()
        if 'articulo_comprado' in self.data:
            try:
                seleccion_actual = int(self.data.get('producto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['articulo_comprado'].queryset = ArticuloComprado.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida


