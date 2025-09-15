from django.db import models
from django.db.models import Sum
from user.models import Distrito, Profile
from solicitudes.models import Contrato
from compras.models import Moneda

from decimal import Decimal

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

    def __str__(self):
        return f'{self.id}|{self.tipo}-{self.distrito}-{self.fecha}'
    
    @property
    def get_total(self):
        total = self.costos.aggregate(total = Sum('monto'))['total']
        return total or 0


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
    created_by = models.ForeignKey(Profile, on_delete= models.CASCADE, null=True, related_name = 'si_created')
    created_at = models.DateField(null=True)
    fecha = models.DateField(null=True)
    complete = models.BooleanField(default = False)

    @property
    def get_total(self):
        total = Decimal("0.00")
        for ingreso in self.ingresos.all():
            if ingreso.moneda and ingreso.moneda.nombre == "DOLARES":
                if ingreso.tipo_cambio:  # evitar None
                    total += ingreso.monto * ingreso.tipo_cambio
            else:
                total += ingreso.monto
        return total
    
    def __str__(self):
        return f'{self.distrito}-{self.fecha}'

class Ingresos(models.Model):
    solicitud = models.ForeignKey(Solicitud_Ingresos, on_delete= models.CASCADE, null = True, related_name = "ingresos" )
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'i_contratos')
    concepto = models.CharField(max_length = 150, null = True, blank = True)
    tipo_cambio = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    complete = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.concepto}'

class Depreciaciones(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete = models.CASCADE, null = True, related_name = 'd_contratos')
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null = True, related_name = 'd_distritos')
    created_by = models.ForeignKey(Profile, on_delete= models.CASCADE, null=True, related_name = 'd_created')
    created_at = models.DateField(null=True)
    concepto = models.CharField(max_length = 150, null = True,)
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tipo_unidad = models.CharField(max_length = 100, null = True,)
    mes_inicial = models.DateField(null=True)
    meses_a_depreciar = models.IntegerField(null=True)
    complete = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.concepto}'

    @property
    def get_depreciacion_mensual(self):
        depreciacion_mensual = self.monto/self.meses_a_depreciar
        return depreciacion_mensual
        