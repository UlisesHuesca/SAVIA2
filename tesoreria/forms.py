from django import forms
from .models import Pago, Facturas, Cuenta
from compras.models import Compra
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','tipo_de_cambio','cuenta','pagado_real']
    
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
    
    #def __init__(self,*args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.fields['cuenta'].queryset = Cuenta.objects.none()

        #if 'cuenta' in self.data:
        #    try:
        #        seleccion_actual = int(self.data.get('cuenta'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
        #        self.fields['cuenta'].queryset = Cuenta.objects.filter(id= seleccion_actual)
        #    except (ValueError, TypeError):
        #        pass  # Manejo de errores en caso de entrada no válida