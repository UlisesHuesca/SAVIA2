from django import forms
from .models import Compra, ArticuloComprado, Comparativo, Item_Comparativo
from requisiciones.models import ArticulosRequisitados

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['id','proveedor','cond_de_pago','uso_del_cfdi','dias_de_credito','deposito_comprador','anticipo',
                  'monto_anticipo','dias_de_entrega','impuesto','impuestos_adicionales','flete','costo_fletes',
                  'tesoreria_matriz','opciones_condiciones','moneda','tipo_de_cambio','logistica', 'referencia','comparativo_model']

class ArticuloCompradoForm(forms.ModelForm):
    class Meta:
        model = ArticuloComprado
        fields = ['producto','cantidad','precio_unitario']

class ArticulosRequisitadosForm(forms.ModelForm):

    class Meta:
        model = ArticulosRequisitados
        fields = ['producto','cantidad']

class ComparativoForm(forms.ModelForm):
    class Meta:
        model = Comparativo
        fields = ['nombre','comentarios']

class Item_ComparativoForm(forms.ModelForm):
    class Meta:
        model = Item_Comparativo
        fields = ['producto','proveedor','modelo','marca','cantidad', 'precio', 'proveedor2', 'modelo2', 'marca2', 
                  'precio2','proveedor3','modelo3','marca3','precio3']

