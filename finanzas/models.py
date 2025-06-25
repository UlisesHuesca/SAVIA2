from django.db import models
from compras.models import Proveedor_direcciones
#class Proveedor(models.Model):
#    nombre = models.CharField(max_length=255)
#    rfc = models.CharField(max_length=13, unique=True)

#    def __str__(self):
#        return self.nombre


class Exhibit(models.Model):
    TIPO_CHOICES = [
        ('Vordcab', 'Vordcab'),
        ('PROVEEDOR', 'Proveedor'),
        ('VACIO', 'Vacío'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    proveedor = models.ForeignKey(
        Proveedor_direcciones,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Solo se llena si el tipo es PROVEEDOR'
    )

    solicitud = models.CharField(max_length=20)
    id_detalle = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    concepto_flujo = models.CharField(max_length=50)
    descripcion = models.TextField()
    observaciones = models.TextField(blank=True, null=True)
    nombre_proveedor = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.tipo} - {self.solicitud} - {self.nombre_proveedor}"