from django import forms
from .models import Activo
from requisiciones.models import Salidas
from dashboard.models import Profile 
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','tipo_activo','descripcion','eco_unidad','serie','marca','modelo','comentario']

class Edit_Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','tipo_activo','descripcion', 'responsable','eco_unidad','serie','marca','modelo','comentario']

class UpdateResponsableForm(forms.ModelForm):
    
    class Meta:
        model = Activo
        fields = ['comentario']

class SalidasActivoForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['activo','comentario']