from django.db import models
from user.models import Profile
from compras.models import Proveedor_direcciones, Banco, Moneda


class Tipo_Pago_Exhibit(models.Model):
    nombre = models.CharField(max_length=50)
    nomenclatura = models.CharField(max_length=10)

    def __str__(self):
        return self.nombre


class Exhibit(models.Model):
    folio = models.IntegerField(null=True)
    creada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Exhibits')
    created_at = models.DateTimeField(null=True)
    hecho = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.folio}"

class Linea_Exhibit(models.Model):
    TIPO_CHOICES = [
        ('Vordcab', 'Vordcab'),
        ('PROVEEDOR', 'Proveedor'),
        ('VACIO', 'Vacío'),
    ]
    TIPO_PROVEEDOR_CHOICES = [
        ('PM', 'Persona Moral'),
        ('PF', 'Persona Física'),
    ]
    exhibit = models.ForeignKey('Exhibit', on_delete=models.CASCADE, related_name='lineas', null=True)  
    tipo = models.CharField(max_length=10, choices = TIPO_CHOICES)
    tipo_pago_exhibit = models.ForeignKey(Tipo_Pago_Exhibit, on_delete=models.CASCADE, null=True)
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
    tipo_proveedor = models.CharField(max_length=2, choices = TIPO_PROVEEDOR_CHOICES, null=True, blank=True, help_text='Selecciona si el proveedor es una Persona Moral (PM) o Física (PF)' )
    descripcion = models.TextField()
    observaciones = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    calle = models.CharField(max_length=255, blank=True, null=True)
    colonia = models.CharField(max_length=255, blank=True, null=True)
    cp = models.CharField(max_length=10, blank=True, null=True)
    municipio = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    contacto_nombre = models.CharField(max_length=100, blank=True, null=True)
    contacto_apellido = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    area = models.CharField(max_length=50, blank=True, null=True)
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, default=2)
    cuenta_bancaria = models.CharField(max_length=20, null=True)
    clabe = models.CharField(max_length=18, null=True)
    swift = models.CharField(max_length=11, null=True)
    aba = models.CharField(max_length=9, null=True)
    iban = models.CharField(max_length=34, null=True)
    direccion_banco = models.CharField(max_length=255, blank=True, null=True)
    observaciones_cuenta = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=30, blank=True, null=True)
    pagina_web = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return str(self.exhibit)
