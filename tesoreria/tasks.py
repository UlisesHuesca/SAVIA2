from .models import Facturas 
from gastos.models import Factura
from viaticos.models import Viaticos_Factura
from celery import shared_task
import time
from django.utils.timezone import now
import time, logging, xml.etree.ElementTree as ET, decimal
from zeep import Client
import logging


logger = logging.getLogger('celery')

def extraer_datos_validacion(xml_file_path, factura):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        version = root.get("Version", "3.3")
        ns = {
            'cfdi': f'http://www.sat.gob.mx/cfd/{version[0]}',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
        }

        emisor = root.find("cfdi:Emisor", ns)
        receptor = root.find("cfdi:Receptor", ns)
        timbre = root.find(".//tfd:TimbreFiscalDigital", ns)

        uuid = timbre.attrib.get('UUID')
        rfc_emisor = emisor.attrib.get('Rfc')
        rfc_receptor = receptor.attrib.get('Rfc')
        total = root.attrib.get('Total')

        if uuid and rfc_emisor and rfc_receptor:
            resultado = obtener_estado_cfdi(uuid, rfc_emisor, rfc_receptor, total)
            factura.estado_sat = resultado['EstadoSAT']
            factura.fecha_validacion_sat = now()
            factura.save()
            logging.info(f"✔ Factura ID {factura.id} validada | UUID: {uuid} | Estado: {factura.estado_sat}")
        else:
            factura.estado_sat = 'Datos insuficientes'
            factura.fecha_validacion_sat = now()
            factura.save()
            logging.warning(f"✖ Factura ID {factura.id} sin datos suficientes para validar")


    except Exception as e:
        factura.estado_sat = f"Error: {str(e)}"
        factura.fecha_validacion_sat = now()
        factura.save()
        logging.error(f"✖ Error al validar factura ID {factura.id}: {e}")


def obtener_estado_cfdi(uuid, rfc_emisor, rfc_receptor, total_decimal):
    """Consulta el estatus de un CFDI ante el SAT."""
    wsdl_url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
    client = Client(wsdl=wsdl_url)

    total_str = f"{decimal.Decimal(total_decimal):017.6f}"
    expresion = f'?re={rfc_emisor}&rr={rfc_receptor}&tt={total_str}&id={uuid}'
    logger.info(f"📤 Validando SAT UUID={uuid} | Emisor={rfc_emisor}")
    try:
        respuesta = client.service.Consulta(expresionImpresa=expresion)
        return {
            'EstadoSAT': respuesta.Estado,
            'EsCancelable': respuesta.EsCancelable,
            'EstatusCancelacion': respuesta.EstatusCancelacion
        }
    except Exception as e:
        return {
            'EstadoSAT': 'Error',
            'EsCancelable': 'N/A',
            'EstatusCancelacion': str(e)
        }


@shared_task
def validar_lote_facturas(facturas_gasto_ids, facturas_compra_ids, facturas_viatico_ids):
    logger.info("🚀 Tarea Celery: validar_lote_facturas iniciada")
    for id in facturas_gasto_ids:
        logger.info(f"📄 Procesando GASTO ID: {id}")
        factura = Factura.objects.get(id=id)
        if factura.archivo_xml:
            extraer_datos_validacion(factura.archivo_xml.path, factura)
            time.sleep(1.5)

    for id in facturas_compra_ids:
        logger.info(f"📄 Procesando COMPRA ID: {id}")
        factura = Facturas.objects.get(id=id)
        if factura.factura_xml:
            extraer_datos_validacion(factura.factura_xml.path, factura)
            time.sleep(1.5)

    for id in facturas_viatico_ids:
        logger.info(f"📄 Procesando VIATICO ID: {id}")
        factura = Viaticos_Factura.objects.get(id=id)
        if factura.factura_xml:
            extraer_datos_validacion(factura.factura_xml.path, factura)
            time.sleep(1.5)

    logger.info("✅ Tarea validar_lote_facturas finalizada.")