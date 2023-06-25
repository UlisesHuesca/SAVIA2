from django.db import models
from dashboard.models import Order, Inventario, ArticulosparaSurtir
from user.models import Profile
from solicitudes.models import Proyecto, Subproyecto
from simple_history.models import HistoricalRecords
#from djmoney.models.fields import MoneyField
# Create your models here.
class Requis(models.Model):
    orden = models.ForeignKey(Order, on_delete = models.CASCADE, null = True)
    folio = models.CharField(max_length=7, blank=True, null=True)
    colocada = models.BooleanField(default=False)
    complete = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    requi_autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    comentario_super = models.CharField(max_length=200, null=True, blank= True)
    comentario_compras = models.CharField(max_length=200, null=True, blank= True)
    comentario_rechazo = models.TextField(max_length=200, null=True, blank= True)
    autorizar = models.BooleanField(null=True, default=None)
    approved_at = models.DateField(null=True)
    approved_at_time = models.TimeField(null=True)

    def __str__(self):
        return f'{self.get_folio} order {self.orden} req {self.id}'

    @property
    def comprado_parcial(self):
        articulos = self.articulosrequisitados_set.all()
        for articulo in articulos:
            if articulo.cantidad_comprada > 0:
                resultado_parcial = False
            else:
                resultado_parcial = True
        return resultado_parcial

    @property
    def get_folio(self):
        return str(self.pk).zfill(6)


class ArticulosRequisitados(models.Model):
    producto = models.ForeignKey(ArticulosparaSurtir, on_delete = models.CASCADE, null=True)
    req = models.ForeignKey(Requis, on_delete = models.CASCADE, null=True)
    cantidad =  models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cantidad_comprada =  models.DecimalField(max_digits=14, decimal_places=2, default=0)
    art_surtido = models.BooleanField(null=True, default=False)
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Almacen2')
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    sel_comp = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    comentario_cancelacion = models.CharField(max_length=200, null=True, blank= True)

    def __str__(self):
        return f'{self.req} - {self.producto}- {self.cantidad}'

class ValeSalidas(models.Model):
    solicitud = models.ForeignKey(Order, on_delete = models.CASCADE, null=True)
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Almacen')
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True, blank=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True, blank=True)
    material_recibido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Vale')
    created_at = models.DateField(auto_now_add=True)
    complete = models.BooleanField(null=True, default=False)
    firmado = models.BooleanField(null=True, default=False)

class Salidas(models.Model):
    vale_salida = models.ForeignKey(ValeSalidas, on_delete = models.CASCADE, null=True)
    producto = models.ForeignKey(ArticulosparaSurtir, on_delete = models.CASCADE, null=True)
    cantidad =  models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comentario = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    salida_firmada = models.BooleanField(null=True, default=False)
    complete = models.BooleanField(null=True, default=False)
    precio = models.DecimalField(max_digits=14, decimal_places=2,default=0)
    entrada = models.IntegerField(default=0, null=True, blank=True)

    @property
    def get_costo_salida(self):
        costo = self.cantidad * self.precio
        return costo

    def __str__(self):
        return f'{self.producto} - {self.cantidad} - {self.created_at}'


class Devolucion(models.Model):
    solicitud = models.ForeignKey(Order, on_delete = models.CASCADE, null=True)
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    created_at = models.DateField(auto_now_add=True)
    fecha = models.DateField(null=True)
    hora = models.TimeField(null=True)
    complete = models.BooleanField(null=True, default=False)
    comentario = models.TextField(max_length=200, null=True)

class Devolucion_Articulos(models.Model):
    vale_devolucion = models.ForeignKey(Devolucion, on_delete = models.CASCADE, null=True)
    producto = models.ForeignKey(ArticulosparaSurtir, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=14, decimal_places=2,default=0)
    comentario = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    complete = models.BooleanField(default=False)


