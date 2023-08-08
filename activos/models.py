from django.db import models
from dashboard.models import Inventario, Marca
from user.models import Profile

# Create your models here.
class Tipo_Activo(models.Model):
    nombre = models.CharField(max_length= 100, null=True)

    def __str__(self):
        return f'{self.nombre}'



class Activo(models.Model):
    activo = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    tipo_activo = models.ForeignKey(Tipo_Activo, on_delete=models.CASCADE, null=True)
    responsable = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    creado_por = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, related_name='Creado_por')
    eco_unidad = models.CharField(max_length=50, null=True, unique=True)
    serie = models.CharField(max_length=20, null=True)
    cuenta_contable = models.CharField(max_length=20, null=True)
    factura_interna = models.CharField(max_length=20, null=True)
    descripcion = models.CharField(max_length=100, null=True)
    marca = models.ForeignKey(Marca, on_delete = models.CASCADE, null=True)
    modelo = models.CharField(max_length=30, null=True, blank=True)
    #codigo = models.CharField(max_length=20, null=True)
    comentario = models.CharField(max_length=100, null=True)
    completo = models.BooleanField(default=False)
   

    def __str__(self):
        return f'{self.eco_unidad}'