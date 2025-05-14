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
    razon_social = forms.CharField(max_length=150, label="Razón Social")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")
    
    #Datos Bancarios
    clabe = forms.CharField(max_length=20)
    cuenta = forms.CharField(max_length=20)
    banco = forms.ModelChoiceField(queryset=Banco.objects.all())
    referencia = forms.CharField(max_length=20)
    convenio = forms.CharField(max_length=20)


    # Datos del proveedor y contacto
    contacto = forms.CharField(max_length=50)
    telefono = forms.CharField(max_length=14)
    domicilio = forms.CharField(max_length=200)
    email_opt = forms.EmailField(max_length=100)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email_opt'].required = False
        self.fields['referencia'].required = False
        self.fields['convenio'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data