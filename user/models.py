from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Banco(models.Model):
    nombre = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Empresa(models.Model):
    nombre = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f'{self.nombre}'
    
class CustomUser(models.Model):
    staff = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, null=True, blank=True)
    cuenta_bancaria = models.CharField(max_length=25, null=True, blank=True)
    clabe = models.CharField(max_length=22, null=True, blank=True)
    image = models.ImageField(blank=True, upload_to='profile_images',null=True)
    phone = models.CharField(max_length=20, null=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    nivel = models.PositiveSmallIntegerField(default=4)
    empresa = models.ForeignKey(Empresa, on_delete= models.CASCADE, null=True)
    puesto = models.CharField(max_length=40, null=True, blank=True)

    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url

    def __str__(self):
        return f'{self.staff}'


class Tipo_perfil(models.Model):
    #Nombre
    nombre = models.CharField(max_length=200, null=True)
    #Filtros del navs
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
    proveedores = models.BooleanField(null=True, default=False)
    #Filtros de perfil para acciones
    supervisor = models.BooleanField(null=True, default=False)
    superintendente = models.BooleanField(null=True, default=False)
    gerente = models.BooleanField(null=True, default= False)
    almacenista = models.BooleanField(null=True, default=False)
    comprador = models.BooleanField(null=True, default=False)
    oc_superintendencia = models.BooleanField(null=True, default=False)
    oc_gerencia = models.BooleanField(null=True, default=False)
    def __str__(self):
        return f'{self.nombre}'

class Distrito(models.Model):
    nombre = models.CharField(max_length=20, null=True)
    abreviado = models.CharField(max_length=3, null=True)
    responsable = models.CharField(max_length=20, null=True)
    status = models.BooleanField(default = True)

    def __str__(self):
        return f'{self.nombre}'

class Almacen(models.Model):
    nombre = models.CharField(max_length=25, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return f'{self.nombre}'



class Profile(models.Model):
    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    distritos = models.ForeignKey(Distrito, on_delete=models.CASCADE, null=True)
    almacen = models.ManyToManyField(Almacen, related_name='almacenes')
    tipo = models.ForeignKey(Tipo_perfil, on_delete = models.CASCADE, null=True)
    st_activo = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.staff.staff.username} - {self.distritos.nombre} - {self.tipo}'

    

#class BancoTB(models.Model):
#    IDBANCO = models.AutoField(primary_key=True)
#    BANCO = models.CharField(max_length=255)
    # ... otros campos que existen en la tabla bancos_tb ...

#    class Meta:
#        managed = False
#        db_table = 'bancostb'