from django import forms
from compras.models import Proveedor, Evidencia



class CSFForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['csf']


class ActaForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['credencial_acta_constitutiva']


class ComprobanteForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['comprobante_domicilio']


class OpinionForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['opinion_cumplimiento']

class EvidenciaForm(forms.ModelForm):

     class Meta:
        model = Evidencia
        fields =['file',]

class UploadFileForm(forms.Form):
    evidencia_file = forms.FileField(required=False) 
    