from django import forms
from .models import Product, Subfamilia, Products_Batch, Inventario_Batch
from compras.models import Proveedor_Batch, Proveedor, Proveedor_direcciones, Proveedor_Direcciones_Batch
from user.models import Distrito
from solicitudes.models import Proyecto, Subproyecto
from user.models import Profile


class Profile_Form(forms.Form):
    profile = forms.ModelChoiceField(
        queryset=Profile.objects.none(),  # Inicialmente, no se mostrarán perfiles
        label='Selecciona tu perfil',
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['familia','subfamilia','unidad','especialista','iva','activo','servicio','baja_item','image','gasto']


    #Sobreescribiendo el método __init__ y configurando el queryset para que esté vacío
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subfamilia'].queryset = Subfamilia.objects.none()

        if 'familia' in self.data:
            try:
                familia_id = int(self.data.get('familia'))
                self.fields['subfamilia'].queryset = Subfamilia.objects.filter(familia_id=familia_id).order_by('nombre')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            self.fields['subfamilia'].queryset = self.instance.familia.subfamilia_set.order_by('nombre')


class PrecioRef_Form(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['precioref', 'porcentaje']

class ProveedoresForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['razon_social','rfc','nombre_comercial','familia']

class DireccionComparativoForm(forms.ModelForm):
   
    class Meta:
        model = Proveedor_direcciones
        fields = ['email']

class ProveedoresDireccionesForm(forms.ModelForm):
    class Meta:
        model = Proveedor_direcciones
        fields = ['estado','telefono','distrito','domicilio','contacto','email','email_opt','banco','swift','clabe','cuenta','financiamiento','dias_credito','estatus']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['distrito'].queryset = Distrito.objects.exclude(id__in=[7, 8])

class ProveedoresExistDireccionesForm(forms.ModelForm):
   
    class Meta:
        model = Proveedor_direcciones
        fields = ['nombre','domicilio','estado','contacto','telefono','email','email_opt','banco','clabe','cuenta','financiamiento','dias_credito']


class Add_ProveedoresDireccionesForm(forms.ModelForm):
    class Meta:
        model = Proveedor_direcciones
        fields = ['domicilio','estado','distrito','contacto','telefono','email','email_opt','banco','swift','clabe','cuenta','financiamiento','dias_credito','estatus']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['distrito'].queryset = Distrito.objects.exclude(id__in=[7, 8])

        
class Products_BatchForm(forms.ModelForm):
    class Meta:
        model = Products_Batch
        fields= ['file_name']

class Inventario_BatchForm(forms.ModelForm):
    class Meta:
        model = Inventario_Batch
        fields= ['file_name']

class Proveedores_BatchForm(forms.ModelForm):
    class Meta:
        model = Proveedor_Batch
        fields= ['file_name']

class Proveedores_Direcciones_BatchForm(forms.ModelForm):
    class Meta:
        model = Proveedor_Direcciones_Batch
        fields= ['file_name']

class AddProduct_Form(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['codigo','nombre','unidad','familia','subfamilia','especialista','iva','activo','servicio','image','gasto']

#Sobreescribiendo el método __init__ y configurando el queryset para que esté vacío
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subfamilia'].queryset = Subfamilia.objects.none()

        if 'familia' in self.data:
            try:
                familia_id = int(self.data.get('familia'))
                self.fields['subfamilia'].queryset = Subfamilia.objects.filter(familia_id=familia_id).order_by('nombre')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            self.fields['subfamilia'].queryset = self.instance.familia.subfamilia_set.order_by('nombre')

class Proyectos_Form(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['descripcion','nombre','cliente','activo','factura','fecha_factura','folio_cotizacion','oc_cliente','status_de_entrega',]

class Proyectos_Add_Form(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['descripcion','nombre','cliente','factura','fecha_factura','folio_cotizacion','oc_cliente','status_de_entrega',]

class Subproyectos_Add_Form(forms.ModelForm):
    class Meta:
        model = Subproyecto
        fields = ['nombre','descripcion','presupuesto','status']