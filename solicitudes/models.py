from django.db import models
# De django.contrib.auth.models estamos importando el modelo de usuarios de la administration
from django.contrib.auth.models import User
from user.models import Distrito
# Create your models here.

class Cliente(models.Model):
    nombre = models.CharField(max_length=30,null=True)

    def __str__(self):
        return f'{self.nombre}'

class St_Entrega(models.Model):
    status = models.CharField(max_length=10,null=True)

    def __str__(self):
        return f'{self.status}'

class Proyecto(models.Model):
    nombre = models.CharField(max_length=50, null=True)
    descripcion = models.CharField(max_length=100, null=True, blank=True)
    activo = models.BooleanField(default=True)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    factura = models.CharField(max_length=10, null=True, blank=True)
    fecha_factura = models.DateField(null=True, blank=True)
    folio_cotizacion = models.CharField(max_length=10, null=True, blank=True)
    oc_cliente = models.CharField(max_length=10, null=True, blank=True)
    status_de_entrega = models.ForeignKey(St_Entrega, on_delete=models.CASCADE, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        unique_together = ('nombre', 'distrito',)

    @property
    def get_projects_total(self):
        subproyectos = self.subproyecto_set.all()
        total = sum([subproyecto.presupuesto for subproyecto in subproyectos])
        return total

    @property
    def get_pagos_cliente(self):
        pagos = self.cobranza_set.all()
        total = sum([pago.monto_abono for pago in pagos])
        return total

    @property
    def get_saldo(self):
        pagos = self.cobranza_set.all()
        if self.get_projects_total:
            total = self.get_projects_total - sum([pago.monto_abono for pago in pagos])
        else:
            total=0
        return total


    def __str__(self):
        return f'{self.nombre}-{self.distrito}'



class Subproyecto(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    nombre = models.CharField(max_length=50, null=True, unique=True)
    descripcion = models.CharField(max_length=50, null=True, blank=True)
    presupuesto = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    gastado = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.nombre}-{self.presupuesto}'

class Sector(models.Model):
    nombre = models.CharField(max_length=50, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre}'

class Activo(models.Model):
    eco_unidad = models.CharField(max_length=15, null=True, unique=True)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, null=True)
    tipo = models.CharField(max_length=15, null=True)
    serie = models.CharField(max_length=15, null=True)
    cuenta = models.CharField(max_length=15, null=True)
    factura_interna = models.CharField(max_length=15, null=True)
    arrendado = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.eco_unidad}'

class Operacion(models.Model):
    nombre = models.CharField(max_length=50, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre}'



