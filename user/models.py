from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Banco(models.Model):
    nombre = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Tipo_perfil(models.Model):
    #Nombre
    nombre = models.CharField(max_length=200, null=True)
    #Filtros del nav
    inicio_estadisticas = models.BooleanField(null=True, default=False)
    calidad = models.BooleanField(null=True, default=False)
    configuracion = models.BooleanField(null=True, default=False)
    almacen = models.BooleanField(null=True, default=False)
    solicitudes = models.BooleanField(null=True, default=False)
    requisiciones = models.BooleanField(null=True, default=False)
    compras = models.BooleanField(null=True, default=False)
    tesoreria = models.BooleanField(null=True, default=False)
    autorizacion = models.BooleanField(null=True, default=False)
    reportes = models.BooleanField(null=True, default=False)
    historicos = models.BooleanField(null=True, default=False)
    #Filtros de perfil para acciones
    supervisor = models.BooleanField(null=True, default=False)
    superintendente = models.BooleanField(null=True, default=False)
    almacenista = models.BooleanField(null=True, default=False)
    comprador = models.BooleanField(null=True, default=False)
    oc_superintendencia = models.BooleanField(null=True, default=False)
    oc_gerencia = models.BooleanField(null=True, default=False)
    def __str__(self):
        return f'{self.nombre}'

class Distrito(models.Model):
    nombre = models.CharField(max_length=20, null=True)
    abreviado = models.CharField(max_length=3, null=True)

    def __str__(self):
        return f'{self.nombre} - {self.abreviado}'

class Almacen(models.Model):
    nombre = models.CharField(max_length=25, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return f'{self.nombre}'



class Profile(models.Model):
    staff = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    address = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=20, null=True)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, null=True)
    almacen = models.ManyToManyField(Almacen, related_name='almacenes')
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, null=True, blank=True)
    cuenta_bancaria = models.CharField(max_length=12, null=True, blank=True)
    clabe = models.CharField(max_length=18, null=True, blank=True)
    image = models.ImageField(blank=True, upload_to='profile_images')
    tipo = models.ForeignKey(Tipo_perfil, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return f'{self.staff.username}'

    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url