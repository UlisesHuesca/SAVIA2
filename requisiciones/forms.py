from django import forms
from requisiciones.models import Salidas, ArticulosRequisitados, ValeSalidas, Requis, Devolucion, Devolucion_Articulos
from dashboard.models import ArticulosparaSurtir

class SalidasForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['producto','cantidad']

  
class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['comentario','tipo']

class DevolucionArticulosForm(forms.ModelForm):
    class Meta:
        model = Devolucion_Articulos
        fields = ['producto','cantidad','comentario']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = ArticulosparaSurtir.objects.none()


class ValeSalidasForm(forms.ModelForm):
    class Meta:
        model = ValeSalidas
        fields = ['material_recibido_por','comentario']

class ValeSalidasProyForm(forms.ModelForm):
    class Meta:
        model = ValeSalidas
        fields = ['proyecto','subproyecto','material_recibido_por']

class ArticulosRequisitadosForm(forms.ModelForm):
    class Meta:
        model = ArticulosRequisitados
        fields = ['cantidad']

class Articulo_Cancelado_Form(forms.ModelForm):
    class Meta:
        model = ArticulosRequisitados
        fields = ['cancelado','comentario_cancelacion']

class RequisForm(forms.ModelForm):
    class Meta:
        model = Requis
        fields = ['comentario_super', 'comentario_compras']

class Rechazo_Requi_Form(forms.ModelForm):
    class Meta:
        model = Requis
        fields = ['comentario_rechazo']