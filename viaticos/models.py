from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion
from user.models import Profile, Distrito
from dashboard.models import Inventario, Product
from django.core.validators import FileExtensionValidator
import decimal
import xml.etree.ElementTree as ET

# Create your models here.

class Solicitud_Viatico(models.Model):
    folio = models.IntegerField(null=True)
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Crea_Viatico')
    colaborador = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, blank=True, related_name='Colaborador_viatico')
    proyecto = models.ForeignKey(Proyecto, on_delete = models.CASCADE, null=True)
    subproyecto = models.ForeignKey(Subproyecto, on_delete = models.CASCADE, null=True)
    superintendente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Autorizacion')
    gerente = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='AutorizacionG')
    montos_asignados = models.BooleanField(default=False)
    complete = models.BooleanField(default=False)
    pagada = models.BooleanField(default=False)
    autorizar = models.BooleanField(null=True, default=None)
    autorizar2 = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(null=True)
    #created_at_time = models.TimeField(null=True)
    fecha_partida = models.DateField(null=True)
    fecha_retorno = models.DateField(null=True)
    periodo_comision = models.PositiveSmallIntegerField(null=True)
    lugar_partida = models.CharField(max_length=50, null=True, blank=False)
    lugar_comision = models.TextField(null=True, blank=False)
    transporte = models.CharField(max_length=90, null=True, blank=False)
    hospedaje = models.BooleanField(default=False)
    comentario_jefe_inmediato = models.TextField(null=True)
    comentario_general = models.TextField(null=True)
    approved_at = models.DateTimeField(null=True)
    #approved_at_time = models.TimeField(null=True)
    approved_at2 = models.DateTimeField(null=True)
    #approved_at_time2 = models.TimeField(null=True)
    facturas_completas = models.BooleanField(default=False)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    motivo = models.TextField(null =True, blank=False)
    comentarios_cancelacion = models.TextField(null =True, blank=False)

    unique_together = ["folio", "distrito"]

    @property
    def get_total(self):
        conceptos = self.concepto_viatico_set.all()
        conceptos = conceptos.filter(completo=True)
        total = sum([concepto.get_total_parcial for concepto in conceptos])
        return total

    @property
    def monto_pagado(self):
        pagado = self.pagosv.all()
        pagado = pagado.filter(hecho = True)
        total = sum([pago.monto for pago in pagado])
        return total

    def __str__(self):
        return f'{self.folio}'

class Puntos_Intermedios(models.Model):
    solicitud = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True)
    nombre = models.CharField(max_length=40)
    comentario_hospedaje = models.TextField(null=True) 
    fecha_inicio = models.DateField(null=True)
    fecha_fin = models.DateField(null=True)

class Concepto_Viatico(models.Model):
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    producto = models.ForeignKey(Product, on_delete = models.CASCADE, null=True)
    comentario = models.CharField(max_length=255, null=True, blank=True)
    viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=1)
    precio = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    rendimiento = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    #factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    #factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])
    completo = models.BooleanField(default=False)

    class Meta:
        unique_together =('viatico','producto',)

    @property
    def get_total_parcial(self):
        #if self.producto.nombre == "GASOLINA":
        #    if self.rendimiento == None:
        #        self.rendimiento = 0
        #    total = self.cantidad/self.rendimiento *self.precio
        #else:
        
        #print(self.cantidad)
        #print(self.precio)
        total = self.cantidad * self.precio
        return total

class Viaticos_Factura(models.Model):
    solicitud_viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True, related_name='facturas')
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    fecha_subido = models.DateTimeField(null=True)
    #hora_subido = models.TimeField(null=True)
    comentario = models.CharField(max_length=20, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturastb',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xmltb', validators=[FileExtensionValidator(['xml'])])

    #def __str__(self):
    #    return f'Factura de viatico:{self.solicitud_viatico.folio}'
    @property   
    def emisor(self):
        #with open(self.factura_xml.path,'r') as file:
            #data = file.read()
        try:
            tree = ET.parse(self.factura_xml.path)
        except ET.ParseError as e:
            print(f"Error al parsear el archivo XML: {e}")
        # Manejo adicional del error
        #tree = ET.parse(self.archivo_xml.path)
        root = tree.getroot()
        # Buscar la versión en el documento XML
        version = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
        cristal = False

        if 'http://www.businessobjects.com/products/xml/CR2008Schema.xsd' in version:
            ns = {'cr': 'urn:crystal-reports:schemas:report-detail'}
            cristal = True
        elif 'http://www.sat.gob.mx/cfd/3' in version:
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/3'}
        elif 'http://www.sat.gob.mx/cfd/4' in version:
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/4'}
       
        else:
            # Manejo de error si no se encuentra ninguna versión conocida
            raise ValueError("Versión del documento XML no reconocida")
        #comprobante = root.findall('cfdi:Comprobante')
        
        
        
       
        resultados = []
        clasificaciones = set()

        if cristal:
             # Extracting data using the correct namespace for Crystal Reports
            rfc = root.find('.//cr:Field[@FieldName="{dt_factura_internet.e_rfc}"]/cr:Value', ns).text
            nombre = root.find('.//cr:Field[@FieldName="{@Emisor1}"]/cr:Value', ns).text
            regimen_fiscal = root.find('.//cr:Field[@FieldName="{dt_factura_internet.e_regimen_fiscal}"]/cr:Value', ns).text
            total = root.find('.//cr:Field[@FieldName="{dt_factura_internet.total}"]/cr:Value', ns).text
            #subtotal = root.find('.//cr:Field[@FieldName="{dt_factura_internet.subtotal_iepsd}"]/cr:Value', ns).text
            impuestos = root.find('.//cr:Field[@FieldName="{dt_factura_internet.iva}"]/cr:Value', ns).text
            conceptos = root.findall('.//cr:Details/cr:Section', ns)
            for concepto in conceptos:
                descripcion = concepto.find('.//cr:Field[@FieldName="{@Descripcion1}"]/cr:Value', ns).text
                cantidad = concepto.find('.//cr:Field[@FieldName="{dt_factura_internet.cantidad}"]/cr:Value', ns).text
                precio = concepto.find('.//cr:Field[@FieldName="{dt_factura_internet.valor_unitario}"]/cr:Value', ns).text
                clave_prod_serv = concepto.find('.//cr:Field[@FieldName="{@Descripcion1}"]/cr:Value', ns).text
                resultados.append((descripcion, cantidad, precio, clave_prod_serv))
        else:
            emisor = root.find('cfdi:Emisor', ns)
            rfc = emisor.get('Rfc')
            nombre = emisor.get('Nombre')
            regimen_fiscal = emisor.get('RegimenFiscal')
            total = root.get('Total')
            subtotal = root.get('Subtotal')
            impuestos = root.get('TotalImpuestosTrasladados')
            receptor = root.find('cfdi:Receptor', ns)
            impuestos = root.find('cfdi:Impuestos', ns)
            conceptos = root.find('cfdi:Conceptos', ns)
            for concepto in conceptos.findall('cfdi:Concepto', ns):
                descripcion = concepto.get('Descripcion')
                cantidad = concepto.get('Cantidad')
                precio = concepto.get('ValorUnitario') 
                clave_prod_serv = concepto.get('ClaveProdServ')
                # Aquí agrupamos los valores en una tupla antes de añadirlos a la lista
                resultados.append((descripcion, cantidad, precio, clave_prod_serv))
        # Obtener los datos requeridos
         # Clasificar según clave_prod_serv
        if clave_prod_serv in ["90111800","90111501"]:
            clasificaciones.add("Hospedaje")
        elif clave_prod_serv in ["15101514", "15101515"]:
            clasificaciones.add("Gasolina")
        elif clave_prod_serv in ["90101501", "50192500","90101503","90101500"]:
            clasificaciones.add("Alimentos")
        elif clave_prod_serv in ["95111602","95111603"]:
            clasificaciones.add("Peaje")
        else:
            clasificaciones.add("Otros")


        if len(clasificaciones) == 1:
            clasificacion_general = clasificaciones.pop()
        else:
            clasificacion_general = "Mixto"


        return {'rfc': rfc, 'nombre': nombre, 'regimen_fiscal': regimen_fiscal,'total':total,'resultados':resultados, 'clasificacion_general': clasificacion_general}





