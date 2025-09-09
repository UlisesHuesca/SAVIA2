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

# Create your models here.
class Costos(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'costos_distritos')
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'costos_contratos')
    concepto = models.ForeignKey(Concepto, on_delete = models.CASCADE, null = True, related_name = 'costos_conceptos')
    categorizacion = models.CharField(max_length = 150, null = True)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tipo = models.ForeignKey(Tipo_Costo, on_delete=models.CASCADE, null = True, related_name = 'costos_tipos')
    created_by = models.ForeignKey(Profile, on_delete= models.CASCADE, null=True, related_name = 'costo_created')
    created_at = models.DateField(null=True)

    def __str__(self):
        return f'{self.concepto}'

class Ingresos(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'ingresos_distritos')
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'ingresos_contratos')
    concepto = models.CharField(max_length = 150, null = True,)
    tipo_cambio = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fecha = models.DateField()

    def __str__(self):
        return f'{self.concepto}'

class Depreciaciones(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'depreciaciones_distritos')
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'depreciaciones_contratos')
    concepto = models.CharField(max_length = 150, null = True,)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tipo_unidad = models.CharField(max_length = 100, null = True,)
    mes_inicial = models.DateField()
    mes_final = models.DateField()

    def __str__(self):
        return f'{self.concepto}'
