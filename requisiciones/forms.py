from django import forms
from requisiciones.models import Salidas, ArticulosRequisitados, ValeSalidas, Requis

class SalidasForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['producto','cantidad']

class ValeSalidasForm(forms.ModelForm):
    class Meta:
        model = ValeSalidas
        fields = ['material_recibido_por']

class ValeSalidasProyForm(forms.ModelForm):
    class Meta:
        model = ValeSalidas
        fields = ['proyecto','subproyecto','material_recibido_por']

class ArticulosRequisitadosForm(forms.ModelForm):
    class Meta:
        model = ArticulosRequisitados
        fields = ['cantidad']

class RequisForm(forms.ModelForm):
    class Meta:
        model = Requis
        fields = ['comentario_super', 'comentario_compras']

class Rechazo_Requi_Form(forms.ModelForm):
    class Meta:
        model = Requis
        fields = ['comentario_rechazo']