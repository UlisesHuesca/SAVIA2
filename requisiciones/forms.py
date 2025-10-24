from django import forms
from requisiciones.models import Salidas, ArticulosRequisitados, ValeSalidas, Requis, Devolucion, Devolucion_Articulos
from dashboard.models import Order
from user.models import Profile

class SalidasForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['producto','cantidad']

class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['comentario']

class DevolucionArticulosForm(forms.ModelForm):
    class Meta:
        model = Devolucion_Articulos
        fields = ['producto','cantidad','comentario']

class ValeSalidasForm(forms.ModelForm):
    class Meta:
        model = ValeSalidas
        fields = ['material_recibido_por','comentario']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material_recibido_por'].queryset = Profile.objects.none()

        if 'material_recibido_por' in self.data:
                try:
                    seleccion_actual = int(self.data.get('material_recibido_por'))
                    # Lógica para determinar el nuevo queryset basado en la selección actual
                    self.fields['material_recibido_por'].queryset = Profile.objects.filter(id= seleccion_actual)
                except (ValueError, TypeError):
                    pass  # Manejo de errores en caso de entrada no válida

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


class OrderComentarioForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["comentario"]
        widgets = {"comentario": forms.Textarea(attrs={"rows":2})}

