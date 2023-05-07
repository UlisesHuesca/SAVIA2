from django import forms
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura
from tesoreria.models import Pago


class Solicitud_ViaticoForm(forms.ModelForm):
    class Meta:
        model = Solicitud_Viatico
        fields = ['proyecto','subproyecto','superintendente','fecha_partida','fecha_retorno','colaborador','lugar_partida','lugar_comision','hospedaje','transporte','comentario']

class Concepto_ViaticoForm(forms.ModelForm):

    class Meta:
        model = Concepto_Viatico
        fields = ['producto','comentario','cantidad','precio','rendimiento','viatico']

class Pago_Viatico_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','cuenta']

class Viaticos_Factura_Form(forms.ModelForm):
    class Meta:
        model = Viaticos_Factura
        fields = ['factura_pdf','factura_xml','comentario']

