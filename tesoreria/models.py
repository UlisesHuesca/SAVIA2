from django.db import models
from compras.models import Compra, Moneda, Banco
from user.models import Profile, Distrito, Banco, Empresa
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico
#from djmoney.models.fields import MoneyField
from simple_history.models import HistoricalRecords
from django.core.validators import FileExtensionValidator
import xml.etree.ElementTree as ET
from .utils import encontrar_variables, extraer_texto_pdf_prop
import os
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
    empresa = models.ForeignKey(Empresa, on_delete= models.CASCADE, null=True)


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
    saldo = models.DecimalField(max_digits=14,decimal_places=4, null=True, default=0)
    indice = models.IntegerField(null=True, blank=True)  # Nuevo campo para el índice

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
    oc = models.ForeignKey(Compra, on_delete = models.CASCADE, null=True, related_name='facturas')
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='uploaded_by')
    fecha_subido = models.DateField(null=True, blank=True)
    hora_subido = models.TimeField(null=True, blank=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    factura_pdf = models.FileField(blank=True, null=True, upload_to='facturas',validators=[FileExtensionValidator(['pdf'])])
    factura_xml = models.FileField(blank=True, null=True, upload_to='xml', validators=[FileExtensionValidator(['xml'])])
    uuid = models.CharField(max_length=36, blank=True, null=True, unique = True, db_index=True) #unique = True
    fecha_timbrado = models.DateTimeField(null=True,blank=True)
    autorizada = models.BooleanField(null=True, default=None)
    autorizada_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='autorizado_factura_compra')
    autorizada_el = models.DateTimeField(null=True)

    def __str__(self):
        return f'id:{self.id} oc:{self.oc}'
    
    @property   
    def emisor(self):
        if not self.factura_xml:
            print(f"Error: {self.id} no tiene un archivo asociado.")
            return None
        
        try:
            print(self.id)
            tree = ET.parse(self.factura_xml.path)
            root = tree.getroot()  # Si tiene éxito, obtener la raíz
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Error al parsear el archivo XML:{self.id}: {e}")
            return None  # Salir de la función si ocurre un error
        # Manejo adicional del error
        #tree = ET.parse(self.archivo_xml.path)
        root = tree.getroot()
        version = root.tag
        print(version)
        ns = {}
        prefix = ''  # Asegúrate de definir prefix inicialmente
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
           
        #elif prefix == 'gcg':
            # Extraer UUID del nodo Tablix5, en el atributo Textbox61
        #    uuid = root.find(".//Tablix5").attrib.get("Textbox61", "UUID no encontrado")
        #    total = root.find(".//Report").attrib.get("Textbox52", "Total no encontrado")
        #    for detalle in root.findall(".//Details5"):
        #        descripcion = detalle.attrib.get("Textbox133", "Descripción no encontrada")
        #        monto = detalle.attrib.get("Textbox79", "Monto no encontrado")
        #        impuestos.append({'descripcion': descripcion, 'monto': monto})

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
        uuid, sello_cfd, sello_sat, fecha_timbrado, no_certificadoSAT = '', '', '', '',''
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
    
class Saldo_Cuenta(models.Model):
    cuenta = models.ForeignKey (Cuenta, on_delete = models.CASCADE, null=True)
    updated = models.DateField(null=True, blank=True)
    fecha_inicial = models.DateField(null=True)
    updated_by = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True)
    monto_inicial = models.DecimalField(max_digits=14,decimal_places=4, null=True, default=0)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    history = HistoricalRecords(history_change_reason_field=models.TextField(null=True))

    def __str__(self):
        return f'id:{self.cuenta}'
    

class Complemento_Pago(models.Model):
    factura = models.ForeignKey(Facturas, on_delete = models.CASCADE, null=True, related_name='complemento')
    subido_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='complemento_subido_por')
    fecha_subido = models.DateField(null=True, blank=True)
    hora_subido = models.TimeField(null=True, blank=True)
    comentario = models.CharField(max_length=100, null=True, blank=True)
    hecho = models.BooleanField(default=False)
    complemento_pdf = models.FileField(blank=True, null=True, upload_to='complementos_pdf',validators=[FileExtensionValidator(['pdf'])])
    cmplemento_xml = models.FileField(blank=True, null=True, upload_to='complementos_xml', validators=[FileExtensionValidator(['xml'])])
    uuid = models.CharField(max_length=36, blank=True, null=True, unique = True, db_index=True) #unique = True
    fecha_timbrado = models.DateTimeField(null=True,blank=True)
    validado = models.BooleanField(null=True, default=None)
    validado_por = models.ForeignKey(Profile, on_delete = models.CASCADE, null=True, related_name='validado_complemento')
    validado_fecha = models.DateTimeField(null=True)

    import xml.etree.ElementTree as ET

    @property
    def emisor(self):
        if not self.factura_xml:
            print(f"Error: {self.id} no tiene un archivo asociado.")
            return None

        try:
            print(self.id)
            tree = ET.parse(self.factura_xml.path)
            root = tree.getroot()
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Error al parsear el archivo XML: {self.id}: {e}")
            return None

        # Definir los espacios de nombres según la versión
        ns = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
            'pago20': 'http://www.sat.gob.mx/Pagos20'
        }

        # Extraer información del emisor y receptor
        emisor = root.find('cfdi:Emisor', ns)
        receptor = root.find('cfdi:Receptor', ns)

        if emisor is None or receptor is None:
            print(f"Error: No se encontraron los nodos Emisor/Receptor en {self.id}")
            return None

        rfc_emisor = emisor.get('Rfc')
        nombre_emisor = emisor.get('Nombre')
        regimen_fiscal_emisor = emisor.get('RegimenFiscal')

        rfc_receptor = receptor.get('Rfc')
        nombre_receptor = receptor.get('Nombre')
        regimen_fiscal_receptor = receptor.get('RegimenFiscalReceptor')
        domicilio_fiscal_receptor = receptor.get('DomicilioFiscalReceptor')
        uso_cfdi = receptor.get('UsoCFDI')

        # Extraer información general
        total = root.get('Total')
        subtotal = root.get('SubTotal')
        moneda = root.get('Moneda')
        fecha = root.get('Fecha')
        lugar_expedicion = root.get('LugarExpedicion')
        folio = root.get('Folio')
        no_certificado = root.get('NoCertificado')
        forma_pago = root.get('FormaPago', 'Por definir')
        metodo_pago = root.get('MetodoPago', 'Por definir')

        # Extraer UUID y otros datos del Timbre Fiscal
        complemento = root.find('cfdi:Complemento', ns)
        uuid, sello_cfd, sello_sat, fecha_timbrado, no_certificadoSAT = '', '', '', '', ''

        # Extraer información del complemento de pagos
        docto_relacionado_id = None

        if complemento is not None:
            pagos = complemento.find('pago20:Pagos', ns)
            if pagos is not None:
                pago = pagos.find('pago20:Pago', ns)
                if pago is not None:
                    docto_relacionado = pago.find('pago20:DoctoRelacionado', ns)
                    if docto_relacionado is not None:
                        docto_relacionado_id = docto_relacionado.get('IdDocumento', 'ID No Disponible')

        # Extraer conceptos
        conceptos = root.findall('cfdi:Conceptos/cfdi:Concepto', ns)
        resultados = []
        for concepto in conceptos:
            resultados.append({
                'descripcion': concepto.get('Descripcion'),
                'cantidad': concepto.get('Cantidad'),
                'precio': concepto.get('ValorUnitario'),
                'clave': concepto.get('ClaveProdServ'),
                'importe': concepto.get('Importe'),
                'unidad': concepto.get('ClaveUnidad'),
                'impuesto': concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns).get('Importe', 'N/A') if concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns) else 'N/A',
                'tipo_factor': concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns).get('TipoFactor', 'N/A') if concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns) else 'N/A',
                'tasa_cuota': concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns).get('TasaOCuota', 'N/A') if concepto.find('cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado', ns) else 'N/A',
            })

        return {
            'no_certificadoSAT': no_certificadoSAT,
            'uso_cfdi': uso_cfdi,
            'rfc_emisor': rfc_emisor,
            'nombre_emisor': nombre_emisor,
            'regimen_fiscal_emisor': regimen_fiscal_emisor,
            'rfc_receptor': rfc_receptor,
            'nombre_receptor': nombre_receptor,
            'regimen_fiscal_receptor': regimen_fiscal_receptor,
            'codigo_postal': domicilio_fiscal_receptor,
            'total': total,
            'subtotal': subtotal,
            'fecha': fecha,
            'moneda': moneda,
            'lugar_expedicion': lugar_expedicion,
            'folio': folio,
            'no_certificado': no_certificado,
            'uuid': uuid,
            'sello_cfd': sello_cfd,
            'sello_sat': sello_sat,
            'fecha_timbrado': fecha_timbrado,
            'docto_relacionado_id': docto_relacionado_id,  # Nuevo campo
            'resultados': resultados,
            'forma_pago': forma_pago,
            'metodo_pago': metodo_pago
        }

