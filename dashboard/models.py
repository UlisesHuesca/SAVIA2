from django.db import models
# De django.contrib.auth.models estamos importando el modelo de usuarios de la administration
from user.models import Distrito, Profile, Almacen, Pais
from solicitudes.models import Proyecto, Subproyecto, Operacion, Sector
#from djmoney.models.fields import MoneyField
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import xml.etree.ElementTree as ET
#from django.db.models.functions import TruncDate

# Create your models here.

#class Sector(models.Model):
#    nombre = models.CharField(max_length=25, null=True, unique=True)
#    status = models.BooleanField(default=False)


class Familia(models.Model):
    nombre = models.CharField(max_length=25, null=True, unique=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.nombre}'

class Unidad(models.Model):
    nombre = models.CharField(max_length=10, null=True, unique=True)

    def __str__(self):
        return f'{self.nombre}'

class Subfamilia(models.Model):
    nombre = models.CharField(max_length=30, null=True)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Product(models.Model):
    codigo = models.CharField(max_length=6,null=True, unique=True)
    nombre = models.TextField(null=True)
    unidad = models.ForeignKey(Unidad, on_delete = models.CASCADE, null=True)
    familia = models.ForeignKey(Familia, on_delete = models.CASCADE, null=True)
    subfamilia = models.ForeignKey(Subfamilia, on_delete =models.CASCADE, null=True, blank=True)
    iva = models.BooleanField(default=True)
    activo = models.BooleanField(default=False)
    servicio = models.BooleanField(default=False)
    gasto = models.BooleanField(default=False)
    viatico = models.BooleanField(default=False)
    baja_item = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True, upload_to='product_images')
    completado = models.BooleanField(default = False)
    precioref = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    porcentaje = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    pais = models.ForeignKey(Pais, on_delete = models.CASCADE, null=True)
    #Para calidad
    critico = models.BooleanField(default = False)
    rev_calidad = models.BooleanField(default = False)
    #Estas opciones de guardado de creación y actualización las voy a utilizar en todos mis modelos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))


    def __str__(self):
        return f'{self.codigo}|{self.nombre}'


    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url
    
class PriceRefChange(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='price_changes')
    new_value = models.DecimalField(max_digits=14, decimal_places=2)
    new_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    autorizado = models.BooleanField(null=True, blank=True)  # None=pending, True=autorizado, False=rechazado
    solicitado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='solicitudes_precioref')
    solicitado_en = models.DateTimeField(null=True)
    autorizado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='autorizaciones_precioref')
    autorizado_en = models.DateTimeField(null=True, blank=True)
    motivo = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-solicitado_en']

    def __str__(self):
        return f'{self.product}'

#Este modelo fue enteramente creado para cumplimiento con la API
class Producto_Calidad(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    producto = models.OneToOneField(Product, on_delete = models.CASCADE, null=True,  related_name='producto_calidad')
    #requisitos = models.TextField(blank=True, null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))

    def __str__(self):
        return f'{self.producto}'

def validar_size(value):
    filesize = value.size
    if filesize > 2 * 1024 * 1024:  # 10 MB en bytes
        raise ValidationError('El tamaño del archivo no puede ser mayor a 2 MB.')    
    
class Tipo_Requerimiento(models.Model):
    nombre = models.CharField(max_length=50, null=True, unique=True)

    def __str__(self):
        return f'{self.nombre}'

class Requerimiento_Calidad(models.Model):
    requerimiento = models.ForeignKey(Tipo_Requerimiento,on_delete=models.CASCADE,null=True)
    comentarios = models.CharField(max_length=100, null=True)    
    solicitud = models.ForeignKey(Producto_Calidad,on_delete=models.CASCADE,null=False, related_name='requerimientos_calidad')
    fecha = models.DateTimeField(null=False,auto_now_add=True)
    
    #url = models.FileField(upload_to="bonos/",unique=True,null=False,validators=[validar_size,FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg','jpeg','xls', 'xlsx'])])
    updated_by = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)


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
        return f'{self.id}|{self.nombre}'






class Inventario(models.Model):
    producto = models.ForeignKey(Product, on_delete =models.CASCADE, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    ubicacion = models.CharField(max_length=50, null=True, blank=True)
    estante = models.CharField(max_length=30, null=True, blank=True)
    marca = models.ManyToManyField(Marca, blank=True)
    almacen = models.ForeignKey(Almacen, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    cantidad_apartada = models.DecimalField(max_digits = 14, decimal_places=2, default=0) #Una vez más cambié el null=True por default = 0
    cantidad_entradas = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    minimo = models.PositiveIntegerField(default =0)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    complete = models.BooleanField(default=False)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    activo_disponible = models.BooleanField(default=False)

    #class Meta:
        #unique_together = ('producto', 'distrito',) #Tuve que comentar tengo un error con el producto 13192-1 está repetivo 


    @property
    def get_total_producto(self):
        total_inv = (self.cantidad + self.apartada) * self.price
        return total_inv

    @property
    def costo_salidas(self):
        art_ordenados = self.articulosordenados_set.all()
        total = sum([item.get_costo_salidas for item in art_ordenados])
        return total
    
    @property
    def apartada(self):
        apartados = self.articulosordenados_set.all()

        # Para cada apartado, suma los valores disponibles_true y disponibles_false
        disponibles = sum([item.articulos_disponibles for item in apartados])
           
        return disponibles
    
    @property
    def apartada_entradas(self):
        articulos = self.articulosordenados_set.all()

        #Para cada apartado, suma los valores disponibles_true y disponibles_false
        disponibles = sum([item.articulos_totales for item in articulos])
           
        return disponibles

    def __str__(self):
        return f'{self.producto}'

class Tipo_Orden(models.Model):
    tipo = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f'{self.id}:{self.tipo}'

class Plantilla(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creador = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Creador')
    modified_at = models.DateField(auto_now=True)
    modified_by = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    complete = models.BooleanField(default=False)
    # otros campos que consideres necesarios

class ArticuloPlantilla(models.Model):
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE, null=True)
    producto = models.ForeignKey(Inventario, on_delete=models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits = 14, decimal_places=2, default=0)
    comentario_articulo = models.TextField(blank=True, null=True)
    comentario_plantilla = models.TextField(blank=True, null=True)
    modified_at = models.DateField(auto_now=True)
    modified_by = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    # otros campos que consideres necesarios

class Tipo_Activo(models.Model):
    nombre = models.CharField(max_length= 100, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Estatus_Activo(models.Model):
    nombre = models.CharField(max_length= 30, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Activo(models.Model):
    nombre = models.CharField(max_length= 20, null =True)
    folio = models.CharField(max_length= 50, null=True)
    activo = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    descripcion = models.CharField(max_length = 50, null = True)
    tipo_activo = models.ForeignKey(Tipo_Activo, on_delete=models.CASCADE, null=True)
    responsable = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    creado_por = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, related_name='Creado_por')
    eco_unidad = models.CharField(max_length=50, null=True)
    serie = models.CharField(max_length=30, null=True)
    cuenta_contable = models.CharField(max_length=25, null=True)
    factura_interna = models.CharField(max_length=15, null=True)
    descripcion = models.CharField(max_length=100, null=True)
    marca = models.ForeignKey(Marca, on_delete = models.CASCADE, null=True, blank=True)
    modelo = models.CharField(max_length=30, null=True, blank=True)
    codigo = models.CharField(max_length=10, null=True)
    comentario = models.CharField(max_length=100, null=True)
    estatus = models.ForeignKey(Estatus_Activo, on_delete = models.CASCADE, default=1)
    mantenimiento = models.BooleanField(default = False)
    completo = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='pdf_activos',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xml_activos', validators=[FileExtensionValidator(['xml'])])
    documento_baja = models.FileField(blank=True, null=True, upload_to='bajas_activos',validators=[FileExtensionValidator(['pdf'])])
    modified_by = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, related_name='modified_by')
    modified_at = models.DateField(null=True)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    fecha_asignacion = models.DateField(null=True, blank= True)

    @property   
    def emisor(self):
        #with open(self.factura_xml.path,'r') as file:
            #data = file.read()
        try:
            tree = ET.parse(self.factura_xml.path)
        except ET.ParseError as e:
            print(f"Error al parsear el archivo XML: {e}")
            return {'error': f"Error al parsear el archivo XML: {e}"}
        # Manejo adicional del error
        #tree = ET.parse(self.archivo_xml.path)
        root = tree.getroot()
        # Buscar la versión en el documento XML
        version = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')

        if 'http://www.sat.gob.mx/cfd/3' in version:
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/3'}
        elif 'http://www.sat.gob.mx/cfd/4' in version:
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/4'}
        else:
            # Manejo de error si no se encuentra ninguna versión conocida
            return {'error': "Versión del documento XML no reconocida"}
        #comprobante = root.findall('cfdi:Comprobante')
        
        emisor = root.find('cfdi:Emisor', ns)
        
        receptor = root.find('cfdi:Receptor', ns)
        impuestos = root.find('cfdi:Impuestos', ns)
        conceptos = root.find('cfdi:Conceptos', ns)
        resultados = []
        for concepto in conceptos.findall('cfdi:Concepto', ns):
            descripcion = concepto.get('Descripcion')
            cantidad = concepto.get('Cantidad')
            precio = concepto.get('ValorUnitario') 
            # Aquí agrupamos los valores en una tupla antes de añadirlos a la lista
            resultados.append((descripcion, cantidad, precio))
        # Obtener los datos requeridos
      
        rfc = emisor.get('Rfc')
        nombre = emisor.get('Nombre')
        regimen_fiscal = emisor.get('RegimenFiscal')
        total = root.get('Total')
        subtotal = root.get('Subtotal')
        impuestos = root.get('TotalImpuestosTrasladados')


        return {'rfc': rfc, 'nombre': nombre, 'regimen_fiscal': regimen_fiscal,'total':total,'resultados':resultados}

    def __str__(self):
        return f'{self.eco_unidad} | {self.descripcion}'

class Order(models.Model):
    folio = models.IntegerField(null=True)
    last_folio_number = models.IntegerField(null=True, blank = True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea')
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    operacion = models.ForeignKey(Operacion, on_delete = models.CASCADE, null=True)
    sector = models.ForeignKey(Sector, on_delete = models.CASCADE, null=True, blank = True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='intendente')
    supervisor = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='supervisor')
    activo = models.ForeignKey(Activo, on_delete = models.CASCADE, null=True, blank = True)
    requisitar = models.BooleanField(null=True, default=False)
    requisitado = models.BooleanField(null=True, default=False)
    complete = models.BooleanField(null=True)
    tipo = models.ForeignKey(Tipo_Orden, on_delete=models.CASCADE, null=True)
    #sol_autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Autoriza')
    autorizar = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(null=True)
    inicio_form = models.DateTimeField(null=True)
    #created_at_time = models.TimeField(null=True)
    approved_at = models.DateField(null=True)
    #approved_at_time = models.TimeField(null=True)
    comentario =  models.TextField(max_length=400, null=True, blank=True)
    soporte = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
   

    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))


    def __str__(self):
        return f'{self.folio}|{self.distrito}'
    
    @property
    def get_total_vales(self):
        salidas = self.valesalidas_set.all()
        suma =  sum([item.get_costo_vale for item in salidas])
        return suma
    
    @property
    def get_requis_compras(self):
        requisiciones = self.requis_set.all()
        suma_comprat = sum([item.get_costo_requisicion['suma_total'] for item in requisiciones])
       
        suma_pagos = sum([item.get_costo_requisicion['suma_pagos'] for item in requisiciones])
       
        return {
            'suma_comprat':suma_comprat,
           
            'suma_pagos': suma_pagos,
        }


    @property
    def get_cart_total(self):
        productos = self.productos.all()
        total = sum([producto.get_total for producto in productos])
        return total

    @property
    def get_cart_quantity(self):
        productos = self.productos.all()
        total = sum([producto.cantidad for producto in productos])
        return total

    @property
    def get_folio(self):
        return 'PL'+str(self.pk).zfill(6)


class ArticulosOrdenados(models.Model):
    producto = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    orden = models.ForeignKey(Order, on_delete = models.CASCADE, null=True, related_name= "productos")
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'{self.orden}|{self.producto}'
    
    @property
    def articulos_salidas(self):
        disponibles = self.articulosparasurtir_set.all()
        cantidad_salida = sum([item.cantidad_salidas for item in disponibles])
        return cantidad_salida
    
    
    
    @property
    def articulos_disponibles(self):
        disponibles = self.articulosparasurtir_set.filter(surtir=True)
        cantidad_disponible = sum([item.cantidad for item in disponibles])

        return cantidad_disponible

    @property
    def articulos_totales(self):
        articulos = self.articulosparasurtir_set.all()
        cantidad = sum([item.cantidad for item in articulos])

        return cantidad
    
    
    @property
    def get_total(self):
        total = self.producto.price * self.cantidad
        return total
    
    
class ArticulosparaSurtir(models.Model):
    articulos = models.ForeignKey(ArticulosOrdenados, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    surtir = models.BooleanField(default=False)
    cantidad_requisitar = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comentario = models.CharField(max_length=60, null=True, blank=True)
    requisitar = models.BooleanField(null=True, default=False)
    salida = models.BooleanField(null=True, default=False)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))
    seleccionado = models.BooleanField(null=True, default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    #created_at_time = models.TimeField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)
    seleccionado_salida = models.BooleanField(default=False)
    seleccionado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Seleccionado_por')
    procesado = models.BooleanField(default = False)

    @property
    def cantidad_salidas(self):
        salidas = self.salidas_set.all()
        cantidad = sum([salida.cantidad for salida in salidas])
        return cantidad

    def __str__(self):
        return f'{self.articulos} - {self.cantidad} - {self.cantidad_requisitar}'
    
#class UnidadTB(models.Model):
#    IDUNIDADMEDIDA = models.AutoField(primary_key=True)
#    NOMBRE = models.CharField(max_length=20)
    # ... otros campos que existen en la tabla bancos_tb ...

#    class Meta:
#        managed = False
#        db_table = 'unidadesmedidatb'