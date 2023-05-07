from django import forms
from .models import Pago, Facturas
from compras.models import Compra

class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','tipo_de_cambio','cuenta']

class Facturas_Form(forms.ModelForm):
    class Meta:
        model = Facturas
        fields = ['factura_pdf','factura_xml','comentario']

class Facturas_Completas_Form(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['facturas_completas']