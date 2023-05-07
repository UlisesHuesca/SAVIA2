from django.db import models
# De django.contrib.auth.models estamos importando el modelo de usuarios de la administration
from user.models import Distrito, Profile, Almacen
from solicitudes.models import Proyecto, Subproyecto, Operacion
#from djmoney.models.fields import MoneyField
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
#from django.db.models.functions import TruncDate

# Create your models here.




class Familia(models.Model):
    nombre = models.CharField(max_length=20, null=True, unique=True)

    def __str__(self):
        return f'{self.nombre}'

class Unidad(models.Model):
    nombre = models.CharField(max_length=10, null=True, unique=True)

    def __str__(self):
        return f'{self.nombre}'

class Subfamilia(models.Model):
    nombre = models.CharField(max_length=15, null=True)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Product(models.Model):
    codigo = models.PositiveSmallIntegerField(null=True, unique=True)
    nombre = models.CharField(max_length=100, null=True, unique=True)
    unidad = models.ForeignKey(Unidad, on_delete = models.CASCADE, null=True)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True)
    subfamilia = models.ForeignKey(Subfamilia, on_delete =models.CASCADE, null=True, blank=True)
    especialista = models.BooleanField(default=False)
    iva = models.BooleanField(default=True)
    activo = models.BooleanField(default=False)
    servicio = models.BooleanField(default=False)
    gasto = models.BooleanField(default=False)
    viatico = models.BooleanField(default=False)
    baja_item = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True, upload_to='product_images')
    completado = models.BooleanField(default = False)

    #Estas opciones de guardado de creación y actualización las voy a utilizar en todos mis modelos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))


    def __str__(self):
        return f'{self.codigo}-{self.nombre}'


    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url

class Products_Batch(models.Model):
    file_name = models.FileField(upload_to='product_bash', validators = [FileExtensionValidator(allowed_extensions=('csv',))])
    uploaded = models.DateField(auto_now_add=True)
    activated = models.BooleanField(default=False)


    def __str__(self):
        return f'File id:{self.id}'

class Inventario_Batch(models.Model):
    file_name = models.FileField(upload_to='product_bash', validators = [FileExtensionValidator(allowed_extensions=('csv',))])
    uploaded = models.DateField(auto_now_add=True)
    activated = models.BooleanField(default=False)


    def __str__(self):
        return f'File id:{self.id}'



class Marca(models.Model):
    nombre = models.CharField(max_length=20, null=True, unique=True)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f'{self.nombre}'





class Inventario(models.Model):
    producto = models.ForeignKey(Product, on_delete =models.CASCADE, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    ubicacion = models.CharField(max_length=30, null=True, blank=True)
    estante = models.CharField(max_length=30, null=True, blank=True)
    marca = models.ManyToManyField(Marca, blank=True)
    almacen = models.ForeignKey(Almacen, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    cantidad_apartada = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    cantidad_entradas = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    minimo = models.PositiveIntegerField(default =0)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    complete = models.BooleanField(default=False)
    comentario = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('producto', 'almacen',)

    @property
    def get_total_producto(self):
        total_inv = (self.cantidad + self.cantidad_apartada) * self.price
        return total_inv

    def __str__(self):
        return f'{self.producto}'

class Tipo_Orden(models.Model):
    tipo = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f'{self.id}:{self.tipo}'

class Order(models.Model):
    folio = models.CharField(max_length=6, null=True, unique=True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea')
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    area = models.ForeignKey(Operacion, on_delete = models.CASCADE, null=True)
    #sector = models.ForeignKey(Sector, on_delete = models.CASCADE, null=True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='intendente')
    supervisor = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='supervisor')
    #activo = models.ForeignKey(Activo, on_delete = models.CASCADE, null=True)
    requisitar = models.BooleanField(null=True, default=False)
    requisitado = models.BooleanField(null=True, default=False)
    complete = models.BooleanField(null=True)
    tipo = models.ForeignKey(Tipo_Orden, on_delete=models.CASCADE, null=True)
    #sol_autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Autoriza')
    autorizar = models.BooleanField(null=True, default=None)
    created_at = models.DateField(null=True)
    created_at_time = models.TimeField(null=True)
    approved_at = models.DateField(null=True)
    approved_at_time = models.TimeField(null=True)


    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))


    def __str__(self):
        return f'{self.id} -{self.folio} ordered by {self.staff}'


    @property
    def get_cart_total(self):
        productos = self.articulosordenados_set.all()
        total = sum([producto.get_total for producto in productos])
        return total

    @property
    def get_cart_quantity(self):
        productos = self.articulosordenados_set.all()
        total = sum([producto.cantidad for producto in productos])
        return total

    @property
    def get_folio(self):
        return str(self.pk).zfill(6)


class ArticulosOrdenados(models.Model):
    producto = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    orden = models.ForeignKey(Order, on_delete = models.CASCADE, null=True)
    cantidad = models.IntegerField(default=0, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.orden} - {self.producto}'

    @property
    def get_total(self):
        total = self.producto.price * self.cantidad
        return total

class ArticulosparaSurtir(models.Model):
    articulos = models.ForeignKey(ArticulosOrdenados, on_delete = models.CASCADE, null=True)
    cantidad = models.IntegerField(default=0, null=True, blank= True)
    precio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    surtir = models.BooleanField(default=False)
    cantidad_requisitar = models.IntegerField(default=0, null=True, blank=True)
    comentario = models.CharField(max_length=60, null=True, blank=True)
    requisitar = models.BooleanField(null=True, default=False)
    salida = models.BooleanField(null=True, default=False)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    seleccionado = models.BooleanField(null=True, default=False)
    created_at = models.DateField(auto_now_add=True)
    created_at_time = models.TimeField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)


    def __str__(self):
        return f'{self.articulos} - {self.cantidad} - {self.cantidad_requisitar}'