from django import forms
from django.core.validators import FileExtensionValidator
from dashboard.models import Activo, Marca, Tipo_Activo, Profile 
from requisiciones.models import Salidas
from compras.models import Proveedor_direcciones
from .models import Vehiculo_Activo, UBM_Activo
#from bootstrap_datepicker_plus.widgets import DatePickerInput
#from django.contrib.admin.widgets import AdminDateWidget
#from django.forms.fields import DateField

class Activo_Form(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['activo','categoria','descripcion','eco_unidad','serie','marca','modelo','comentario','cuenta_contable','factura_interna',
                  'responsable','fecha_asignacion']

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Profile.objects.none()
        #self.fields['marca'].queryset = Marca.objects.none()
        if 'responsable' in self.data:
            try:
                seleccion_actual = int(self.data.get('responsable'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['responsable'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

    def clean_eco_unidad(self):
        eco = self.cleaned_data.get('eco_unidad')

        if not eco:
            return eco

        eco = eco.strip().upper()

        repetido = (Activo.objects.filter(eco_unidad__iexact=eco).exclude(pk=self.instance.pk).exists())

        if repetido:
            raise forms.ValidationError('Ya existe un activo con este ECO.')

        return eco



class DocumentosActivoForm(forms.ModelForm):
    factura_pdf = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['pdf'])],
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': '.pdf,application/pdf',
        }),
    )

    factura_xml = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['xml'])],
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': '.xml,application/xml,text/xml',
        }),
    )

    class Meta:
        model = Activo
        fields = [
            'factura_pdf',
            'factura_xml',
        ]

class Edit_Activo_Form(forms.ModelForm):

    class Meta:
        model = Activo
        fields = ['activo','categoria','descripcion', 'responsable','eco_unidad','serie','marca','modelo','comentario','estatus','cuenta_contable','factura_interna',
                  'documento_baja','fecha_asignacion','fecha_adquisicion','precio_adquisicion','proveedor_adquisicion','origen']
       
  
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Profile.objects.none()
        self.fields['marca'].queryset = Marca.objects.none()
        self.fields['proveedor_adquisicion'].queryset = (Proveedor_direcciones.objects.none())
        self.fields['categoria'].required = True

        if 'proveedor_adquisicion' in self.data:
            try:
                seleccion_actual = int(
                    self.data.get('proveedor_adquisicion')
                )

                self.fields[
                    'proveedor_adquisicion'
                ].queryset = Proveedor_direcciones.objects.filter(
                    id=seleccion_actual
                )

            except (ValueError, TypeError):
                pass

        elif (self.instance and self.instance.pk and self.instance.proveedor_adquisicion_id):
            self.fields['proveedor_adquisicion'].queryset = Proveedor_direcciones.objects.filter(id=self.instance.proveedor_adquisicion_id)


        
        if 'responsable' in self.data:
            try:
                seleccion_actual = int(self.data.get('responsable'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['responsable'].queryset = Profile.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'marca' in self.data:
            try:
                seleccion_actual = int(self.data.get('marca'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['marca'].queryset = Marca.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida
        if 'tipo_activo' in self.data:
            try:
                seleccion_actual = int(self.data.get('tipo_activo'))
                # Lógica para determinar el nuevo queryset basado en la selección actual
                self.fields['tipo_activo'].queryset = Tipo_Activo.objects.filter(id= seleccion_actual)
            except (ValueError, TypeError):
                pass  # Manejo de errores en caso de entrada no válida

class UpdateResponsableForm(forms.ModelForm):
    
    class Meta:
        model = Activo
        fields = ['comentario']

class SalidasActivoForm(forms.ModelForm):
    class Meta:
        model = Salidas
        fields = ['activo','comentario']

class Tipo_ActivoForm(forms.ModelForm):
    class Meta:
        model = Tipo_Activo
        fields = ['nombre',]

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre','familia',]


from django import forms
from .models import Vehiculo_Activo


class VehiculoActivoForm(forms.ModelForm):

    vigencia_poliza = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-control',
            },
        ),
        label='Vigencia de póliza',
    )

    fecha_verificacion = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-control',
            },
        ),
        label='Fecha de verificación',
    )

    class Meta:
        model = Vehiculo_Activo

        # No incluimos "activo" porque se asignará desde la vista.
        fields = ['tipo_vehiculo','anio_modelo','numero_motor','color','placas','estado_registro','vigencia_poliza','numero_poliza','cobertura',
            'fecha_verificacion',
        ]

        widgets = {
            'tipo_vehiculo': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'anio_modelo': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Año modelo',
                    'min': '1900',
                    'max': '2100',
                }
            ),
            'numero_motor': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Número de motor',
                }
            ),
            'color': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'placas': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Placas',
                }
            ),
            'estado_registro': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'vigencia_poliza': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'numero_poliza': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Número de póliza',
                }
            ),
            'cobertura': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'fecha_verificacion': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
        }

class UBMActivoForm(forms.ModelForm):

    class Meta:
        model = UBM_Activo

        fields = ['tipo_ubm','serie_acumulador','serie_cilindro','deposito_aceite','rack','pedestal','motor','bomba','manifold','pozo',]

        widgets = {
            'tipo_ubm': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'serie_acumulador': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Serie del acumulador',
                }
            ),
            'serie_cilindro': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Serie del cilindro',
                }
            ),
            'deposito_aceite': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Depósito de aceite',
                }
            ),
            'rack': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Rack',
                }
            ),
            'pedestal': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Pedestal',
                }
            ),
             'motor': forms.Select(
                attrs={
                    'class': 'form-select js-ubm-component',
                }
            ),
            'bomba': forms.Select(
                attrs={
                    'class': 'form-select js-ubm-component',
                }
            ),
            'manifold': forms.Select(
                attrs={
                    'class': 'form-select js-ubm-component',
                }
            ),
            'pozo': forms.Select(
                attrs={
                    'class': 'form-select js-ubm-component',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['motor'].empty_label = (
            'Sin motor asignado'
        )

        self.fields['bomba'].empty_label = (
            'Sin bomba asignada'
        )

        self.fields['manifold'].empty_label = (
            'Sin manifold asignado'
        )

        self.fields['pozo'].empty_label = (
            'Sin pozo asignado'
        )