from django import forms
#from compras.models import Proveedor, Evidencia, DocumentosProveedor, Cond_pago, Moneda, Estado
from user.models import Banco, Distrito, Pais
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from compras.models import (
    Evidencia,
    DocumentosProveedor,
    Cond_pago,
    Moneda,
    Estado,
    Debida_Diligencia,
    Accionista,
    Miembro_Alta_Direccion,
    Funcionario_Publico_Relacionado,
    Relacion_Servidor_Publico,
    Responsable_Interaccion
)



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
    pais = forms.ModelChoiceField(queryset=Pais.objects.all())
    estado = forms.ModelChoiceField(queryset=Estado.objects.all())

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
    
class DebidaDiligenciaForm(forms.ModelForm):
    class Meta:
        model = Debida_Diligencia
        fields = ['cargo', 'representante_nombre', 'sitio_web', 'tiene_alta_direccion','empleado_funcionarios_publicos', 'pertenece_funcionario_publico', 'notificar_relacion_familiar',  \
        'cuentas_bloqueadas', 'detalle_cuentas_bloqueadas', 'financiamiento_externo', 'fuentes_financiamiento', 'controles_antilavado', 'responsables_interactuar',  \
        'respeta_derechos_humanos', 'elimina_trabajo_forzoso', 'empleados_contrato_prestaciones', 'explicacion_sin_contrato', 'erradica_trabajo_infantil', 'elimina_discriminacion',  \
        'enfoque_medio_ambiente', 'codigo_etica', 'codigo_conducta', 'politica_anticorrupcion', 'otro_documento_etico', 'transparencia_donativos', 'conocimiento_publico',  \
        'extensivo_grupos_interes', 'transparencia_contribuciones_politicas', 'prohibicion_sobornos', 'prohibicion_incentivos', 'prohibicion_lavado_dinero', 'manual_organizacion',  \
        'verifica_perfil_etico', 'descripcion_verificacion', 'capacitacion_anticorrupcion', 'medio_denuncia', 'seguimiento_denuncia', 'descripcion_seguimiento',  \
        'directivos_hablan_de_corrupcion']

class AccionistaForm(forms.ModelForm):
    class Meta:
        model = Accionista
        fields = ['nombre', 'porcentaje_participacion', 'nacionalidad',]

class MiembroAltaDireccionForm(forms.ModelForm):
    class Meta:
        model = Miembro_Alta_Direccion
        fields = ['nombre', 'anios_servicio','cargo', 'nacionalidad',]

class FuncionarioPublicoRelacionadoForm(forms.ModelForm):
    class Meta:
        model = Funcionario_Publico_Relacionado
        fields = ['nombre','cargo','puesto_gubernamental','periodo_funciones']

class RelacionServidorPublicoForm(forms.ModelForm):
    class Meta:
        model = Relacion_Servidor_Publico
        fields = ['nombre_servidor','tipos_relacion', 'porcentaje_participacion']

class ResponsableInteraccionForm(forms.ModelForm):
    class Meta:
        model = Responsable_Interaccion
        fields = ['nombre','trabajo_previo_vordcab','anio_baja','puesto_ocupado']