from django import forms
from .models import Costos

class Costo_Form(forms.ModelForm):
    class Meta:
        model = Costos
        fields = ['distrito','contrato','concepto','categorizacion','fecha','monto','tipo'] 

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