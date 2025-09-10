from django import forms
from .models import Solicitud_Costos, Costos

class Costo_Form(forms.ModelForm):
    class Meta:
        model = Solicitud_Costos
        fields = ['distrito','contrato','fecha'] 

        widgets = {
            'fecha': forms.DateInput(
                attrs={
                    'type': 'month',
                    'class': 'form-control',
                    'placeholder': 'MM-YYYY',
                },
                format='%Y-%m'  # formato de entrada
            ),
        }