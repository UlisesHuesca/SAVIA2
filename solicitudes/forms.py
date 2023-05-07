from django import forms
from solicitudes.models import Subproyecto, Proyecto
from dashboard.models import Inventario, Order, Product, ArticulosOrdenados

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto','cantidad', 'price','comentario']

    def __init__(self, *args, **kwargs):

        #item_creado = Inventario.objects.get(complete=False)


        super(InventarioForm, self).__init__(*args, **kwargs)
        #distrito = kwargs.pop('distrito')
        # Get a 'value list' of products already in the inventario model
        #existing = Inventario.objects.filter(distrito=item_creado.distrito).values_list('producto')
        existing = Inventario.objects.all().values_list('producto')

        # Override the product query set with a list of product excluding those already in the pricelist
        self.fields['producto'].queryset = Product.objects.exclude(id__in=existing)

class ArticulosOrdenadosForm(forms.ModelForm):

    class Meta:
        model = ArticulosOrdenados
        fields = ['cantidad']

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['proyecto','subproyecto', 'area','superintendente','supervisor']

class Inv_UpdateForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['price','cantidad','minimo','ubicacion','estante','comentario']

class Inv_UpdateForm_almacenista(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['ubicacion','estante','minimo','comentario']