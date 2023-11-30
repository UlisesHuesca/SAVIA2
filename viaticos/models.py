from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion
from user.models import Profile, Distrito
from dashboard.models import Inventario, Product
from django.core.validators import FileExtensionValidator
import decimal

# Create your models here.

class Solicitud_Viatico(models.Model):
    folio = models.CharField(max_length=6, null=True, unique=True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea_Viatico')
    colaborador = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Colaborador_viatico')
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Autorizacion')
    montos_asignados = models.BooleanField(default=False)
    complete = models.BooleanField(default=False)
    pagada = models.BooleanField(default=False)
    autorizar = models.BooleanField(null=True, default=None)
    autorizar2 = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(null=True)
    #created_at_time = models.TimeField(null=True)
    fecha_partida = models.DateField(null=True)
    fecha_inicio_comision = models.DateField(null=True)
    periodo_comision = models.PositiveSmallIntegerField(null=True)
    lugar_partida = models.CharField(max_length=50, null=True)
    lugar_comision = models.CharField(max_length=100, null=True)
    transporte = models.CharField(max_length=90, null=True)
    hospedaje = models.BooleanField(default=False)
    comentario_hospedaje = models.CharField(max_length=255, null=True)
    comentario = models.TextField(max_length=255, null=True)
    approved_at = models.DateTimeField(null=True)
    #approved_at_time = models.TimeField(null=True)
    approved_at2 = models.DateTimeField(null=True)
    #approved_at_time2 = models.TimeField(null=True)
    facturas_completas = models.BooleanField(default=False)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    motivo = models.CharField(max_length=255, null =True)

    @property
    def get_total(self):
        conceptos = self.concepto_viatico_set.all()
        conceptos = conceptos.filter(completo=True)
        total = sum([concepto.get_total_parcial for concepto in conceptos])
        return total

    @property
    def monto_pagado(self):
        pagado = self.pago_set.all()
        pagado = pagado.filter(hecho = True)
        total = sum([pago.monto for pago in pagado])
        return total


class Concepto_Viatico(models.Model):
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    producto = models.ForeignKey(Product, on_delete = models.CASCADE, null=True, blank=True)
    comentario = models.CharField(max_length=255, null=True, blank=True)
    viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=1)
    precio = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    rendimiento = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    #factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    #factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])
    completo = models.BooleanField(default=False)

    class Meta:
        unique_together =('viatico','producto',)

    @property
    def get_total_parcial(self):
        if self.producto.producto.nombre == "GASOLINA":
            if self.rendimiento == None:
                self.rendimiento = 0
            total = self.cantidad/self.rendimiento *self.precio
        else:
            total = self.cantidad * self.precio
        return total

class Viaticos_Factura(models.Model):
    solicitud_viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True)
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    fecha_subido = models.DateTimeField(null=True)
    #hora_subido = models.TimeField(null=True)
    comentario = models.CharField(max_length=20, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturastb',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xmltb', validators=[FileExtensionValidator(['xml'])])








