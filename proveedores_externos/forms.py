from django import forms
from compras.models import Proveedor, Evidencia, DocumentosProveedor



#lass CSFForm(forms.ModelForm):
#    class Meta:
#        model = Proveedor
#        fields = ['csf']


#class ActaForm(forms.ModelForm):
#    class Meta:
#        model = Proveedor
#        fields = ['credencial_acta_constitutiva']


#class ComprobanteForm(forms.ModelForm):
#    class Meta:
#        model = Proveedor
#        fields = ['comprobante_domicilio']

#class CurriculumForm(forms.ModelForm):
#    class Meta:
#        model = Proveedor
#        fields = ['curriculum']


#class OpinionForm(forms.ModelForm):
#    class Meta:
#        model = Proveedor
#        fields = ['opinion_cumplimiento']

class SubirDocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentosProveedor
        fields = ['archivo']
        
class EvidenciaForm(forms.ModelForm):

     class Meta:
        model = Evidencia
        fields =['file',]

class UploadFileForm(forms.Form):
    evidencia_file = forms.FileField(required=False) 
    