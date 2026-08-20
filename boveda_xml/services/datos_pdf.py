from decimal import Decimal, InvalidOperation

from defusedxml import ElementTree as ET


class ErrorDatosPDF(Exception):
    pass


def nombre_etiqueta(elemento):
    return elemento.tag.split('}')[-1]


def buscar_elemento(elemento, nombre):
    for hijo in elemento.iter():
        if nombre_etiqueta(hijo) == nombre:
            return hijo

    return None


def buscar_hijo_directo(elemento, nombre):
    if elemento is None:
        return None

    for hijo in elemento:
        if nombre_etiqueta(hijo) == nombre:
            return hijo

    return None


def convertir_decimal(valor):
    try:
        return Decimal(str(valor or '0'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def extraer_detalles_pdf(archivo_xml):
    try:
        archivo_xml.open('rb')
        archivo_xml.seek(0)
        raiz = ET.parse(archivo_xml).getroot()
    except (ET.ParseError, FileNotFoundError, OSError) as error:
        raise ErrorDatosPDF(
            f'No fue posible leer el XML: {error}'
        )
    finally:
        try:
            archivo_xml.close()
        except Exception:
            pass

    conceptos_xml = buscar_hijo_directo(raiz, 'Conceptos')
    resultados = []

    if conceptos_xml is not None:
        for concepto in conceptos_xml:
            if nombre_etiqueta(concepto) != 'Concepto':
                continue

            impuestos_concepto = buscar_hijo_directo(
                concepto,
                'Impuestos',
            )
            traslados = buscar_hijo_directo(
                impuestos_concepto,
                'Traslados',
            )

            importe_impuesto = Decimal('0')
            tasas = []

            if traslados is not None:
                for traslado in traslados:
                    if nombre_etiqueta(traslado) != 'Traslado':
                        continue

                    importe_impuesto += convertir_decimal(
                        traslado.get('Importe')
                    )

                    tasa = traslado.get('TasaOCuota')

                    if tasa:
                        tasas.append(tasa)

            resultados.append({
                'descripcion': concepto.get('Descripcion') or '',
                'cantidad': concepto.get('Cantidad') or '0',
                'precio': concepto.get('ValorUnitario') or '0',
                'importe': concepto.get('Importe') or '0',
                'unidad': (
                    concepto.get('Unidad') or
                    concepto.get('ClaveUnidad') or
                    ''
                ),
                'clave': concepto.get('ClaveProdServ') or '',
                'impuesto': str(importe_impuesto),
                'tasa_cuota': ', '.join(tasas) if tasas else '0',
            })

    timbre = buscar_elemento(raiz, 'TimbreFiscalDigital')

    sello_cfd = ''
    sello_sat = ''
    certificado_sat = ''

    if timbre is not None:
        sello_cfd = timbre.get('SelloCFD') or ''
        sello_sat = timbre.get('SelloSAT') or ''
        certificado_sat = timbre.get('NoCertificadoSAT') or ''

    return {
        'resultados': resultados,
        'sello_cfd': sello_cfd or raiz.get('Sello') or '',
        'sello_sat': sello_sat,
        'no_certificado': raiz.get('NoCertificado') or '',
        'no_certificadoSAT': certificado_sat,
        'cadena_original': '',
    }

def preparar_datos_pdf(factura):
    detalles = extraer_detalles_pdf(factura.archivo_xml)

    data = {
        # Datos almacenados
        'uuid': factura.uuid,
        'rfc_emisor': factura.rfc_emisor,
        'nombre_emisor': factura.nombre_emisor or '',
        'regimen_fiscal_emisor': (
            factura.regimen_fiscal_emisor or ''
        ),
        'rfc_receptor': factura.rfc_receptor,
        'nombre_receptor': factura.nombre_receptor or '',
        'regimen_fiscal_receptor': (
            factura.regimen_fiscal_receptor or ''
        ),
        'codigo_postal': (
            factura.domicilio_fiscal_receptor or ''
        ),
        'uso_cfdi': factura.uso_cfdi or '',
        'total': factura.total or Decimal('0'),
        'subtotal': factura.subtotal or Decimal('0'),
        'impuestos': (
            factura.impuestos_trasladados or Decimal('0')
        ),
        'impuestos_retenidos': (
            factura.impuestos_retenidos or Decimal('0')
        ),
        'fecha': factura.fecha_emision,
        'fecha_timbrado': factura.fecha_timbrado,
        'moneda': factura.moneda or '',
        'lugar_expedicion': factura.lugar_expedicion or '',
        'forma_pago': factura.forma_pago or '',
        'metodo_pago': factura.metodo_pago or '',

        # Datos extraídos del XML
        **detalles,
    }

    return data