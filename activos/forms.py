from django import forms
from dashboard.models import Activo, Marca, Tipo_Activo, Profile 
from requisiciones.models import Salidas
from compras.models import Proveedor_direcciones
from django.core.validators import FileExtensionValidator
#from bootstrap_datepicker_plus.widgets import DatePickerInput
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','tipo_activo','descripcion','eco_unidad','serie','marca','modelo','comentario','cuenta_contable','factura_interna','factura_pdf','factura_xml','responsable','fecha_asignacion']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Profile.objects.none()
        #self.fields['marca'].queryset = Marca.objects.none()
        if 'responsable' in self.data:
            try:
                seleccion_actual = int(self.data.get('responsable'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['responsable'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida



class DocumentosActivoForm(forms.ModelForm):
    factura_pdf = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['pdf'])],
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': '.pdf,application/pdf',
        }),
    )

    factura_xml = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['xml'])],
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': '.xml,application/xml,text/xml',
        }),
    )

    class Meta:
        model = Activo
        fields = [
            'factura_pdf',
            'factura_xml',
        ]

class Edit_Activo_Form(forms.ModelForm):

    class Meta:
        model = Activo
        fields = ['activo','tipo_activo','descripcion', 'responsable','eco_unidad','serie','marca','modelo','comentario','estatus','cuenta_contable','factura_interna',
                  'documento_baja','fecha_asignacion','fecha_adquisicion','precio_adquisicion','proveedor_adquisicion','origen']
       
  
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Profile.objects.none()
        self.fields['marca'].queryset = Marca.objects.none()
        self.fields['proveedor_adquisicion'].queryset = (Proveedor_direcciones.objects.none())

        if 'proveedor_adquisicion' in self.data:
            try:
                seleccion_actual = int(
                    self.data.get('proveedor_adquisicion')
                )

                self.fields[
                    'proveedor_adquisicion'
                ].queryset = Proveedor_direcciones.objects.filter(
                    id=seleccion_actual
                )

            except (ValueError, TypeError):
                pass

        elif (self.instance and self.instance.pk and self.instance.proveedor_adquisicion_id):
            self.fields['proveedor_adquisicion'].queryset = Proveedor_direcciones.objects.filter(id=self.instance.proveedor_adquisicion_id)


        
        if 'responsable' in self.data:
            try:
                seleccion_actual = int(self.data.get('responsable'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['responsable'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'marca' in self.data:
            try:
                seleccion_actual = int(self.data.get('marca'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['marca'].queryset = Marca.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'tipo_activo' in self.data:
            try:
                seleccion_actual = int(self.data.get('tipo_activo'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['tipo_activo'].queryset = Tipo_Activo.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

class UpdateResponsableForm(forms.ModelForm):
    
    class Meta:
        model = Activo
        fields = ['comentario']

class SalidasActivoForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['activo','comentario']

class Tipo_ActivoForm(forms.ModelForm):
    class Meta:
        model = Tipo_Activo
        fields = ['nombre',]

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre','familia',]