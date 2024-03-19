from django.db import models
from compras.models import Compra, ArticuloComprado
from simple_history.models import HistoricalRecords
from user.models import Profile

# Create your models here.

class Entrada(models.Model):
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True)
    folio = models.PositiveIntegerField(null=True)
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, related_name ='vale_entrada')
    comentario = models.CharField(max_length=250, null=True, blank=True)
    entrada_date = models.DateTimeField(null=True, blank=True)
    #entrada_hora = models.TimeField(null=True, blank=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    completo = models.BooleanField()

    def __str__(self):
        return f'{self.id} - {self.oc} - {self.completo}'

class EntradaArticulo(models.Model):
    entrada = models.ForeignKey(Entrada, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cantidad_por_surtir = models.DecimalField(max_digits=14, decimal_places=2, null=True) #Cambié el dafault de 0 porque eso es lo que considera la view para llenar este campo
    articulo_comprado = models.ForeignKey(ArticuloComprado, on_delete = models.CASCADE, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    created_at = models.DateTimeField(auto_now_add=True)
    agotado = models.BooleanField(default=False)
    liberado = models.BooleanField(default=True)
    referencia = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f'{self.id} - {self.entrada} - {self.cantidad} - {self.articulo_comprado}'

class Reporte_Calidad(models.Model):
    articulo = models.ForeignKey(EntradaArticulo, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comentarios = models.TextField(max_length=200, null=True, blank=True)
    reporte_date = models.DateField(null=True, blank=True)
    reporte_hora = models.TimeField(null=True, blank=True)
    completo = models.BooleanField(default=False)
    autorizado = models.BooleanField(null=True, default=None)

    def __str__(self):
        return f'{self.id} - {self.articulo} - {self.completo} - {self.autorizado}'

class Tipo_Nc(models.Model):
    nombre = models.CharField(max_length=25, null=True)

    def __str__(self):
        return f'{self.nombre}'

class No_Conformidad(models.Model):
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True)
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True)
    comentario = models.TextField(max_length=250, null=True)
    tipo_nc = models.ForeignKey(Tipo_Nc, on_delete = models.CASCADE, null=True)
    nc_date = models.DateField(null=True, blank=True)
    nc_hora = models.TimeField(null=True, blank=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    completo = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.id}'

class NC_Articulo(models.Model):
    nc = models.ForeignKey(No_Conformidad, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    #cantidad_por_surtir = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    articulo_comprado = models.ForeignKey(ArticuloComprado, on_delete = models.CASCADE, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    created_at = models.DateTimeField(auto_now_add=True)
    #folio = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f'{self.id} - {self.nc} - {self.cantidad} - {self.articulo_comprado}'
