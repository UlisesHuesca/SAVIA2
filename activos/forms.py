from django import forms
from .models import Activo
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','tipo_activo', 'responsable','eco_unidad','serie','cuenta_contable','factura_interna','descripcion','comentario']
        