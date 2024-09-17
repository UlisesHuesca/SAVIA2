from django.db import models
from solicitudes.models import Proyecto, Subproyecto, Operacion
from user.models import Profile, Distrito
from dashboard.models import Inventario, Product
from django.core.validators import FileExtensionValidator
import decimal
import xml.etree.ElementTree as ET
import os

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
    uuid = models.CharField(max_length=36, blank=True, null=True, db_index=True, unique = True) #
    fecha_timbrado = models.DateTimeField(null=True,blank=True)
    #def __str__(self):
    #    return f'Factura de viatico:{self.solicitud_viatico.folio}'
    @property
    def emisor(self):
        if not self.factura_xml:
            print(f"Error: {self.factura_xml.path} no tiene un archivo asociado.")
            return None

        try:
            print(self.id)
            tree = ET.parse(self.factura_xml.path)
            root = tree.getroot()
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Error al parsear el archivo XML:{self.id}: {e}")
            return None  # Salir de la función si ocurre un error

        # Inicializar namespaces y prefijo
        ns = {}
        prefix = ''
        cristal = False

        # Identificar la versión del XML y ajustar namespaces
        version = root.tag
        if 'http://www.businessobjects.com/products/xml/CR2008Schema.xsd' in version:
            ns = {'cr': 'urn:crystal-reports:schemas:report-detail'}
            cristal = True
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

        resultados = []
        clasificaciones = set()

        if cristal:
            # Extracción de datos de Crystal Reports
            rfc = root.find('.//cr:Field[@FieldName="{dt_factura_internet.e_rfc}"]/cr:Value', ns).text
            nombre = root.find('.//cr:Field[@FieldName="{@Emisor1}"]/cr:Value', ns).text
            regimen_fiscal = root.find('.//cr:Field[@FieldName="{dt_factura_internet.e_regimen_fiscal}"]/cr:Value', ns).text
            total = root.find('.//cr:Field[@FieldName="{dt_factura_internet.total}"]/cr:Value', ns).text
            impuestos = root.find('.//cr:Field[@FieldName="{dt_factura_internet.iva}"]/cr:Value', ns).text
            conceptos = root.findall('.//cr:Details/cr:Section', ns)
            for concepto in conceptos:
                descripcion = concepto.find('.//cr:Field[@FieldName="{@Descripcion1}"]/cr:Value', ns).text
                cantidad = concepto.find('.//cr:Field[@FieldName="{dt_factura_internet.cantidad}"]/cr:Value', ns).text
                precio = concepto.find('.//cr:Field[@FieldName="{dt_factura_internet.valor_unitario}"]/cr:Value', ns).text
                clave_prod_serv = concepto.find('.//cr:Field[@FieldName="{@Descripcion1}"]/cr:Value', ns).text
                resultados.append((descripcion, cantidad, precio, clave_prod_serv))
            # Clasificación según Crystal Reports
            clasificacion_general = "Otros"  # Cristal no tiene claves específicas de CFDI
        else:
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
                    clave_prod_serv = concepto.get('ClaveProdServ')
                    impuesto = concepto.find(f'{prefix}:Impuestos/{prefix}:Traslados/{prefix}:Traslado', ns)
                    impuesto_valor = impuesto.get('Importe') if impuesto is not None else 'N/A'
                    tipo_factor = impuesto.get('TipoFactor') if impuesto is not None else 'N/A'
                    tasa_cuota = impuesto.get('TasaOCuota') if impuesto is not None else 'N/A'
                    # Clasificación según clave_prod_serv
                    if clave_prod_serv in ["90111800", "90111501"]:
                        clasificaciones.add("Hospedaje")
                    elif clave_prod_serv in ["15101514", "15101515"]:
                        clasificaciones.add("Gasolina")
                    elif clave_prod_serv in ["90101501", "50192500", "90101503", "90101500"]:
                        clasificaciones.add("Alimentos")
                    elif clave_prod_serv in ["95111602", "95111603"]:
                        clasificaciones.add("Peaje")
                    else:
                        clasificaciones.add("Otros")

                    resultados.append({
                        'descripcion': descripcion,
                        'cantidad': cantidad,
                        'precio': precio,
                        'clave_prod_serv': clave_prod_serv,
                        'importe': importe,
                        'unidad': unidad,
                        'impuesto': impuesto_valor,
                        'tipo_factor': tipo_factor,
                        'tasa_cuota': tasa_cuota,
                    })

                # Determinar clasificación general
                clasificacion_general = clasificaciones.pop() if len(clasificaciones) == 1 else "Mixto"
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
                clasificacion_general = "Otros" 
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
                'metodo_pago': metodo_pago,
                'clasificacion_general': clasificacion_general,
            }
                

        





