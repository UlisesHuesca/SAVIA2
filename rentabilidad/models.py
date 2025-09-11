from django.db import models
from user.models import Distrito, Profile
from solicitudes.models import Contrato
from compras.models import Moneda

class Concepto(models.Model):
    nombre = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Tipo_Costo(models.Model):
    nombre = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f'{self.nombre}'
    
class Solicitud_Costos(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'sc_distritos')
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'sc_contratos')
    created_by = models.ForeignKey(Profile, on_delete= models.CASCADE, null=True, related_name = 'sc_created')
    created_at = models.DateField(null=True)
    tipo = models.ForeignKey(Tipo_Costo, on_delete=models.CASCADE, null = True, related_name = 'sc_tipos')
    fecha = models.DateField(null=True)
    complete = models.BooleanField(default = False)

# Create your models here.
class Costos(models.Model):
    solicitud = models.ForeignKey(Solicitud_Costos, on_delete= models.CASCADE, null = True, related_name = "costos" )
    concepto = models.ForeignKey(Concepto, on_delete = models.CASCADE, null = True, related_name = 'costos_conceptos')
    categorizacion = models.CharField(max_length = 150, null = True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    complete = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.concepto}'
    
class Solicitud_Ingresos(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'si_distritos')
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'si_contratos')
    created_by = models.ForeignKey(Profile, on_delete= models.CASCADE, null=True, related_name = 'si_created')
    created_at = models.DateField(null=True)
    fecha = models.DateField()
    complete = models.BooleanField(default = False)

class Ingresos(models.Model):
    concepto = models.CharField(max_length = 150, null = True,)
    tipo_cambio = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    complete = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.concepto}'

class Depreciaciones(models.Model):
    concepto = models.CharField(max_length = 150, null = True,)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tipo_unidad = models.CharField(max_length = 100, null = True,)
    mes_inicial = models.DateField()
    mes_final = models.DateField()
    complete = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.concepto}'
