from django import forms
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura, Puntos_Intermedios
from tesoreria.models import Pago
from solicitudes.models import Subproyecto, Proyecto, Operacion, Sector
from user.models import Profile

class Puntos_Intermedios_Form(forms.ModelForm):
    class Meta: 
        model = Puntos_Intermedios
        fields = ['nombre','comentario_hospedaje','fecha_inicio','fecha_fin']

class Solicitud_ViaticoForm(forms.ModelForm):
    class Meta:
        model = Solicitud_Viatico
        fields = ['proyecto','subproyecto','superintendente','motivo','fecha_partida','fecha_retorno','colaborador','lugar_partida','lugar_comision','hospedaje','transporte','comentario_general','comentario_jefe_inmediato']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.none()
        self.fields['subproyecto'].queryset = Subproyecto.objects.none()
        self.fields['superintendente'].queryset = Profile.objects.none()
        self.fields['colaborador'].queryset = Profile.objects.none()
        
        if 'proyecto' in self.data:
            try:
                seleccion_actual = int(self.data.get('proyecto'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['subproyecto'].queryset = Subproyecto.objects.filter(proyecto= seleccion_actual)  
                self.fields['proyecto'].queryset = Proyecto.objects.filter(id= seleccion_actual)
                        
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        
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

class Concepto_ViaticoForm(forms.ModelForm):

    class Meta:
        model = Concepto_Viatico
        fields = ['producto','comentario','cantidad','precio','rendimiento']

class Pago_Viatico_Form(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto','comprobante_pago','cuenta']

class Viaticos_Factura_Form(forms.ModelForm):
    class Meta:
        model = Viaticos_Factura
        fields = ['factura_pdf','factura_xml','comentario']

class UploadFileForm(forms.Form):
    factura_pdf = forms.FileField() 
    factura_xml = forms.FileField() 