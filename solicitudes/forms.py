from django import forms
from solicitudes.models import Subproyecto, Proyecto, Operacion, Sector
from dashboard.models import Inventario, Order, Product, ArticulosOrdenados, Plantilla, ArticuloPlantilla, Activo
from gastos.models import Entrada_Gasto_Ajuste, Conceptos_Entradas 
from user.models import Profile

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto','cantidad', 'price','comentario']

    def __init__(self, *args, **kwargs):

        # Recibir el distrito como un argumento adicional del formulario
        distrito = kwargs.pop('distrito', None)

        super(InventarioForm, self).__init__(*args, **kwargs)
        
        # Get a 'value list' of products already in the inventario model
        existing = Inventario.objects.filter(distrito=distrito).values_list('producto')
        #existing = Inventario.objects.all().values_list('producto')

        # Override the product query set with a list of product excluding those already in the pricelist
        self.fields['producto'].queryset = Product.objects.exclude(id__in=existing)

class ArticulosOrdenadosForm(forms.ModelForm):

    class Meta:
        model = ArticulosOrdenados
        fields = ['cantidad']

class ArticulosOrdenadosComentForm(forms.ModelForm):

    class Meta:
        model = ArticulosOrdenados
        fields = ['comentario']

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['proyecto','subproyecto', 'operacion','sector','activo','superintendente','supervisor','comentario','soporte']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.none()
        self.fields['subproyecto'].queryset = Subproyecto.objects.none()
        self.fields['sector'].queryset = Sector.objects.none()
        self.fields['operacion'].queryset = Operacion.objects.none()
        self.fields['activo'].queryset = Activo.objects.none()
        self.fields['superintendente'].queryset = Profile.objects.none()
        self.fields['supervisor'].queryset = Profile.objects.none()

        if 'proyecto' in self.data:
            try:
                seleccion_actual = int(self.data.get('proyecto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['subproyecto'].queryset = Subproyecto.objects.filter(proyecto= seleccion_actual)  
                self.fields['proyecto'].queryset = Proyecto.objects.filter(id= seleccion_actual)
                        
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
      
        if 'sector' in self.data:
            try:
                seleccion_actual = int(self.data.get('sector'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['sector'].queryset = Sector.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'operacion' in self.data:
            try:
                seleccion_actual = int(self.data.get('operacion'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['operacion'].queryset = Operacion.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'activo' in self.data:
            try:
                seleccion_actual = int(self.data.get('activo'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['activo'].queryset = Activo.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'superintendente' in self.data:
            try:
                seleccion_actual = int(self.data.get('superintendente'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['superintendente'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'supervisor' in self.data:
            try:
                seleccion_actual = int(self.data.get('supervisor'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['supervisor'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        
class Order_Resurtimiento_Form(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['proyecto','subproyecto','superintendente']

class Inv_UpdateForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['price','cantidad','minimo','ubicacion','estante','comentario']

class Inv_UpdateForm_almacenista(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['ubicacion','estante','minimo','comentario']

class Entrada_Gasto_AjusteForm(forms.ModelForm):
    class Meta:
        model = Entrada_Gasto_Ajuste
        fields = ['comentario']

class Conceptos_EntradasForm(forms.ModelForm):
    class Meta:
        model = Conceptos_Entradas
        fields = ['concepto_material','cantidad', 'precio_unitario']

class Plantilla_Form(forms.ModelForm):
    class Meta:
        model = Plantilla
        fields = ['nombre','descripcion','comentario']

class ArticuloPlantilla_Form(forms.ModelForm):
    class Meta:
        model = ArticuloPlantilla
        fields = ['producto','cantidad','comentario_articulo','comentario_plantilla']
