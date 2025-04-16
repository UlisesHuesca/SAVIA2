from django import forms
from compras.models import Proveedor, Evidencia, DocumentosProveedor
from user.models import Banco, Distrito

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
    
class RegistroProveedorForm(forms.Form):
    razon_social = forms.CharField(max_length=150, required=True, label="Razón Social")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirmar Contraseña")
    
    contacto = forms.CharField(max_length=50, required=True)
    telefono = forms.CharField(max_length=14, required=True)
    domicilio = forms.CharField(max_length=200, required=True)
    clabe = forms.CharField(max_length=20, required=True)
    banco = forms.ModelChoiceField(queryset=Banco.objects.all(), required=True)
    distrito = forms.ModelChoiceField(queryset=Distrito.objects.all(), required=True)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data