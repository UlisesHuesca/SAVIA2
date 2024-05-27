from django.db import models
from compras.models import Compra, Moneda, Banco
from user.models import Profile, Distrito, Banco
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico
#from djmoney.models.fields import MoneyField
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
import xml.etree.ElementTree as ET
from .utils import encontrar_variables, extraer_texto_pdf_prop
# Create your models here.



class Cuenta(models.Model):
    cuenta = models.CharField(max_length=16, null=True)
    clabe = models.CharField(max_length=22, null=True)
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    encargado = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    banco = models.ForeignKey(Banco, on_delete = models.CASCADE, null=True)
    monto_inicial = models.DecimalField(max_digits=14,decimal_places=2, null=True, blank=True)
    saldo = models.DecimalField(max_digits=14,decimal_places=2, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.CASCADE, null=True, blank=True)
    status = models.BooleanField(default=True)
    descripcion = models.CharField(max_length=250, null=True, blank=True)


    def __str__(self):
        return f'{self.id} - {self.cuenta} -{self.moneda}'
    
class Tipo_Pago(models.Model):
    nombre = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f'{self.nombre}'

class Pago(models.Model):
    tesorero = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='Tesorero')
    folio = models.PositiveIntegerField(null=True)
    tipo = models.ForeignKey(Tipo_Pago, on_delete = models.CASCADE, null=True)
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, blank=True, related_name = 'pagos')
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete = models.CASCADE, null=True, blank=True, related_name= 'pagosg')
    viatico = models.ForeignKey(Solicitud_Viatico, on_delete = models.CASCADE, null=True, blank=True, related_name = 'pagosv')
    cuenta = models.ForeignKey (Cuenta, on_delete = models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=14,decimal_places=4, null=True, default=0)
    #distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    pagado_date = models.DateTimeField(null=True, blank=True)
    pagado_real = models.DateField(null=True, blank=True)
    pagado_hora = models.TimeField(null=True, blank=True)
    hecho = models.BooleanField(null=True)
    tipo_de_cambio = models.DecimalField(max_digits=14,decimal_places=4, null=True, blank=True)
    comprobante_pago = models.FileField(null=True, upload_to='comprobante',validators=[FileExtensionValidator(['pdf'])])

    @property
    def get_facturas(self):
        facturas = self.facturas_set.all()
        return facturas

    @property
    def detalles_comprobante(self):
        texto = extraer_texto_pdf_prop(self.comprobante_pago)
        return encontrar_variables(texto)
    #def __str__(self):
     #   return f'{self.id} - {self.oc} - {self.cuenta}'

class Facturas(models.Model):
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, related_name='Compra')
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='uploaded_by')
    fecha_subido = models.DateField(null=True, blank=True)
    hora_subido = models.TimeField(null=True, blank=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])

    def __str__(self):
        return f'id:{self.id} oc:{self.oc}'
    
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

class Comprobante_saldo_favor(models.Model):
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True)
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    fecha_subido = models.DateField(null=True, blank=True)
    hora_subido = models.TimeField(null=True, blank=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    comprobante_pdf = models.FileField(blank=True, null=True, upload_to='saldo_pdf',validators=[FileExtensionValidator(['pdf'])])
    comprobante_xml = models.FileField(blank=True, null=True, upload_to='saldo_xml', validators=[FileExtensionValidator(['xml'])])

    def __str__(self):
        return f'id:{self.id} oc:{self.oc}'