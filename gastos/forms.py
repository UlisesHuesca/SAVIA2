from django import forms
from .models import Solicitud_Gasto, Articulo_Gasto, Entrada_Gasto_Ajuste, Conceptos_Entradas, Factura, Tipo_Gasto
from solicitudes.models import Subproyecto, Proyecto, Operacion, Sector
from user.models import Profile, Distrito
from dashboard.models import Inventario, Order, Product
from compras.models import Proveedor_direcciones
from tesoreria.models import Pago, Cuenta

class Solicitud_GastoForm(forms.ModelForm):
    class Meta:
        model = Solicitud_Gasto
        fields = ['superintendente','colaborador','tipo','proveedor','distrito']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['colaborador'].queryset = Profile.objects.none()
        self.fields['superintendente'].queryset = Profile.objects.none()
        self.fields['proveedor'].queryset = Proveedor_direcciones.objects.none()
        self.fields['distrito'].queryset = Distrito.objects.none()
        self.fields['tipo'].queryset = Tipo_Gasto.objects.none()

        if 'superintendente' in self.data:
            try:
                seleccion_actual = int(self.data.get('superintendente'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['superintendente'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'colaborador' in self.data:
            try:
                seleccion_actual = int(self.data.get('colaborador'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['colaborador'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'proveedor' in self.data:
            try:
                seleccion_actual = int(self.data.get('proveedor'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['proveedor'].queryset = Proveedor_direcciones.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'tipo' in self.data:
            try:
                seleccion_actual = int(self.data.get('tipo'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['tipo'].queryset = Tipo_Gasto.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'distrito' in self.data:
            try:
                seleccion_actual = int(self.data.get('distrito'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['distrito'].queryset = Distrito.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

        self.fields['distrito'].required = False

class Articulo_GastoForm(forms.ModelForm):

    class Meta:
        model = Articulo_Gasto
        fields = ['producto','comentario','proyecto','subproyecto','cantidad','precio_unitario','otros_impuestos','impuestos_retenidos', 'iva']
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.none()
        self.fields['subproyecto'].queryset = Subproyecto.objects.none()
        self.fields['producto'].queryset = Product.objects.none()

        if 'proyecto' in self.data:
            try:
                seleccion_actual = int(self.data.get('proyecto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['subproyecto'].queryset = Subproyecto.objects.filter(proyecto= seleccion_actual)  
                self.fields['proyecto'].queryset = Proyecto.objects.filter(id= seleccion_actual)
                        
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'producto' in self.data:
            try:
                seleccion_actual = int(self.data.get('producto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['producto'].queryset = Product.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida


class Articulo_GastoForm2(forms.ModelForm):

    class Meta:
        model = Articulo_Gasto
        fields = ['producto','comentario']


class Articulo_Gasto_Edit_Form(forms.ModelForm):
    class Meta:
        model = Articulo_Gasto
        fields = ['cantidad','precio_unitario','otros_impuestos','impuestos_retenidos']


class Pago_Gasto_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','cuenta','pagado_real','pagado_hora']

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

#class Articulo_Gasto_Factura_Form(forms.ModelForm):

#    class Meta:
#        model = Articulo_Gasto
#        fields = ['factura_pdf','factura_xml']

class Entrada_Gasto_AjusteForm(forms.ModelForm):
    
    class Meta:
        model = Entrada_Gasto_Ajuste
        fields = ['comentario']

class Conceptos_EntradasForm(forms.ModelForm):

    class Meta:
        model = Conceptos_Entradas
        fields =['concepto_material','cantidad','precio_unitario','comentario']
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concepto_material'].queryset = Inventario.objects.none()

        if 'concepto_material' in self.data:
            try:
                seleccion_actual = int(self.data.get('concepto_material'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['concepto_material'].queryset = Inventario.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida


class FacturaForm(forms.ModelForm):

     class Meta:
        model = Factura
        fields =['archivo_pdf','archivo_xml','monto']

class UploadFileForm(forms.Form):
    archivo_pdf = forms.FileField(required=False) 
    archivo_xml = forms.FileField(required=False) 


class Autorizacion_Gasto_Form(forms.ModelForm):
    class Meta:
        model = Solicitud_Gasto
        fields = ['comentario']