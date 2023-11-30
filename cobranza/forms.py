from django import forms
from .models import Cobranza
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Cobranza_Form(forms.ModelForm):
    class Meta:
        model = Cobranza
        fields = ['proyecto','monto_abono', 'fecha_pago','comentario',]

class Cobranza_Edit_Form(forms.ModelForm):
    class Meta:
        model = Cobranza
        fields = ['monto_abono', 'fecha_pago','comentario',]