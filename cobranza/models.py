from django.db import models
from solicitudes.models import Proyecto

# Create your models here.

class Cobranza(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, null=True)
    monto_abono = models.DecimalField(max_digits=19, null=True, decimal_places=2)
    fecha_pago = models.DateField(auto_now=False)
    comentario = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f'{self.id}'