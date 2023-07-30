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
        fields = ['nombre','comentarios','proveedor', 'proveedor2','proveedor3','cotizacion','cotizacion2', 'cotizacion3']

class Item_ComparativoForm(forms.ModelForm):
    class Meta:
        model = Item_Comparativo
        fields = ['producto','modelo','marca','cantidad', 'precio','dias_de_entrega', 'modelo2', 'marca2','dias_de_entrega2', 
                  'precio2','modelo3','marca3','precio3','dias_de_entrega3',]

class Compra_ComentarioForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['comentarios']