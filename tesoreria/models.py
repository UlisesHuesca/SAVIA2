from django.db import models
from compras.models import Compra, Moneda, Banco
from user.models import Profile, Distrito, Banco
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico
#from djmoney.models.fields import MoneyField
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
# Create your models here.



class Cuenta(models.Model):
    cuenta = models.CharField(max_length=13, null=True)
    clabe = models.CharField(max_length=22, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    encargado = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    banco = models.ForeignKey(Banco, on_delete = models.CASCADE, null=True)
    monto_inicial = models.DecimalField(max_digits=14,decimal_places=2, null=True, blank=True)
    saldo = models.DecimalField(max_digits=14,decimal_places=2, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'{self.id} - {self.cuenta} - {self.monto_inicial}'

class Pago(models.Model):
    tesorero = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Tesorero')
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, blank=True)
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete = models.CASCADE, null=True, blank=True)
    viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True, blank=True)
    cuenta = models.ForeignKey (Cuenta, on_delete = models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=14,decimal_places=4, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    pagado_date = models.DateField(null=True, blank=True)
    pagado_hora = models.TimeField(null=True, blank=True)
    hecho = models.BooleanField(default=False)
    tipo_de_cambio = models.DecimalField(max_digits=14,decimal_places=4, null=True, blank=True)
    comprobante_pago = models.FileField(null=True, upload_to='comprobante',validators=[FileExtensionValidator(['pdf'])])

    @property
    def get_facturas(self):
        facturas = self.facturas_set.all()
        return facturas

    def __str__(self):
        return f'{self.id} - {self.oc} - {self.cuenta}'

class Facturas(models.Model):
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, related_name='Compra')
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='uploaded_by')
    fecha_subido = models.DateField(null=True, blank=True)
    hora_subido = models.TimeField(null=True, blank=True)
    comentario = models.CharField(max_length=100, null=True)
    hecho = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])

    def __str__(self):
        return f'id:{self.id} oc:{self.oc}'