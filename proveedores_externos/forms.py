from django import forms
from compras.models import Proveedor, Evidencia, DocumentosProveedor, Cond_pago, Moneda
from user.models import Banco, Distrito
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


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
    moneda = forms.ModelChoiceField(queryset=Moneda.objects.all())
    referencia = forms.CharField(max_length=20)
    convenio = forms.CharField(max_length=20)

    #Condiciones de Compra
    condiciones = forms.ModelChoiceField(queryset=Cond_pago.objects.all())
    dias_credito = forms.IntegerField(min_value=0, max_value=365, initial=0, label="Días de Crédito")

    # Datos del proveedor y contacto
    contacto = forms.CharField(max_length=50)
    telefono = forms.CharField(max_length=14)
    domicilio = forms.CharField(max_length=200)
    email_opt = forms.EmailField(max_length=100)

    producto = forms.BooleanField(required=False, label='Producto')
    servicio = forms.BooleanField(required=False, label='Servicio')
    arrendamiento = forms.BooleanField(required=False, label='Arrendamiento')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email_opt'].required = False
        self.fields['referencia'].required = False
        self.fields['convenio'].required = False
        self.fields['dias_credito'].required = False

    def clean_password(self):
        password = self.cleaned_data.get('password')
        try:
            validate_password(password)  # Aquí se aplican los validators definidos en AUTH_PASSWORD_VALIDATORS
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data