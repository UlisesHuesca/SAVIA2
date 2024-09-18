from django.db import models
from dashboard.models import Order, Inventario, ArticulosparaSurtir, Familia
from requisiciones.models import Requis, ArticulosRequisitados
from user.models import Profile, Distrito, Banco
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
import decimal
from phone_field import PhoneField
# Create your models here.



class Estatus_proveedor(models.Model):
    nombre = models.CharField(max_length=10, null=True, unique=True)

    def __str__(self):
        return f'{self.nombre}'


class Proveedor(models.Model):
    razon_social = models.CharField(max_length=150, null=True, unique=True)
    nombre_comercial = models.CharField(max_length=100, null=True, blank=True)
    rfc = models.CharField(max_length=13, null=True, unique=True)
    creado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    completo = models.BooleanField(default=False)
    extranjero = models.BooleanField(default=False)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))


    def __str__(self):
        return f'{self.razon_social}'

class Proveedor_Batch(models.Model):
    file_name = models.FileField(upload_to='product_bash', validators = [FileExtensionValidator(allowed_extensions=('csv',))])
    uploaded = models.DateField(auto_now_add=True)
    activated = models.BooleanField(default=False)


    def __str__(self):
        return f'File id:{self.id}'

class Estado(models.Model):
    nombre = models.CharField(max_length=30, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Moneda(models.Model):
    nombre = models.CharField(max_length=20)

    def __str__(self):
        return f'{self.nombre}'


class Proveedor_direcciones(models.Model):
    nombre = models.ForeignKey(Proveedor, on_delete=models.CASCADE, null=True)
    creado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, null=True)
    domicilio = models.CharField(max_length=200, null=True)
    telefono = models.CharField(null=True, max_length=14)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, null=True, blank=True)
    contacto = models.CharField(max_length=50, null=True)
    email = models.EmailField(max_length=254, null=True)
    email_opt = models.EmailField(max_length=100, null=True, blank=True)
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, null=True)
    clabe = models.CharField(max_length=20, null=True)
    cuenta = models.CharField(max_length=20, null=True)
    swift = models.CharField(max_length=20, null=True, blank=True) #TRANSFERENCIA INTERNACIONAL
    spid = models.CharField(max_length=50, null=True, blank=True)  #TRANSFERENCIA NACIONAL DOLARES
    contratocie = models.CharField(max_length=50, null=True, blank=True) #TRANSFERENCIA NACIONAL TELMEX POR EJEMPLO
    domicilio_banco = models.CharField(max_length=200, null=True, blank=True) #CUANDO ES TRANSFERENCIA INTERNACIONAL
    financiamiento = models.BooleanField(null=True, default=False)
    dias_credito = models.PositiveIntegerField(null=True)
    estatus = models.ForeignKey(Estatus_proveedor, on_delete=models.CASCADE, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    completo = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True)
    modified = models.DateField(auto_now=True)
    actualizado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Des_proveedores' )
    modificado_fecha = models.DateField(null=True)
    enviado_fecha = models.DateField(null=True)
    servicio = models.BooleanField(default=False)
    producto = models.BooleanField(default=False)
    arrendamiento = models.BooleanField(default=False)
    moneda = models.ForeignKey(Moneda, on_delete = models.CASCADE, null=True)
    referencia = models.CharField(max_length=20, null=True, blank = True)
    convenio = models.CharField(max_length=20, null=True, blank = True)

    def __str__(self):
        return f'{self.nombre}'

class Proveedor_Direcciones_Batch(models.Model):
    file_name = models.FileField(upload_to='product_bash', validators = [FileExtensionValidator(allowed_extensions=('csv',))])
    uploaded = models.DateField(auto_now_add=True)
    activated = models.BooleanField(default=False)

class Uso_cfdi(models.Model):
    codigo = models.CharField(max_length=3, null=True)
    descripcion = models.CharField(max_length=80, null=True)

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'

class Cond_pago(models.Model):
    nombre = models.CharField(max_length=20)

    def __str__(self):
        return f'{self.nombre}'

class Formas_pago(models.Model):
    codigo = models.PositiveSmallIntegerField(null=True)
    nombre = models.CharField(max_length=30)


    
class Comparativo(models.Model):
    nombre = models.CharField(max_length=100, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete = models.CASCADE, null=True)
    proveedor2 = models.ForeignKey(Proveedor, on_delete = models.CASCADE, null=True, related_name='proveedor2') 
    proveedor3 = models.ForeignKey(Proveedor, on_delete = models.CASCADE, null=True, related_name='proveedor3')
    cotizacion = models.FileField(null=True, blank=True, upload_to='comparativos',validators=[FileExtensionValidator(['pdf'])]) 
    cotizacion2 = models.FileField(null=True, blank=True, upload_to='comparativos',validators=[FileExtensionValidator(['pdf'])])
    cotizacion3 = models.FileField(null=True, upload_to='comparativos',validators=[FileExtensionValidator(['pdf'])])
    cotizacion4 = models.FileField(null=True, upload_to='comparativos', blank=True)
    cotizacion5 = models.FileField(null=True, upload_to='comparativos', blank=True)
    creada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completo = models.BooleanField(default=False)
    comentarios = models.TextField(max_length=200, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Item_Comparativo(models.Model):
    producto = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    comparativo = models.ForeignKey(Comparativo, on_delete = models.CASCADE, null=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    dias_de_entrega = models.PositiveIntegerField(null=True, blank=True)
    modelo2 = models.CharField(max_length=100, null=True, blank=True)
    marca2 = models.CharField(max_length=100, null=True, blank=True)
    precio2 = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    dias_de_entrega2 = models.PositiveIntegerField(null=True, blank=True)
    modelo3 = models.CharField(max_length=100, null=True, blank=True)
    marca3 = models.CharField(max_length=100, null=True, blank=True)
    precio3 = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    dias_de_entrega3 = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completo = models.BooleanField(default=False)

class Compra(models.Model):
    req = models.ForeignKey(Requis, on_delete = models.CASCADE, null=True, related_name = 'compras')
    folio = models.IntegerField(null=True)
    complete = models.BooleanField(default=False)
    creada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Generacion')
    created_at = models.DateTimeField(null=True)
    oc_autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Aprobacion')
    autorizado_at = models.DateTimeField(null=True, blank=True)
    autorizado1 = models.BooleanField(null=True, default=None)
    oc_autorizada_por2 = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True,related_name='Aprobacion2')
    autorizado_at_2 = models.DateTimeField(null=True, blank=True)
    autorizado2 = models.BooleanField(null=True, default=None)
    proveedor = models.ForeignKey(Proveedor_direcciones, on_delete = models.CASCADE, null=True)
    tesorero = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Tesoreria')
    referencia = models.CharField(max_length=20, null=True, blank=True)
    cond_de_pago = models.ForeignKey(Cond_pago, on_delete = models.CASCADE, null=True)
    formas_de_pago = models.ForeignKey(Formas_pago, on_delete = models.CASCADE, null=True)
    uso_del_cfdi = models.ForeignKey(Uso_cfdi, on_delete = models.CASCADE, null=True)
    dias_de_credito =  models.PositiveIntegerField(null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True)
    tipo_de_cambio = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    #anticipo = models.BooleanField(default=False)
    monto_anticipo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    dias_de_entrega = models.PositiveIntegerField(null=True, blank=True)
    #impuesto =  models.BooleanField(default=False)
    impuestos = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    retencion = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    costo_fletes = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    logistica = models.BooleanField(default=False)
    tesoreria_matriz = models.BooleanField(default=False)
    opciones_condiciones = models.TextField(max_length=400, null=True, blank=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    #comparativo = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    comparativo_model = models.ForeignKey(Comparativo, on_delete = models.CASCADE, null=True, blank=True)
    facturas_completas = models.BooleanField(default=False)
    costo_oc = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    costo_iva = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    pagada = models.BooleanField(default=False)
    fecha_pago = models.DateTimeField(null=True, blank= True)
    monto_pagado = models.DecimalField(max_digits=14,decimal_places=2, default=0)
    entrada_completa = models.BooleanField(default=False)
    solo_servicios = models.BooleanField(default=False)
    regresar_oc = models.BooleanField(default=False)
    comentarios = models.TextField(max_length=400, null=True, blank=True)
    comentario_gerencia = models.TextField(null=True, blank=True)
    comentario_solicitud = models.BooleanField(default = False)
    saldo_a_favor = models.DecimalField(max_digits=14,decimal_places=2, default=0)

    @property
    def costo_plus_adicionales(self):
        total = 0
        if self.complete:
            total = self.costo_oc
            if self.impuestos:
                total = total + self.impuestos
            if self.retencion:
                total = total - self.retencion
            if self.costo_fletes:
                total = total + self.costo_fletes
        return total


    @property
    def get_monto_pagos(self):
        pagos = self.pago_set.all()

        total_pagos = 0

        for pago in pagos:
            tipo_de_cambio = pago.tipo_de_cambio or self.tipo_de_cambio
            cuenta_moneda = pago.cuenta.moneda.nombre if pago.cuenta else None

            if self.moneda.nombre == 'DOLARES' and cuenta_moneda == 'DOLARES' and tipo_de_cambio:
                total_pagos += pago.monto * tipo_de_cambio
            else:
                total_pagos += pago.monto

        return {
            'total_pagos':total_pagos,
        }


    @property
    def get_pagos(self):
        pagos = self.pago_set.all()
        return pagos

    

    @property
    def get_subtotal(self):
        productos = self.articulocomprado_set.all()
        suma =  sum([producto.subtotal_parcial for producto in productos])
        return suma

    @property
    def get_iva(self):
        productos =  self.articulocomprado_set.all()
        suma = sum([producto.iva_parcial for producto in productos])
        return suma

    @property
    def get_total(self):
        productos =  self.articulocomprado_set.all()
        suma = sum([producto.total for producto in productos])
        return suma

    @property
    def get_folio(self):
        return f'OC{self.id}'

    def __str__(self):
        return f'oc:{self.folio} - {self.id}'


class ArticuloComprado(models.Model):
    producto = models.ForeignKey(ArticulosRequisitados, on_delete = models.CASCADE, null=True)
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cantidad_pendiente = models.DecimalField(max_digits=14, decimal_places=2, null=True) #De acuerdo al código de entradas estos son los pendientes por entrar
    entrada_completa = models.BooleanField(default=False)
    seleccionado = models.BooleanField(default=False)
    precio_unitario = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))

    @property
    def get_entradas(self):
        entradas = self.entradaarticulo_set.all()
        #entradas = entradas.filter(entrada__oc = self.oc)
        cant_entradas = sum([entrada.cantidad for entrada in entradas])
        return cant_entradas


    @property
    def subtotal_parcial(self):
        total = self.cantidad * self.precio_unitario
        return total

    @property
    def iva_parcial(self):
        iva = 0
        if self.producto.producto.articulos.producto.producto.iva:
            iva = self.subtotal_parcial * decimal.Decimal(str(0.16))
        return iva

    @property
    def total(self):
        total = self.subtotal_parcial + self.iva_parcial
        return total



    def __str__(self):
        return f'{self.id} - {self.producto.producto.articulos.producto.producto} - {self.oc.id} - {self.cantidad} - {self.precio_unitario}'

