from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion, Sector
from dashboard.models import Inventario, Activo, Product
from user.models import Profile, Distrito
from django.core.validators import FileExtensionValidator
import decimal
import xml.etree.ElementTree as ET
import os
# Create your models here.

#Este modelo se refiere a si es Gasto o Reembolso
class Tipo_Gasto(models.Model):
    tipo = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f'{self.id}:{self.tipo}'

class Solicitud_Gasto(models.Model):
    folio = models.IntegerField(null=True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea_gasto')
    colaborador = models.ForeignKey(Profile, on_delete=models.CASCADE,null=True, related_name='Asignado_gasto', blank=True)
    #proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    #subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    operacion = models.ForeignKey(Operacion, on_delete = models.CASCADE, null=True, blank=True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='superintendente')
    complete = models.BooleanField(null=True)
    tipo = models.ForeignKey(Tipo_Gasto, on_delete=models.CASCADE, null=True)
    pagada = models.BooleanField(default=False)
    autorizar = models.BooleanField(null=True, default=None)
    autorizar2 = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(null=True)
    #created_at_time = models.TimeField(null=True)
    approved_at = models.DateTimeField(null=True)
    #approved_at_time = models.TimeField(null=True)
    approbado_fecha2 = models.DateTimeField(null=True)
    #approved_at_time2 = models.TimeField(null=True)
    facturas_completas = models.BooleanField(default=False)
    comentario = models.TextField(null=True, blank=True)
    comentariotesorero = models.TextField(null=True, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE,null=True )
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)

    class Meta:
        unique_together = ('folio', 'distrito',)

    @property
    def get_validado(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(producto__nombre="MATERIALES", completo=True, validacion = False, gasto__tipo__tipo = "REEMBOLSO")
        conteo_productos = productos.count()
        if productos == None:
            valor = True
        else:
            if conteo_productos == 0:
                valor = True
            else:
                valor = False
            
        return valor

    @property
    def monto_pagado(self):
        pagado = self.pago_set.all()
        pagado= pagado.filter(hecho=True)
        total = sum([pago.monto for pago in pagado])
        return total

    @property
    def get_subtotal_solicitud(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        total = sum([producto.get_subtotal for producto in productos])
        return total

    @property
    def get_total_impuesto(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        suma = round(sum([(producto.get_iva + producto.get_otros_impuestos) for producto in productos]),2)
        return suma

    @property
    def get_total_solicitud(self):
        productos = self.articulo_gasto_set.all()
        productos = productos.filter(completo=True)
        total = sum([producto.total_parcial for producto in productos])
        return total

    def __str__(self):
        return f'{self.id}'

class Articulo_Gasto(models.Model):
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    clase = models.BooleanField(null=True, default=False)   #Se refiere a si el producto es del True == almacén o entrara al almacén o si va por fuera
    producto = models.ForeignKey(Product, on_delete = models.CASCADE, null=True)
    comentario = models.CharField(max_length=255, null=True)
    descripcion = models.CharField(max_length=255, null=True)
    otros_impuestos = models.DecimalField(default=0,max_digits=14, decimal_places=4, null=True, blank=True)
    impuestos_retenidos = models.DecimalField(default=0, max_digits=14, decimal_places=4, null=True, blank=True)
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    #entrada_salida_express = models.BooleanField(null=True, default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    #factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    #factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])
    completo = models.BooleanField(default=False)
    validacion = models.BooleanField(default=False)
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    activo = models.ForeignKey(Activo, on_delete = models.CASCADE, null=True )

    
    

    @property
    def get_subtotal(self):
        subtotal = 0
        if self.precio_unitario and self.cantidad:
            subtotal = round(self.precio_unitario * self.cantidad, 2)
        return subtotal

    @property
    def get_iva(self):
        iva = 0

        if self.precio_unitario and self.cantidad and self.producto.iva:
            iva = self.precio_unitario * decimal.Decimal(str(0.16))*self.cantidad
        else:
            iva = 0
        return iva

    @property
    def get_otros_impuestos(self):
        impuestos = 0
        if self.otros_impuestos:
            if self.impuestos_retenidos:
                impuestos = round(self.otros_impuestos,2 - self.impuestos_retenidos, 2)
            else:
                impuestos = round(self.otros_impuestos,2)
        else:
            if self.impuestos_retenidos:
                impuestos = round(-self.impuestos_retenidos, 2)


        return impuestos

    @property
    def total_parcial(self):
        impuesto = self.get_iva
        total = round(self.get_subtotal + impuesto + self.get_otros_impuestos,2)
        return total
    
class Factura(models.Model):
    solicitud_gasto = models.ForeignKey(Solicitud_Gasto, on_delete=models.CASCADE, related_name='facturas', null=True)
    archivo_pdf = models.FileField(blank=True, null=True, upload_to='facturastb', validators=[FileExtensionValidator(['pdf'])])
    archivo_xml = models.FileField(blank=True, null=True, upload_to='xmltb', validators=[FileExtensionValidator(['xml'])])
    fecha_subida= models.DateTimeField(null=True, blank=True)
    # Puedes agregar más campos si es necesario, como fecha, descripción, etc.

    @property   
    def emisor(self):
        #with open(self.factura_xml.path,'r') as file:
            #data = file.read()
        try:
            tree = ET.parse(self.archivo_xml.path)
        except ET.ParseError as e:
            print(f"Error al parsear el archivo XML: {e}")
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
            raise ValueError("Versión del documento XML no reconocida")
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


class Entrada_Gasto_Ajuste(models.Model):
    gasto = models.ForeignKey(Articulo_Gasto, on_delete = models.CASCADE, null=True, blank=True)
    almacenista = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completado_fecha = models.DateTimeField(null=True)
    #completado_hora = models.TimeField(null=True)
    completo = models.BooleanField(default=False)
    comentario = models.TextField(max_length=200, null=True)

    @property
    def get_total_entrada(self):
        conceptos = self.conceptos_entradas_set.all()
        conceptos = conceptos.filter(completo=True)
        total = sum([concepto.get_subtotal for concepto in conceptos])
        return total

    def __str__(self):
        return f'{self.id}'


class Conceptos_Entradas(models.Model):
    concepto_material = models.ForeignKey(Inventario, on_delete = models.CASCADE, null=True)
    entrada = models.ForeignKey(Entrada_Gasto_Ajuste, on_delete= models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=6, null=True)
    agotado = models.BooleanField(default=False)
    completo = models.BooleanField(default=False)
    comentario = models.TextField(max_length=200, null=True, blank=True)

    @property
    def get_subtotal(self):
        subtotal = self.cantidad * self.precio_unitario
        return subtotal 

