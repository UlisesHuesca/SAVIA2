from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion, Sector
from dashboard.models import Inventario, Activo, Product
from user.models import Profile, Distrito, Empresa
from compras.models import Proveedor_direcciones
from django.core.validators import FileExtensionValidator
from decimal import Decimal
from viaticos.models import Solicitud_Viatico
import decimal
import xml.etree.ElementTree as ET
from django.db.models import Q
import os

# Create your models here.

#Este modelo se refiere a si es Gasto o Reembolso
class Tipo_Gasto(models.Model):
    tipo = models.CharField(max_length=30, null=True)
    familia = models.CharField(max_length=30, null=True, blank=True)

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
    autorizado_por2 = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='gerente')
    complete = models.BooleanField(null=True)
    tipo = models.ForeignKey(Tipo_Gasto, on_delete=models.CASCADE, null=True)
    pagada = models.BooleanField(default=False)
    transferencia_finanzas = models.BooleanField(default=False)
    autorizar = models.BooleanField(null=True, default=None)
    autorizar2 = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(null=True)
    inicio_form = models.DateTimeField(null=True)
    #created_at_time = models.TimeField(null=True)
    approved_at = models.DateTimeField(null=True)
    #approved_at_time = models.TimeField(null=True)
    approbado_fecha2 = models.DateTimeField(null=True)
    #approved_at_time2 = models.TimeField(null=True)
    facturas_completas = models.BooleanField(default=False)
    comentario = models.TextField(null=True, blank=True)
    comentariotesorero = models.TextField(null=True, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE,null=True, blank = True )
    distrito = models.ForeignKey(Distrito, on_delete = models.CASCADE, null=True)
    proveedor = models.ForeignKey(Proveedor_direcciones, on_delete = models.CASCADE, null=True, blank = True)
    verificacion_facturas = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='rh', blank = True)
    cerrar_sin_pago_completo = models.BooleanField(default=False)
    persona_cierre = models.ForeignKey('user.Profile', on_delete = models.CASCADE, null=True, blank=True, related_name='Cierre_Gasto')
    fecha_cierre = models.DateField(null=True, blank = True)
    comentario_cierre = models.TextField(blank=True, null=True)
    dispersion = models.BooleanField(default=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    para_pago = models.BooleanField(default=False)
    manda_pago = models.ForeignKey('user.Profile', on_delete = models.CASCADE, null=True, blank=True, related_name='manda_pago_gasto')
    parcial = models.DecimalField(max_digits=14,decimal_places=2, default=0)

    class Meta:
        unique_together = ('folio', 'distrito',)

    @property
    def get_validado(self):
        productos = self.articulos.all()
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
        pagado = self.pagosg.filter(Q(tipo__id = 1)| Q(tipo__isnull=True))
        pagado= pagado.filter(hecho=True)
        total = sum([pago.monto for pago in pagado])
        return total
    
    @property
    def monto_pagado_transferencia(self):
        pagado = self.pagosg.filter(tipo__id = 3)
        pagado= pagado.filter(hecho=True) 
        total = sum([pago.monto for pago in pagado])
        return total


    @property
    def get_subtotal_solicitud(self):
        productos = self.articulos.all()
        productos = productos.filter(completo=True)
        total = sum([producto.get_subtotal for producto in productos])
        return total

    @property
    def get_total_impuesto(self):
        productos = self.articulos.all()
        productos = productos.filter(completo=True)
        suma = round(sum([(producto.get_iva + producto.get_otros_impuestos) for producto in productos]),2)
        return suma

    @property
    def get_total_solicitud(self):
        productos = self.articulos.all()
        print(productos)
        productos = productos.filter(completo=True)
        total = sum([producto.total_parcial for producto in productos])
        return total

    def __str__(self):
        return f'{self.folio}'
    
    
class Porcentaje_iva(models.Model):
    porcentaje = models.DecimalField(max_digits=2, decimal_places=0, null=True)

    def __str__(self):
        return f'{self.porcentaje}'

class Articulo_Gasto(models.Model):
    staff = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    clase = models.BooleanField(null=True, default=False)   #Se refiere a si el producto es del True == almacén o entrara al almacén o si va por fuera
    producto = models.ForeignKey(Product, on_delete = models.CASCADE, null=True)
    comentario = models.TextField(null=True)
    descripcion = models.CharField(max_length=255, null=True)
    otros_impuestos = models.DecimalField(default=0,max_digits=14, decimal_places=4, null=True, blank=True)
    impuestos_retenidos = models.DecimalField(default=0, max_digits=14, decimal_places=4, null=True, blank=True)
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete = models.CASCADE, null=True,  related_name ='articulos')
    cantidad = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=6, null=True)
    iva = models.ForeignKey(Porcentaje_iva, on_delete = models.CASCADE, null=True, blank=True)
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
        if self.precio_unitario and self.cantidad and self.iva:
            if self.iva.id == 1:
                valor_iva = .1
            elif self.iva.id == 2:
                valor_iva = .16
            else:
                valor_iva = 0
            iva = self.precio_unitario * self.cantidad *  Decimal(str(valor_iva)) #Esta conversión (Decimal(str ....es una estrategia para convertir float a decimal sin introducir errores
        return iva

    @property
    def get_otros_impuestos(self):
        impuestos = 0
        if self.otros_impuestos:
            if self.impuestos_retenidos:
                impuestos = round(self.otros_impuestos - self.impuestos_retenidos, 2)
            else:
                impuestos = round(self.otros_impuestos,2)
        else:
            if self.impuestos_retenidos:
                impuestos = round(-self.impuestos_retenidos, 2)


        return impuestos

    @property
    def total_parcial(self):
        total = round(self.get_subtotal + self.get_iva + self.get_otros_impuestos,2)
        return total
    
class Factura(models.Model):
    solicitud_gasto = models.ForeignKey(Solicitud_Gasto, on_delete=models.CASCADE, related_name='facturas', null=True)
    archivo_pdf = models.FileField(blank=True, null=True, upload_to='facturastb', validators=[FileExtensionValidator(['pdf'])])
    archivo_xml = models.FileField(blank=True, null=True, upload_to='xmltb', validators=[FileExtensionValidator(['xml'])])
    fecha_subida= models.DateTimeField(null=True, blank=True)
    hecho = models.BooleanField(default=False)
    monto = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    es_repetida = models.BooleanField(default=False)
    uuid = models.CharField(max_length=36, blank=True, null=True, unique = True, db_index=True)
    fecha_timbrado = models.DateTimeField(null=True,blank=True)
    autorizada = models.BooleanField(null=True, default=None)
    autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='autorizado_factura_gasto')
    autorizada_el = models.DateTimeField(null=True)
    estado_sat = models.CharField(max_length=50, null=True, blank=True)
    fecha_validacion_sat = models.DateTimeField(null=True, blank=True)

    @property   
    def emisor(self):
        if not self.archivo_xml:
            print(f"Error: {self.archivo_xml.path} no tiene un archivo asociado.")
            return None
        
        try:
            tree = ET.parse(self.archivo_xml.path)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"Error al parsear el archivo XML:{self.id}: {e}")
            return None  # Salir de la función si ocurre un error
        # Manejo adicional del error
        #tree = ET.parse(self.archivo_xml.path)
        
        version = root.tag
        prefix = ''  # Asegúrate de definir prefix inicialmente
        ns = {}
        if 'http://www.sat.gob.mx/cfd/3' in version:
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/3',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                'if': 'https://www.interfactura.com/Schemas/Documentos',
                }
            prefix = 'cfdi'
        elif 'http://www.sat.gob.mx/EstadoDeCuentaCombustible12' in version:
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4', 
                'ecc12': 'http://www.sat.gob.mx/EstadoDeCuentaCombustible12', 
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
                }
            prefix = 'ecc12'  
        elif 'http://www.sat.gob.mx/cfd/4' in version:
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4', 
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital', 
                'if': 'https://www.interfactura.com/Schemas/Documentos',
                }
            prefix = 'cfdi'
        #elif 'GCG_EInvoiceCFDIReport_MX.Report' in version:
            # Esquema GCG_EInvoiceCFDIReport_MX.Report
        #    ns = {}  # No necesita un espacio de nombres específico
        #    prefix = 'gcg'  # Prefijo ficticio para manejar este caso
        else:
            print(f"Versión del documento XML no reconocida: {self.id}")
            return None

        #print(prefix)
        emisor = root.find(f'cfdi:Emisor', ns)
        receptor = root.find(f'cfdi:Receptor', ns)
        conceptos = root.find(f'{prefix}:Conceptos', ns)
        impuestos = root.find(f'{prefix}:Impuestos', ns)
        complemento = root.find(f'cfdi:Complemento', ns)
        addenda = root.find(f'{prefix}:Addenda', ns)
         # Extraer la cadena original
        cadena_original = None
        if addenda is not None:
            factura_interfactura = addenda.find('if:FacturaInterfactura', ns)
            if factura_interfactura is not None:
                encabezado = factura_interfactura.find('if:Encabezado', ns)
                if encabezado is not None:
                    cadena_original = encabezado.get('cadenaOriginal', 'Cadena original no disponible')
        
        impuestos_total = 0.0
        iva_retenido = 0.0
        isr_retenido = 0.0
        resultados = []
        if prefix == 'cfdi':
            conceptos = root.find(f'{prefix}:Conceptos', ns)
            for concepto in conceptos.findall(f'{prefix}:Concepto', ns):
                descripcion = concepto.get('Descripcion')
                cantidad = concepto.get('Cantidad')
                precio = concepto.get('ValorUnitario')
                importe = concepto.get('Importe')
                unidad = concepto.get('Unidad') or concepto.get('ClaveUnidad')
                clave = concepto.get('ClaveProdServ')
                impuesto = concepto.find(f'{prefix}:Impuestos/{prefix}:Traslados/{prefix}:Traslado', ns)
                impuesto_valor = impuesto.get('Importe') if impuesto is not None else 'N/A'
                tipo_factor = impuesto.get('TipoFactor') if impuesto is not None else 'N/A'
                tasa_cuota = impuesto.get('TasaOCuota') if impuesto is not None else 'N/A'
                resultados.append({
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio': precio,
                    'clave': clave,
                    'importe': importe,
                    'unidad': unidad,
                    'impuesto': impuesto_valor,
                    'tipo_factor': tipo_factor,
                    'tasa_cuota': tasa_cuota,
                })
            total = root.get('Total')
            subtotal = root.get('SubTotal')
            impuestos_total = impuestos.get('TotalImpuestosTrasladados') if impuestos is not None else None
            # Procesar retenciones
            retenciones = impuestos.find(f'{prefix}:Retenciones', ns) if impuestos is not None else None
            if retenciones is not None:
                for retencion in retenciones.findall(f'{prefix}:Retencion', ns):
                    impuesto_tipo = retencion.get('Impuesto')
                    retencion_valor = retencion.get('Importe', '0')
                    if impuesto_tipo == '002':
                        iva_retenido = float(retencion_valor)
                    elif impuesto_tipo == '001':
                        isr_retenido = float(retencion_valor)
                
        elif prefix == 'ecc12':
            estado_cuenta = complemento.find('ecc12:EstadoDeCuentaCombustible', ns)
            conceptos = estado_cuenta.find('ecc12:Conceptos', ns)
            for concepto in conceptos.findall(f'{prefix}:ConceptoEstadoDeCuentaCombustible', ns):
                descripcion = concepto.get('NombreCombustible')
                cantidad = concepto.get('Cantidad')
                precio = concepto.get('ValorUnitario')
                importe = concepto.get('Importe')
                unidad = concepto.get('TipoCombustible')
                clave = concepto.get('Identificador')
                impuesto = concepto.find(f'{prefix}:Traslados/{prefix}:Traslado', ns)
                impuesto_valor = impuesto.get('Importe') if impuesto is not None else 'N/A'
                tipo_factor = impuesto.get('Impuesto') if impuesto is not None else 'N/A'
                tasa_cuota = impuesto.get('TasaOCuota') if impuesto is not None else 'N/A'
                resultados.append({
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio': precio,
                    'clave': clave,
                    'importe': importe,
                    'unidad': unidad,
                    'impuesto': impuesto_valor,
                    'tipo_factor': tipo_factor,
                    'tasa_cuota': tasa_cuota,
                })
                if impuesto_valor != 'N/A':
                    impuestos_total += float(impuesto_valor)
           
            total = estado_cuenta.get('Total')
            subtotal = estado_cuenta.get('SubTotal')
           
            

        rfc_emisor = emisor.get('Rfc')
        nombre_emisor = emisor.get('Nombre')
        regimen_fiscal_emisor = emisor.get('RegimenFiscal')
        moneda = root.get('Moneda')
        
        
        rfc_receptor = receptor.get('Rfc')
        nombre_receptor = receptor.get('Nombre')
        regimen_fiscal_receptor = receptor.get('RegimenFiscalReceptor')
        domicilio_fiscal_receptor = receptor.get('DomicilioFiscalReceptor')
        uso_cfdi = receptor.get('UsoCFDI')
        
       
        
        # Extraer la cadena original
        #cadena_original = encabezado.get('cadenaOriginal', 'Cadena original no disponible') or None

        # Datos adicionales del complemento
        uuid, sello_cfd, sello_sat, fecha_timbrado, no_certificadoSAT  = '', '', '', '', ''
        if complemento is not None:
            timbre_fiscal = complemento.find('tfd:TimbreFiscalDigital', ns)
            #print(timbre_fiscal)
            if timbre_fiscal is not None:
                uuid = timbre_fiscal.get('UUID')
                sello_cfd = timbre_fiscal.get('SelloCFD')
                sello_sat = timbre_fiscal.get('SelloSAT')
                fecha_timbrado = timbre_fiscal.get('FechaTimbrado')
                no_certificadoSAT = timbre_fiscal.get('NoCertificadoSAT')

        fecha = root.get('Fecha')
        lugar_expedicion = root.get('LugarExpedicion')
        folio = root.get('Folio')
        no_certificado = root.get('NoCertificado')
        

        # Campos adicionales opcionales con valores predeterminados
        forma_pago = root.get('FormaPago', 'Por definir')
        metodo_pago = root.get('MetodoPago', 'Por definir')

        return {
            'no_certificadoSAT':no_certificadoSAT,
            'cadena_original': cadena_original,
            'uso_cfdi': uso_cfdi,
            'rfc_emisor': rfc_emisor,
            'nombre_emisor': nombre_emisor,
            'regimen_fiscal_emisor': regimen_fiscal_emisor,
            'rfc_receptor': rfc_receptor,
            'nombre_receptor': nombre_receptor,
            'regimen_fiscal_receptor':regimen_fiscal_receptor,
            'codigo_postal':domicilio_fiscal_receptor,
            'total': total,
            'subtotal': subtotal,
            'impuestos': impuestos_total,
            'iva_retenido': iva_retenido,
            'isr_retenido': isr_retenido,
            'fecha': fecha,
            'moneda': moneda,
            'lugar_expedicion': lugar_expedicion,
            'folio': folio,
            'no_certificado': no_certificado,
            'uuid': uuid,
            'sello_cfd': sello_cfd,
            'sello_sat': sello_sat,
            'fecha_timbrado': fecha_timbrado,
            'resultados': resultados,
            'forma_pago': forma_pago,
            'metodo_pago': metodo_pago
        }



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

class ValeRosa(models.Model):
    gasto = models.ForeignKey(Solicitud_Gasto, on_delete=models.CASCADE, related_name='vales_rosa', null=True, blank=True)
    viatico = models.ForeignKey(Solicitud_Viatico, on_delete=models.CASCADE, related_name='vales_rosa_viatico', null=True, blank=True)
    motivo = models.TextField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    creado_por = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='vale_rosa_creado', null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    aprobado_por = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='vale_rosa_aprobado', null=True, blank=True)
    aprobado_en = models.DateTimeField(null=True, blank=True)
    esta_aprobado = models.BooleanField(null=True, default=None)

    comentarios = models.TextField(null=True, blank=True)
    comprobante_pdf = models.FileField(upload_to='comprobantes_vales', null=True, blank=True, validators=[FileExtensionValidator(['pdf'])])

    def __str__(self):
        if self.gasto:
            return f"Vale Rosa #{self.id} para Gasto #{self.gasto.folio}"
        elif self.viatico:
            return f"Vale Rosa #{self.id} para Viático #{self.viatico.folio}"
        return f"Vale Rosa #{self.id} (sin destino)"
    
class TipoArchivoSoporte(models.Model):
    nombre = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nombre
    
class ArchivoSoporte(models.Model):
    solicitud = models.ForeignKey(Solicitud_Gasto, on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoArchivoSoporte, on_delete=models.PROTECT)
    archivo = models.FileField(upload_to='soportes')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo.nombre} - {self.solicitud.folio if self.solicitud.folio else 'Nueva'}"

