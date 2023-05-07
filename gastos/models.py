from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion
from dashboard.models import Inventario
from user.models import Profile
from django.core.validators import FileExtensionValidator
import decimal
# Create your models here.

#Este modelo se refiere a si es Gasto o Reembolso
class Tipo_Gasto(models.Model):
    tipo = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f'{self.id}:{self.tipo}'

class Solicitud_Gasto(models.Model):
    folio = models.CharField(max_length=6, null=True, unique=True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea_gasto')
    colaborador = models.ForeignKey(Profile, on_delete=models.CASCADE,null=True, related_name='Asignado_gasto', blank=True)
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    area = models.ForeignKey(Operacion, on_delete = models.CASCADE, null=True, blank=True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='superintendente')
    complete = models.BooleanField(null=True)
    tipo = models.ForeignKey(Tipo_Gasto, on_delete=models.CASCADE, null=True)
    pagada = models.BooleanField(default=False)
    autorizar = models.BooleanField(null=True, default=None)
    autorizar2 = models.BooleanField(null=True, default=None)
    created_at = models.DateField(null=True)
    created_at_time = models.TimeField(null=True)
    approved_at = models.DateField(null=True)
    approved_at_time = models.TimeField(null=True)
    approbado_fecha2 = models.DateField(null=True)
    approved_at_time2 = models.TimeField(null=True)



    @property
    def monto_pagado(self):
        pagado = self.pago_set.all()
        pagado= pagado.filter(hecho=True)
        total = sum([pago.monto for pago in pagado])
        return total

    @property
    def get_subtotal_solicitud(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        total = sum([producto.get_subtotal for producto in productos])
        return total

    @property
    def get_total_impuesto(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        suma = round(sum([(producto.get_iva + producto.get_otros_impuestos) for producto in productos]),2)
        return suma

    @property
    def get_total_solicitud(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        total = sum([producto.total_parcial for producto in productos])
        return total

    def __str__(self):
        return f'{self.id}'

class Articulo_Gasto(models.Model):
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    clase = models.BooleanField(null=True, default=False)   #Se refiere a si el producto es del True == almacén o entrara al almacén o si va por fuera
    producto = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True, blank=True)
    comentario = models.CharField(max_length=75, null=True)
    otros_impuestos = models.DecimalField(default=0,max_digits=14, decimal_places=4, null=True, blank=True)
    impuestos_retenidos = models.DecimalField(default=0, max_digits=14, decimal_places=4, null=True, blank=True)
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    entrada_salida_express = models.BooleanField(null=True, default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])
    completo = models.BooleanField(default=False)


    def __str__(self):
        return f'{self.producto}'

    @property
    def get_subtotal(self):
        subtotal = 0
        if self.precio_unitario and self.cantidad:
            subtotal = round(self.precio_unitario * self.cantidad, 2)
        return subtotal

    @property
    def get_iva(self):
        iva = 0

        if self.precio_unitario and self.cantidad:
            iva = self.precio_unitario * decimal.Decimal(str(0.16))*self.cantidad
        else:
            iva = 0
        return iva

    @property
    def get_otros_impuestos(self):
        impuestos = round(self.otros_impuestos - self.impuestos_retenidos, 2)
        return impuestos

    @property
    def total_parcial(self):
        impuesto = self.get_iva
        total = round(self.get_subtotal + impuesto + self.get_otros_impuestos)
        return total