from django import forms
from .models import Solicitud_Gasto, Articulo_Gasto, Entrada_Gasto_Ajuste, Conceptos_Entradas
from tesoreria.models import Pago

class Solicitud_GastoForm(forms.ModelForm):
    class Meta:
        model = Solicitud_Gasto
        fields = ['proyecto','subproyecto','superintendente','colaborador','tipo']

class Articulo_GastoForm(forms.ModelForm):

    class Meta:
        model = Articulo_Gasto
        fields = ['producto','comentario','cantidad','precio_unitario','factura_pdf','factura_xml','otros_impuestos','impuestos_retenidos']

class Articulo_GastoForm2(forms.ModelForm):

    class Meta:
        model = Articulo_Gasto
        fields = ['producto','factura_xml','comentario']


class Articulo_Gasto_Edit_Form(forms.ModelForm):
    class Meta:
        model = Articulo_Gasto
        fields = ['cantidad','precio_unitario','otros_impuestos','impuestos_retenidos']


class Pago_Gasto_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','cuenta']

class Articulo_Gasto_Factura_Form(forms.ModelForm):

    class Meta:
        model = Articulo_Gasto
        fields = ['factura_pdf','factura_xml']

class Entrada_Gasto_AjusteForm(forms.ModelForm):
    
    class Meta:
        model = Entrada_Gasto_Ajuste
        fields = ['comentario']

class Conceptos_EntradasForm(forms.ModelForm):

    class Meta:
        model = Conceptos_Entradas
        fields =['concepto_material','cantidad','precio_unitario','comentario']