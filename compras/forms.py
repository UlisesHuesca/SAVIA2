from django import forms
from .models import Compra, ArticuloComprado, Comparativo, Item_Comparativo, Proveedor_direcciones, Proveedor
from dashboard.models import Product, Inventario
from requisiciones.models import ArticulosRequisitados, Requis



class UploadFileForm(forms.Form):
    file = forms.FileField()


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor','cond_de_pago','uso_del_cfdi','dias_de_credito','tesorero',
                  'monto_anticipo','dias_de_entrega','impuestos','costo_fletes', 'retencion','comentario_solicitud',
                  'opciones_condiciones','moneda','tipo_de_cambio','logistica', 'referencia','comparativo_model','local']
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor_direcciones.objects.none()
        self.fields['comparativo_model'].queryset = Comparativo.objects.none()
        if 'proveedor' in self.data:
            try:
                seleccion_actual = int(self.data.get('proveedor'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['proveedor'].queryset = Proveedor_direcciones.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'comparativo_model' in self.data:
            try:
                seleccion_actual = int(self.data.get('comparativo_model'))
                self.fields['comparativo_model'].queryset = Comparativo.objects.filter(id = seleccion_actual)
            except (ValueError, TypeError):
                pass #Manejo de errores en caso de entrada no válida

class ArticuloCompradoForm(forms.ModelForm):
    class Meta:
        model = ArticuloComprado
        fields = ['producto','cantidad','precio_unitario']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['producto'].queryset = ArticulosRequisitados.objects.none() 

class ArticulosRequisitadosForm(forms.ModelForm):

    class Meta:
        model = ArticulosRequisitados
        fields = ['producto','cantidad']

class ComparativoForm(forms.ModelForm):
    class Meta:
        model = Comparativo
        fields = ['nombre','comentarios','proveedor', 'proveedor2','proveedor3', 'cotizacion','cotizacion2','cotizacion3']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.none()
        self.fields['proveedor2'].queryset = Proveedor.objects.none()
        self.fields['proveedor3'].queryset = Proveedor.objects.none()
        if 'proveedor' in self.data:
            try:
                seleccion_actual = int(self.data.get('proveedor'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['proveedor'].queryset = Proveedor.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'proveedor2' in self.data:
            try:
                seleccion_actual = int(self.data.get('proveedor2'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['proveedor2'].queryset = Proveedor.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'proveedor3' in self.data:
            try:
                seleccion_actual = int(self.data.get('proveedor3'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['proveedor3'].queryset = Proveedor.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

class Item_ComparativoForm(forms.ModelForm):
    class Meta:
        model = Item_Comparativo
        fields = ['producto','modelo','marca','cantidad', 'precio','dias_de_entrega', 'modelo2', 'marca2','dias_de_entrega2', 
                  'precio2','modelo3','marca3','precio3','dias_de_entrega3',]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Inventario.objects.none()
        if 'producto' in self.data:
            try:
                seleccion_actual = int(self.data.get('producto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['producto'].queryset = Inventario.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
    


class Compra_ComentarioForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['comentarios']

class Compra_ComentarioGerForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['comentario_gerencia']

class RequisDevolucionForm(forms.ModelForm):
    class Meta:
        model = Requis
        fields = ["comentario_devolucion"]
        widgets = {
            "comentario_devolucion": forms.Textarea(attrs={"rows":2}),
        }
