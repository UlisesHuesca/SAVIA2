from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from defusedxml import ElementTree as ET
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class CFDIError(Exception):
    """Error controlado durante la lectura de un CFDI."""


def obtener_nombre_etiqueta(elemento):
    return elemento.tag.split('}')[-1]


def buscar_elemento(elemento, nombre):
    for hijo in elemento.iter():
        if obtener_nombre_etiqueta(hijo) == nombre:
            return hijo

    return None


def buscar_hijo_directo(elemento, nombre):
    for hijo in elemento:
        if obtener_nombre_etiqueta(hijo) == nombre:
            return hijo

    return None


def convertir_decimal(valor, default='0'):
    if valor in (None, ''):
        return Decimal(default)

    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def convertir_fecha(valor):
    if not valor:
        return None

    fecha = parse_datetime(valor)

    if fecha is None:
        formatos = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
        ]

        for formato in formatos:
            try:
                fecha = datetime.strptime(valor, formato)
                break
            except ValueError:
                continue

    if fecha is None:
        raise CFDIError(f'La fecha "{valor}" no tiene un formato válido.')

    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(
            fecha,
            timezone.get_current_timezone(),
        )

    return fecha


def normalizar_uuid(valor):
    if not valor:
        raise CFDIError(
            'El XML no contiene un UUID en el Timbre Fiscal Digital.'
        )

    try:
        return str(UUID(valor.strip())).upper()
    except (ValueError, AttributeError):
        raise CFDIError(f'El UUID "{valor}" no es válido.')


def parsear_cfdi(archivo):
    """
    Recibe un UploadedFile de Django y devuelve los datos principales
    del CFDI. Al finalizar regresa el archivo a la posición inicial.
    """

    try:
        archivo.seek(0)
        contenido = archivo.read()
        archivo.seek(0)

        raiz = ET.fromstring(contenido)

    except ET.ParseError as error:
        archivo.seek(0)
        raise CFDIError(f'El archivo no contiene un XML válido: {error}')

    except Exception as error:
        archivo.seek(0)
        raise CFDIError(f'No fue posible leer el archivo: {error}')

    if obtener_nombre_etiqueta(raiz) != 'Comprobante':
        raise CFDIError(
            'El archivo XML no corresponde a un comprobante CFDI.'
        )

    emisor = buscar_hijo_directo(raiz, 'Emisor')
    receptor = buscar_hijo_directo(raiz, 'Receptor')
    impuestos = buscar_hijo_directo(raiz, 'Impuestos')
    timbre = buscar_elemento(raiz, 'TimbreFiscalDigital')

    if emisor is None:
        raise CFDIError('El XML no contiene la información del emisor.')

    if receptor is None:
        raise CFDIError('El XML no contiene la información del receptor.')

    if timbre is None:
        raise CFDIError(
            'El XML no contiene el Timbre Fiscal Digital.'
        )

    uuid = normalizar_uuid(timbre.get('UUID'))

    rfc_emisor = (emisor.get('Rfc') or '').strip().upper()
    rfc_receptor = (receptor.get('Rfc') or '').strip().upper()

    if not rfc_emisor:
        raise CFDIError('El XML no contiene el RFC del emisor.')

    if not rfc_receptor:
        raise CFDIError('El XML no contiene el RFC del receptor.')

    impuestos_trasladados = Decimal('0')
    impuestos_retenidos = Decimal('0')

    if impuestos is not None:
        impuestos_trasladados = convertir_decimal(
            impuestos.get('TotalImpuestosTrasladados')
        )
        impuestos_retenidos = convertir_decimal(
            impuestos.get('TotalImpuestosRetenidos')
        )

    datos = {
        'uuid': uuid,
        'version_cfdi': (
            raiz.get('Version') or
            raiz.get('version') or
            ''
        ),
        'tipo_comprobante': raiz.get('TipoDeComprobante'),
        'serie': raiz.get('Serie'),
        'folio': raiz.get('Folio'),
        'fecha_emision': convertir_fecha(raiz.get('Fecha')),
        'fecha_timbrado': convertir_fecha(
            timbre.get('FechaTimbrado')
        ),

        'rfc_emisor': rfc_emisor,
        'nombre_emisor': emisor.get('Nombre'),
        'regimen_fiscal_emisor': emisor.get('RegimenFiscal'),

        'rfc_receptor': rfc_receptor,
        'nombre_receptor': receptor.get('Nombre'),
        'regimen_fiscal_receptor': receptor.get(
            'RegimenFiscalReceptor'
        ),
        'domicilio_fiscal_receptor': receptor.get(
            'DomicilioFiscalReceptor'
        ),
        'uso_cfdi': receptor.get('UsoCFDI'),

        'subtotal': convertir_decimal(raiz.get('SubTotal')),
        'impuestos_trasladados': impuestos_trasladados,
        'impuestos_retenidos': impuestos_retenidos,
        'total': convertir_decimal(raiz.get('Total')),

        'moneda': raiz.get('Moneda'),
        'tipo_cambio': (
            convertir_decimal(raiz.get('TipoCambio'))
            if raiz.get('TipoCambio')
            else None
        ),
        'forma_pago': raiz.get('FormaPago'),
        'metodo_pago': raiz.get('MetodoPago'),
        'lugar_expedicion': raiz.get('LugarExpedicion'),
    }

    archivo.seek(0)

    return datos