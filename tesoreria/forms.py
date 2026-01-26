from django import forms
from .models import Pago, Facturas, Cuenta
from compras.models import Compra
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico
from tesoreria.models import Comprobante_saldo_favor, Saldo_Cuenta

class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','tipo_de_cambio','cuenta','pagado_real','pagado_hora']
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cuenta'].queryset = Cuenta.objects.none()

        if 'cuenta' in self.data:
            try:
                seleccion_actual = int(self.data.get('cuenta'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['cuenta'].queryset = Cuenta.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

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
        model = Comprobante_saldo_favor
        fields = ['comprobante_pdf','comprobante_xml','comentario']

class CompraSaldo_Form(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['saldo_a_favor']

class ComprobanteForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['comprobante_pago']


class TxtForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','cuenta']
    

class Cargo_Abono_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','cuenta','pagado_real', 'comentario', 'comprobante_pago']
        #fields = ['monto','cuenta','pagado_real','comprobante_pago','tipo_de_cambio',] los fields del pago normal
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cuenta'].queryset = Cuenta.objects.none()

        if 'cuenta' in self.data:
            try:
                seleccion_actual = int(self.data.get('cuenta'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['cuenta'].queryset = Cuenta.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida   #def __init__(self,*args, **kwargs):

class Cargo_Abono_Tipo_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','pagado_real', 'tipo', 'comentario','comprobante_pago','empresa_beneficiario','distrito',]
        #fields = ['monto','cuenta','pagado_real','comprobante_pago','tipo_de_cambio',] los fields del pago normal
    
class Cargo_Abono_No_Documento_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','pagado_real', 'tipo', 'comentario','empresa_beneficiario','distrito']
        #fields = ['monto','cuenta','pagado_real','comprobante_pago','tipo_de_cambio',] los fields del pago normal   

class Saldo_Inicial_Form(forms.ModelForm):
    class Meta:
        model = Saldo_Cuenta
        fields = ['monto_inicial','comentario','fecha_inicial'] #Quito cuenta porque estaría relacionada con el pk de la cuenta que estamos viendo
    

class Transferencia_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['cuenta']

class UploadFileForm(forms.Form):
    factura_pdf = forms.FileField(required=False)
    factura_xml = forms.FileField(required=False)

class UploadComplementoForm(forms.Form):
    complemento_pdf = forms.FileField(required=False)
    complemento_xml = forms.FileField(required=False)