from django.db import models
from compras.models import Compra, ArticuloComprado
from simple_history.models import HistoricalRecords
from user.models import Profile

# Create your models here.

class Entrada(models.Model):
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True)
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True)
    comentario = models.CharField(max_length=250, null=True, blank=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    completo = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.id} - {self.oc} - {self.completo}'

class EntradaArticulo(models.Model):
    entrada = models.ForeignKey(Entrada, on_delete = models.CASCADE, null=True)
    cantidad = models.PositiveIntegerField(null=True, blank=True)
    cantidad_por_surtir = models.PositiveIntegerField(null=True, blank=True)
    articulo_comprado = models.ForeignKey(ArticuloComprado, on_delete = models.CASCADE, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    created_at = models.DateTimeField(auto_now_add=True)
    agotado = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.id} - {self.entrada} - {self.cantidad} - {self.articulo_comprado}'
