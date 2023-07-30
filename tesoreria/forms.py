from django import forms
from .models import Pago, Facturas
from compras.models import Compra
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico


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

class Facturas_Gastos_Form(forms.ModelForm):
    class Meta:
        model = Solicitud_Gasto
        fields = ['facturas_completas']

class Facturas_Viaticos_Form(forms.ModelForm):
    class Meta:
        model = Solicitud_Viatico
        fields = ['facturas_completas']

class Saldo_Form(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['saldo_a_favor']