from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from dashboard.models import Inventario, Marca
from user.models import Profile
from solicitudes.models import Pozo



# Create your models here.
class Categoria_Activo(models.Model):
    nombre = models.CharField(max_length= 50, unique=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoria de activo'
        verbose_name_plural = 'Categorias de activos'

    def __str__(self):
        return self.nombre






class Vehiculo_Activo(models.Model):

    class TipoVehiculo(models.TextChoices):
        MOTOCICLETA = 'MOTOCICLETA', 'Motocicleta'
        MOTOCARRO = 'MOTOCARRO', 'Motocarro'
        AUTOMOVIL = 'AUTOMOVIL', 'Automóvil'
        SUV = 'SUV', 'SUV'
        VAN = 'VAN', 'Van'
        PICK_UP = 'PICK UP', 'Pick up'
        TRACTOCAMION = 'TRACTOCAMION', 'Tractocamión'
        REMOLQUE_CUELLO_GANZO = (
            'REMOLQUE CUELLO DE GANZO',
            'Remolque cuello de ganso',
        )
        REMOLQUE = 'REMOLQUE', 'Remolque'
        CAMIONETA = 'CAMIONETA', 'Camioneta'
        CAMION = 'CAMION', 'Camión'

    class ColorVehiculo(models.TextChoices):
        AZUL = 'AZUL', 'Azul'
        BLANCO = 'BLANCO', 'Blanco'
        BLANCO_CANDY = 'BLANCO CANDY', 'Blanco candy'
        GRIS = 'GRIS', 'Gris'
        GRIS_PLATA = 'GRIS/PLATA', 'Gris/Plata'
        NEGRO = 'NEGRO', 'Negro'
        ROJO = 'ROJO', 'Rojo'

    class EstadoRegistro(models.TextChoices):
        FEDERAL = 'FEDERAL', 'Federal'
        TABASCO = 'TABASCO', 'Tabasco'
        TAMAULIPAS = 'TAMAULIPAS', 'Tamaulipas'
        VERACRUZ = 'VERACRUZ', 'Veracruz'

    class CoberturaSeguro(models.TextChoices):
        AMPLIA = 'AMPLIA', 'Amplia'
        LIMITADA = 'LIMITADA', 'Limitada'
        COBERTURA_0017 = '0017', '0017'

    activo = models.OneToOneField('dashboard.Activo',on_delete=models.CASCADE,related_name='vehiculo',)
    tipo_vehiculo = models.CharField(max_length=30,choices=TipoVehiculo.choices,null=True,blank=True,)
    anio_modelo = models.PositiveSmallIntegerField(null=True,blank=True,validators=[MinValueValidator(1900),MaxValueValidator(2100),],verbose_name='Año modelo',)
    numero_motor = models.CharField(max_length=30,null=True,blank=True,verbose_name='Número de motor',)
    color = models.CharField(max_length=20,choices=ColorVehiculo.choices,null=True,blank=True,)
    placas = models.CharField(max_length=20,null=True,blank=True,db_index=True,)
    estado_registro = models.CharField(max_length=20,choices=EstadoRegistro.choices,null=True,blank=True,verbose_name='Estado de registro',)
    vigencia_poliza = models.DateField(null=True,blank=True,verbose_name='Vigencia de póliza',)
    numero_poliza = models.CharField(max_length=30,null=True,blank=True,verbose_name='Número de póliza',)
    cobertura = models.CharField(max_length=15,choices=CoberturaSeguro.choices,null=True,blank=True,)
    fecha_verificacion = models.DateField(null=True,blank=True,verbose_name='Fecha de verificación',)

    class Meta:
        ordering = ['activo__eco_unidad']
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'

    def __str__(self):
        return (
            f'{self.activo.eco_unidad} - '
            f'{self.get_tipo_vehiculo_display()}'
        )

class Motor_UBM(models.Model):

    class TipoMotor(models.TextChoices):
        V6_43 = 'V6_43', 'CI V6 4.3 L'
        V6_44 = 'V6_44', 'CI V6 4.4 L'
        V6_45 = 'V6_45', 'CI V6 4.5 L'
        V6_48 = 'V6_48', 'CI V6 4.8 L'
        V8_57 = 'V8_57', 'CI V8 5.7 L'

    tipo = models.CharField(max_length=20, choices=TipoMotor.choices, null=True, blank=True,)
    serie = models.CharField(max_length=30,null=True,blank=True,)
    factura = models.CharField(max_length=50,null=True,blank=True,)

    def __str__(self):
        return f'{self.serie or "Sin serie"} - {self.get_tipo_display() or "Sin tipo"}'


class Bomba_UBM(models.Model):

    class MarcaBomba(models.TextChoices):
        DANFOSS = 'DANFOSS', 'Danfoss'
        KAWASAKI = 'KAWASAKI', 'Kawasaki'
        KPM = 'KPM', 'KPM'
        OTRA = 'OTRA', 'Otra'
        NO_APLICA = 'NO_APLICA', 'No aplica'

    serie = models.CharField(max_length=30, null=True, blank=True,)
    marca = models.CharField(max_length=20,choices=MarcaBomba.choices, null=True,blank=True,)
    numero_interno = models.CharField(max_length=20, null=True, blank=True,)

    def __str__(self):
        datos = [self.numero_interno, self.serie]
        return ' - '.join(dato for dato in datos if dato) or 'Bomba sin identificar'

class Manifold_UBM(models.Model):

    class MarcaManifold(models.TextChoices):
        VORDCAB = 'VORDCAB', 'Vordcab'
        OTRO = 'OTRO', 'Otro'

    serie = models.CharField(max_length=30, null=True, blank=True,)
    marca = models.CharField(max_length=20, choices=MarcaManifold.choices, null=True, blank=True,)

    def __str__(self):
        return self.serie or 'Manifold sin identificar'

class UBM_Activo(models.Model):
    class TipoUBM(models.TextChoices):
        UBM_120 = 'UBM_120', 'UBM 120"'
        UBM_144 = 'UBM_144', 'UBM / UBMC 144"'
        UBMSC_300 = 'UBMSC_300', 'UBMSC 300"'
        UBMSC_320 = 'UBMSC_320', 'UBMSC 320"'
        UBMSC_360 = 'UBMSC_360', 'UBMSC 360"'

    activo = models.OneToOneField('dashboard.Activo', on_delete=models.CASCADE,related_name='ubm')
    tipo_ubm = models.CharField(max_length=20, choices=TipoUBM.choices, null=True, blank=True,)
    serie_acumulador = models.CharField(max_length=30, null=True, blank=True,)
    serie_cilindro = models.CharField(max_length=30, null=True, blank=True,)
    deposito_aceite = models.CharField(max_length=30,null=True,blank=True,)
    rack = models.CharField(max_length=50,null=True,blank=True,)
    pedestal = models.CharField(max_length=50,null=True,blank=True,)
    motor = models.OneToOneField(Motor_UBM, on_delete=models.SET_NULL, null=True, blank=True, related_name='ubm_actual',)
    bomba = models.OneToOneField(Bomba_UBM,on_delete=models.SET_NULL,null=True,blank=True,related_name='ubm_actual',)
    manifold = models.OneToOneField(Manifold_UBM,on_delete=models.SET_NULL,null=True,blank=True,related_name='ubm_actual',)
    pozo = models.ForeignKey(Pozo, on_delete=models.SET_NULL, null=True, blank=True, related_name='ubms',)

    @property
    def ubicacion_operativa(self):
        if self.pozo:
            return self.pozo

        if self.activo.activo and self.activo.activo.distrito:
            return self.activo.activo.distrito

        return None

    def __str__(self):
        return f'{self.activo.eco_unidad} - {self.get_tipo_ubm_display()}'