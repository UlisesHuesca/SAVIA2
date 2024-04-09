from django import forms
from dashboard.models import Activo, Marca
from requisiciones.models import Salidas
from dashboard.models import Profile 
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','tipo_activo','descripcion','eco_unidad','serie','marca','modelo','comentario','estatus','cuenta_contable','factura_interna','factura_pdf','factura_xml']

    
class Edit_Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['tipo_activo','descripcion', 'responsable','eco_unidad','serie','marca','modelo','comentario','estatus','cuenta_contable','factura_interna','factura_pdf','factura_xml','documento_baja']
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Profile.objects.none()
        self.fields['marca'].queryset = Marca.objects.none()
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


class UpdateResponsableForm(forms.ModelForm):
    
    class Meta:
        model = Activo
        fields = ['comentario']

class SalidasActivoForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['activo','comentario']