from django import forms
from .models import Product, Subfamilia, Products_Batch, Inventario_Batch, Requerimiento_Calidad
from compras.models import Proveedor_Batch, Proveedor, Proveedor_direcciones, Proveedor_Direcciones_Batch, DocumentosProveedor
from user.models import Distrito
from solicitudes.models import Proyecto, Subproyecto, Contrato
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
        fields = ['familia','subfamilia','unidad','iva','activo','servicio','baja_item','image','gasto']


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

class ProductCalidadForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['rev_calidad']

class RequerimientoCalidadForm(forms.ModelForm):
    class Meta:
        model = Requerimiento_Calidad
        fields = ['nombre', 'url']


class PrecioRef_Form(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['precioref', 'porcentaje']

class ProveedoresForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['razon_social','rfc','familia','extranjero','visita']

class DireccionComparativoForm(forms.ModelForm):
   
    class Meta:
        model = Proveedor_direcciones
        fields = ['email']

class ProveedoresDireccionesForm(forms.ModelForm):
    class Meta:
        model = Proveedor_direcciones
        fields = ['estado','telefono','distrito','domicilio','contacto','email','email_opt','banco','swift','spid','clabe','cuenta','financiamiento','dias_credito','estatus','producto','servicio','arrendamiento','moneda','modificado_fecha','referencia','convenio',]

    def __init__(self, *args, **kwargs):
        
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if profile and profile.tipo.nombre == "Subdirector_Alt":
            self.fields['distrito'].queryset = Distrito.objects.all()
        else:
            self.fields['distrito'].queryset = Distrito.objects.exclude(id__in=[7, 8])

class ProveedoresExistDireccionesForm(forms.ModelForm):
   
    class Meta:
        model = Proveedor_direcciones
        fields = ['nombre','domicilio','estado','contacto','telefono','email','email_opt','banco','clabe','cuenta','financiamiento','dias_credito']


class Add_ProveedoresDireccionesForm(forms.ModelForm):
    class Meta:
        model = Proveedor_direcciones
        fields = ['domicilio','estado','distrito','contacto','telefono','email','email_opt','banco','swift','spid','clabe','cuenta','financiamiento','dias_credito','estatus','producto','servicio','arrendamiento','referencia','convenio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['distrito'].queryset = Distrito.objects.exclude(id__in=[7, 8])

class Add_ProveedoresDir_Alt_Form(forms.ModelForm):
    class Meta:
        model = Proveedor_direcciones
        fields = ['domicilio','estado','distrito','contacto','telefono','email','email_opt','banco','swift','spid','clabe','cuenta','financiamiento','dias_credito','estatus','producto','servicio','arrendamiento','referencia','convenio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['distrito'].queryset = Distrito.objects.filter(id__in=[8])


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
        fields = ['codigo','nombre','unidad','familia','subfamilia','iva','activo','critico','servicio','baja_item','image','gasto']

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

class Contrato_form(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['nombre', 'descripcion',]

class Proyectos_Form(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['descripcion','nombre','status_de_entrega','contrato'] #Se retiran campos 'cliente','factura','fecha_factura','folio_cotizacion','oc_cliente','activo',


class Proyectos_Add_Form(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['descripcion','nombre','status_de_entrega','contrato'] #'cliente','factura','fecha_factura','folio_cotizacion','oc_cliente',

class Subproyectos_Add_Form(forms.ModelForm):
    class Meta:
        model = Subproyecto
        fields = ['nombre','descripcion','presupuesto','status']

class Add_Product_CriticoForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),  # Dejamos el queryset vacío por defecto
        label="Seleccionar Producto",
        widget=forms.Select(attrs={'class': 'select2'})
    )

    class Meta:
        fields = ['product']


class Comentario_Proveedor_Doc_Form(forms.ModelForm):
    class Meta:
        model = DocumentosProveedor
        fields = ['comentario']