import re
import xml.etree.ElementTree as ET

#Se duplican funciones porque me arroja una referencia circular
#######################################################################
# Create your views here.
def eliminar_caracteres_invalidos(archivo_xml):
    # Definir la expresión regular para encontrar caracteres inválidos
    regex = re.compile(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]')

    # Leer el contenido del archivo XML
    xml_content = archivo_xml.read().decode('utf-8')

    if xml_content.startswith("o;?"):
        print('Detectado "o;?" en el inicio del XML')
        xml_content = xml_content[3:]

    # Eliminar caracteres inválidos según la expresión regular
    xml_content = regex.sub('', xml_content)

    # Volver a posicionar el puntero del archivo al principio
    archivo_xml.seek(0)

    # Guardar el contenido modificado en el archivo original
    archivo_xml.write(xml_content.encode('utf-8'))
    archivo_xml.truncate()  # Asegurarse de que no quede contenido sobrante

    print('Contenido corregido guardado exitosamente.')

    # Retornar el archivo con el contenido modificado
    return archivo_xml

def extraer_datos_del_xml(archivo_xml):
    """
    Extrae información de CFDI 3.3 y 4.0.

    Retorna:
        {
            "uuid": str,
            "fecha_timbrado": str,
            "rfc_receptor": str,
            "conceptos": list
        }

    Devuelve None si el XML no es válido
    o no contiene la información requerida.
    """

    ns_cfdi = {
        "3.3": "http://www.sat.gob.mx/cfd/3",
        "4.0": "http://www.sat.gob.mx/cfd/4",
    }

    ns_tfd = (
        "http://www.sat.gob.mx/TimbreFiscalDigital"
    )

    try:
        archivo_xml.seek(0)
        root = ET.parse(archivo_xml).getroot()

        version = root.get("Version") or root.get("version")
        namespace = ns_cfdi.get(version)

        if namespace is None:
            return None

        if root.tag != f"{{{namespace}}}Comprobante":
            return None

        receptor = root.find(f"{{{namespace}}}Receptor")
        # RFC emisor
        emisor = root.find(f"{{{namespace}}}Emisor")

        complemento = root.find(
            f"{{{namespace}}}Complemento"
        )

        if complemento is None:
            return None

        timbre = complemento.find(
            f"{{{ns_tfd}}}TimbreFiscalDigital"
        )

        if timbre is None:
            return None

        conceptos_xml = root.findall(
            f"{{{namespace}}}Conceptos/"
            f"{{{namespace}}}Concepto"
        )

        conceptos = [
            {
                "clave": concepto.get("ClaveProdServ", "").strip(),
                "descripcion": concepto.get("Descripcion", ""),
            }
            for concepto in conceptos_xml
        ]

        datos = {
            "uuid": timbre.get("UUID"),
            "fecha_timbrado": timbre.get("FechaTimbrado"),
            "rfc_emisor": (
                emisor.get("Rfc") if emisor is not None else None
            ),
            "rfc_receptor": (
                receptor.get("Rfc") if receptor is not None else None
            ),
            "tipo_comprobante": root.get("TipoDeComprobante"),
            "conceptos": conceptos,
        }

        if (
            not datos["uuid"]
            or not datos["fecha_timbrado"]
            or not datos["rfc_receptor"]
            or not conceptos
        ):
            return None

        return datos

    except (ET.ParseError, OSError, ValueError, TypeError):
        return None

    finally:
        archivo_xml.seek(0)