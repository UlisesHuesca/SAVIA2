import fitz  # PyMuPDF
import re
import PyPDF2
import os
import zipfile
from io import BytesIO

from datetime import date, datetime
from django.utils import timezone
import xml.etree.ElementTree as ET
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import numbers

# Importar desde sus módulos actuales:


# generar_pdf_nueva


# extraer_datos_xml_carpetas
def extraer_datos_xml_carpetas(xml_file, folio, fecha_subida, distrito, beneficiario, nombre_general, factura):
    """Extrae los datos clave de un archivo XML CFDI, compatible con diferentes versiones, incluyendo complementos de pago."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error al parsear {xml_file}: {e}")
        return {
            'Folio': folio,
            'Archivo': nombre_general,
            'Error': f"Archivo XML inválido: {e}"
        }

    # Detectar la versión del CFDI
    version = root.get("Version", "3.3")

    # Definir los espacios de nombres según la versión
    ns = {
        'cfdi': f'http://www.sat.gob.mx/cfd/{version[0]}',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        'pago20': 'http://www.sat.gob.mx/Pagos20'
    }

    emisor = root.find("cfdi:Emisor", ns)
    receptor = root.find("cfdi:Receptor", ns)
    complemento = root.find("cfdi:Complemento/tfd:TimbreFiscalDigital", ns)
    pagos = root.find("cfdi:Complemento/pago20:Pagos", ns)

    rfc_emisor = (emisor.get("Rfc", "").strip().upper() if emisor is not None else "")
    rfc_receptor = (receptor.get("Rfc", "").strip().upper() if receptor is not None else "")

      # Este es el total fiscal que utiliza la consulta SAT.
    # Para complementos de pago generalmente será 0.
    try:
        total_sat = float(root.get("Total", "0"))
    except (TypeError, ValueError):
        total_sat = 0


    # Verificar si es un complemento de pago
    es_complemento_pago = pagos is not None

    # Obtener datos generales
    fecha_emision = root.get('Fecha', '')
    fecha_emision_excel = datetime.strptime(fecha_emision, "%Y-%m-%dT%H:%M:%S") if fecha_emision else None

    # Datos específicos para complemento de pago
    if es_complemento_pago:
        pago = pagos.find("pago20:Pago", ns)
        if pago is not None:
            moneda = pago.get("MonedaP", "")
            monto_total = float(pago.get("Monto", "0"))
            forma_pago = pago.get("FormaDePagoP", "")
            metodo_pago = pago.get("MetodoPago", "N/A")  
        else:
            moneda = ""
            monto_total = 0
            forma_pago = ""
            metodo_pago = ""

        tipo_documento = "Complemento de Pago"
    else:
        moneda = root.get('Moneda', '')
        monto_total = float(root.get('Total', '0'))
        forma_pago = root.get('FormaPago', '')
        metodo_pago = root.get('MetodoPago', '')
        tipo_documento = "Factura"

    datos = {
        'Fecha subida': fecha_subida,
        'Beneficiario': beneficiario,
        'Folio': folio,
        'Distrito': distrito,  # Se agrega el distrito
        'Tipo de Documento': tipo_documento,
        'Fecha factura': fecha_emision_excel,
        'Razón Social': emisor.get('Nombre') if emisor is not None else '',
        'Folio Fiscal (UUID)': complemento.get('UUID') if complemento is not None else '',
        'Tipo de Moneda': moneda,
        'Método de Pago': metodo_pago,
        'Forma de pago': forma_pago,
        'Receptor (Empresa) Nombre': receptor.get('Nombre') if receptor is not None else '',
        'Archivo': nombre_general,
        'EstadoSAT': factura.estado_sat or '',
        'Fecha Validación SAT': timezone.localtime(factura.fecha_validacion_sat).strftime("%Y-%m-%d %H:%M:%S") if factura.fecha_validacion_sat else '',
        'RFC Emisor': rfc_emisor,
        'RFC Receptor': rfc_receptor,
        'Total SAT': total_sat,
        'Monto Total Factura': monto_total,
    }
    return datos


def encontrar_variables(texto):
    # Diccionario para almacenar los valores extraídos
    variables = {}

    # Definir los patrones de regex para cada variable
    patrones = {
        'fecha_valor': r'Fecha valor:\s*(\d{2}/\d{2}/\d{4})',
        'fecha': r'Fecha de aplicación:\s*(\d{2}/\d{2}/\d{4})', #r'Fecha de creación:\s*(\d{2}/\d{2}/\d{4})',
        'hora_operacion': r'(?:Hora de captura en el canal|Hora):\s*(\d{2}:\d{2}:\d{2})',
        'importe_operacion': r'(?:Importe|Importe de la operación):\s?([\d,.]+)',
        'cuenta_retiro': r'Cuenta de retiro:\s?(\d+)',
        'divisa_cuenta': r'Divisa de la cuenta:\s?([^\n\r]+)',
        'titulares': r'Titular de la cuenta:\s*([^\n\r]+?)(?=\s*Titular de la cuenta:|\n|\r|$)',
        #'titular_cuenta_2': r'Titular de la cuenta:\s*([^\n\r]+)\s*Titular de la cuenta:\s*([^\n\r]+)',
        'motivo_pago': r'(?:Motivo de pago|Concepto de pago):\s*([^\n\r]+)',
        'folio_unico': r'Folio único:\s*(\d+)'
    }
    
    # Buscar cada patrón y extraer el valor
    for clave, patron in patrones.items():
        if clave == 'titulares':
            coincidencias = re.findall(patron, texto, re.DOTALL | re.IGNORECASE)
            #print(coincidencias)
            if coincidencias:
                # Guardamos hasta 2 titulares si existen
                variables['titular_cuenta_1'] = coincidencias[0].strip() if len(coincidencias) > 0 else 'No disponible'
                variables['titular_cuenta_2'] = coincidencias[1].strip() if len(coincidencias) > 1 else 'No disponible'
            else:
                variables['titular_cuenta_1'] = 'No disponible'
                variables['titular_cuenta_2'] = 'No disponible'
        else:
            coincidencia = re.search(patron, texto, re.DOTALL)
            if coincidencia:
                valor = coincidencia.group(1).strip()
                if clave == 'importe_operacion':
                    valor = valor.replace('MXP', '').replace(',', '')
                variables[clave] = valor
            else:
                variables[clave] = 'No disponible'

    # Priorizar fecha valor cuando esté disponible
    if variables['fecha_valor'] != 'No disponible':
        variables['fecha'] = variables['fecha_valor']
    
    return variables

def limpiar_importe(importe_str):
    if not importe_str:
        return None
    # Eliminar símbolos monetarios, letras y comas
    limpio = re.sub(r"[^\d.]", "", importe_str)
    return limpio

def convertir_fecha_larga(fecha_larga):
    MESES_ES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    match = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", fecha_larga.lower())
    if not match:
        return None
    dia, mes_texto, anio = match.groups()
    mes = MESES_ES.get(mes_texto)
    if not mes:
        return None
    return f"{dia.zfill(2)}/{mes}/{anio}"

def encontrar_variables_bloques(bloques):
    datos = {}
    cuentas_encontradas = []

    # Convertimos a lista de dicts para más claridad
    bloques_struct = [
        {
            'x0': b[0],
            'y0': b[1],
            'x1': b[2],
            'y1': b[3],
            'text': b[4].strip(),
        }
        for b in bloques
    ]

    for bloque in bloques_struct:
        texto = bloque['text']
        y_centro = (bloque['y0'] + bloque['y1']) / 2

        # Buscar valores alineados a la derecha en la misma línea (±2 puntos de tolerancia)
        def buscar_valor_y_mayor_x(etiqueta_y):
            candidatos = [
                b for b in bloques_struct
                if abs(((b['y0'] + b['y1']) / 2) - etiqueta_y) < 2 and b['x0'] > 200
            ]
            if candidatos:
                return candidatos[0]['text']
            return None

        if texto == "Cuenta:":
            valor = buscar_valor_y_mayor_x(y_centro)
            if valor:
                cuenta_limpia = re.sub(r"[^\d]", "", valor)
                if len(cuenta_limpia) >= 4:
                    cuentas_encontradas.append(cuenta_limpia)

        elif texto == "Importe:":
            valor = buscar_valor_y_mayor_x(y_centro)
            if valor:
                datos['importe_operacion'] = limpiar_importe(valor)

        elif texto.startswith("Fecha y hora de creación"):
            valor = buscar_valor_y_mayor_x(y_centro)
            if valor:
                datos['fecha'] = convertir_fecha_larga(valor)
                #match = re.search(r"(\d{1,2} de \w+ de \d{4})", valor)
                #if match:
                #    datos['fecha'] = match.group(1)

    if len(cuentas_encontradas) >= 2:
        datos['cuenta_retiro'] = cuentas_encontradas[0]
        datos['cuenta_deposito'] = cuentas_encontradas[1]
    elif len(cuentas_encontradas) == 1:
        datos['cuenta_retiro'] = cuentas_encontradas[0]

    datos['divisa_cuenta'] = 'MXN'

    #print("DATOS EXTRAÍDOS CON BLOQUES:", datos)
    return datos

def detectar_formato_pdf(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
        texto = ""
        for pagina in pdf:
            texto += pagina.get_text()

        if "Cuenta de retiro" in texto and "Cuenta de depósito" in texto:
            return "formato_1"
        elif "Datos de la operación" in texto and "Importe" in texto:
            return "formato_2"
        else:
            return "desconocido"

def extraer_texto_de_pdf(pdf_file):
    pdf = fitz.open(stream=pdf_file, filetype='pdf')
    texto = ""
    for pagina in pdf:
        texto += pagina.get_text() + "\n"
    return texto

def extraer_bloques_formato_2(pdf_bytes):
    bloques_total = []
    with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
        for pagina in pdf:
            bloques = pagina.get_text("blocks")
            bloques_total.extend(bloques)
    return bloques_total

def extraer_texto_pdf_prop(file_field):
    if not file_field:
        return ''

    try:
        with file_field.open('rb') as archivo_pdf:
            lector_pdf = PyPDF2.PdfReader(archivo_pdf)
            texto = ''
            for pagina in range(len(lector_pdf.pages)):
                texto += lector_pdf.pages[pagina].extract_text()
        return texto
    except FileNotFoundError:
        # Maneja la situación cuando el archivo no se encuentra
        return "Archivo no encontrado"
    except Exception as e:
        # Maneja cualquier otra excepción que pueda ocurrir
        return f"Error al leer el archivo: {str(e)}"

def agregar_cfdi_zip(zip_file, factura, xml, carpeta, tipo):
    #Las importaciones de las funciones de generación de PDF se hacen dentro de la función para evitar problemas de importación circular.
    # ------------------------------------------------------------------
    from gastos.views import crear_pdf_cfdi_buffer
    # -----------------------------------------------------------------
    if not xml:
        return None

    uuid = factura.uuid or "SIN_UUID"
    nombre_base = f"{tipo}_{factura.id}_{uuid}"

    # Guardar XML en carpeta individual y general
    nombre_xml = f"{nombre_base}.xml"
    ruta_xml = os.path.join(carpeta, nombre_xml)
    ruta_xml_general = f"GENERAL_XMLs/{nombre_xml}"

    zip_file.write(xml.path, ruta_xml)
    zip_file.write(xml.path, ruta_xml_general)

    # Generar PDF desde el XML
    pdf_buf = crear_pdf_cfdi_buffer(factura)

    if pdf_buf:
        nombre_pdf = f"{nombre_base}.pdf"

        zip_file.writestr(
            os.path.join(carpeta, nombre_pdf),
            pdf_buf.getvalue()
        )

        zip_file.writestr(
            f"GENERAL_PDFs/{nombre_pdf}",
            pdf_buf.getvalue()
        )

    return ruta_xml_general


def descargar_documentos_pagos(pagos):
    #Las importaciones de las funciones de generación de PDF se hacen dentro de la función para evitar problemas de importación circular.
    # ------------------------------------------------------------------
    from gastos.views import render_pdf_gasto, generar_pdf_vale_rosa
    from viaticos.views import generar_pdf_viatico
    from compras.views import generar_pdf_nueva
    # ------------------------------------------------------------------
    zip_buffer = BytesIO()
    datos_xml_lista = []
    processed_docs = set()

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:

        for pago in pagos:
            carpeta = None
            if pago.gasto:
                gasto = pago.gasto
                carpeta = f'{pago.pagado_real}_GASTO_{gasto.folio}_{gasto.distrito.nombre}'
                    
                for factura in gasto.facturas.all():
                    if not factura.archivo_xml:
                        continue
                    beneficiario = factura.solicitud_gasto.colaborador.staff.staff.first_name + ' ' + factura.solicitud_gasto.colaborador.staff.staff.last_name  if factura.solicitud_gasto.colaborador else factura.solicitud_gasto.staff.staff.staff.first_name + ' ' + factura.solicitud_gasto.staff.staff.staff.last_name
                    fecha_subida = factura.fecha_subida.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subida else 'No disponible'
                 
                    gen_path = agregar_cfdi_zip(zip_file, factura, factura.archivo_xml, carpeta, "GASTO")
                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.archivo_xml.path,f"G{gasto.folio}",fecha_subida, gasto.distrito.nombre, beneficiario,
                                                                      gen_path, factura))
                
                #Formato de PDF del gasto, solo se genera una vez por gasto, no por factura
                if gasto.id not in processed_docs:
                    pdf_buf = render_pdf_gasto(gasto.id)
                    zip_file.writestr(os.path.join(carpeta, f'GASTO_{gasto.folio}.pdf'), pdf_buf.getvalue())
                    processed_docs.add(gasto.id)
                
                # Generar y agregar vales rosa aprobados
                for vale in gasto.vales_rosa.filter(esta_aprobado=True):
                    pdf_vale_buf = generar_pdf_vale_rosa(vale.id)

                    nombre_archivo = f"VALE_ROSA_{vale.id}_GASTO_{gasto.folio}.pdf"

                    zip_file.writestr(os.path.join(carpeta, "VALES_ROSA", nombre_archivo),pdf_vale_buf.getvalue())

                    zip_file.writestr(f"GENERAL_VALES_ROSA/{nombre_archivo}", pdf_vale_buf.getvalue())
            elif pago.oc:
                oc = pago.oc
                carpeta = f'{pago.pagado_real}_COMPRA_{oc.folio}_{oc.req.orden.distrito.nombre}'
                    
                for factura in oc.facturas.all():
                    if not factura.factura_xml:
                        continue
                  
                    gen_path = agregar_cfdi_zip(zip_file, factura, factura.factura_xml, carpeta,"COMPRA")

                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, f"OC{oc.folio}", factura.fecha_subido, oc.req.orden.distrito.nombre, "NA",
                                                                      gen_path, factura))

                    for complemento in factura.complementos.all():
                        if complemento.complemento_pdf:     #Encarpeta el complemento_pdf
                            complemento_file_name = os.path.basename(complemento.complemento_pdf.path)
                            zip_file.write(complemento.complemento_pdf.path, os.path.join(carpeta, complemento_file_name))
                        if complemento.complemento_xml:     #Encarpeta el complemento_xml
                            complemento_file_name = os.path.basename(complemento.complemento_xml.path)
                            zip_file.write(complemento.complemento_xml.path, os.path.join(carpeta, complemento_file_name))
                if oc.id not in processed_docs:
                    pdf_buf = generar_pdf_nueva(oc)
                    zip_file.writestr(os.path.join(carpeta, f'OC_{oc.folio}.pdf'), pdf_buf.getvalue())
                    processed_docs.add(oc.id)
                    # 🚀 Incluir los complementos de pago relacionados en la misma carpeta
                        
            elif pago.viatico:
                viatico = pago.viatico
                carpeta = f'{pago.pagado_real}_VIATICO_{viatico.folio}_{viatico.distrito.nombre}'
                    
                for factura in viatico.facturas.all():
                    if not factura.factura_xml:
                        continue

                    beneficiario = factura.solicitud_viatico.colaborador.staff.staff.first_name + ' ' + factura.solicitud_viatico.colaborador.staff.staff.last_name  if factura.solicitud_viatico.colaborador else factura.solicitud_viatico.staff.staff.staff.first_name + ' ' + factura.solicitud_viatico.staff.staff.staff.last_name
                    fecha_subida = factura.fecha_subido.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subido else 'No disponible' # Formato YYYY-MM-DD
                    gen_path = agregar_cfdi_zip(zip_file, factura, factura.factura_xml, carpeta, "VIATICO")

                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, f"V{viatico.folio}", fecha_subida, viatico.distrito.nombre, beneficiario, 
                                                                      gen_path, factura))
                    
                if viatico.id not in processed_docs:
                    pdf_buf = generar_pdf_viatico(viatico.id)
                    zip_file.writestr(os.path.join(carpeta, f'VIATICO_{viatico.folio}.pdf'), pdf_buf.getvalue())
                    processed_docs.add(viatico.id)

                # Generar y agregar vales aprobados relacionados al viático
                for vale in viatico.vales_rosa_viatico.filter(esta_aprobado=True):
                    pdf_vale_buf = generar_pdf_vale_rosa(vale.id)

                    tipo_vale = "AZUL" if vale.color == "azul" else "ROSA"
                    nombre_archivo = f"VALE_{tipo_vale}_{vale.id}_VIATICO_{viatico.folio}.pdf"

                    zip_file.writestr(
                        os.path.join(carpeta, "VALES", nombre_archivo),
                        pdf_vale_buf.getvalue()
                    )

                    zip_file.writestr(f"GENERAL_VALES/{nombre_archivo}", pdf_vale_buf.getvalue())


            if pago.comprobante_pago and carpeta is not None:
                fecha_pago = pago.pagado_real.strftime('%Y-%m-%d') if pago.pagado_real else 'SIN_FECHA'
                if pago.gasto:
                    folio = f'G{pago.gasto.folio}'
                    if pago.gasto.colaborador:
                        pago_nombre = f'{pago.gasto.colaborador.staff.staff.first_name}_{pago.gasto.colaborador.staff.staff.last_name}'
                    else:
                        pago_nombre = f'{pago.gasto.staff.staff.staff.first_name}_{pago.gasto.staff.staff.staff.last_name}'
                elif pago.oc:
                    folio = f'OC{oc.folio}'
                    pago_nombre = f'{pago.oc.proveedor.nombre.razon_social}'
                elif pago.viatico:
                    folio = f'V{viatico.folio}'
                    if pago.viatico.colaborador:
                        pago_nombre = f'{pago.viatico.colaborador.staff.staff.first_name}_{pago.viatico.colaborador.staff.staff.last_name}'
                    else:
                        pago_nombre = f'{pago.viatico.staff.staff.staff.first_name}_{pago.viatico.staff.staff.staff.last_name}'
                    
                monto = f"{pago.monto:.2f}".replace('.', '_')
                nuevo_nombre = f'{fecha_pago}_{folio}_{pago_nombre}_{monto}'
                    
                zip_file.write(pago.comprobante_pago.path, os.path.join(carpeta, f'{nuevo_nombre}.pdf'))
            

        # Excel de resumen: fuera del for, dentro del with.
        output = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "Resumen XML"

        columnas = [
            'Distrito', 'Folio', 'Fecha subida',
            'Fecha factura', 'Razón Social',
            'Folio Fiscal (UUID)', 'Monto Total Factura',
            'Tipo de Moneda', 'Forma de pago',
            'Método de Pago',
            'Receptor (Empresa) Nombre',
            'Beneficiario', 'Archivo',
            'Tipo de Documento'
            #'EstadoSAT', 'Fecha Validación SAT',
        ]

        ws.append(columnas)

        for dato in datos_xml_lista:
            ws.append([dato.get(col, '') for col in columnas])

        for row in range(2, ws.max_row + 1):
            ws[f"G{row}"].number_format = (
                numbers.FORMAT_CURRENCY_USD_SIMPLE
            )

        wb.save(output)

        zip_file.writestr("GENERAL_XMLs/reporte_facturas.xlsx", output.getvalue())

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer,content_type='application/zip')
    response.set_cookie('descarga_iniciada','true',max_age=20)
    response['Content-Disposition'] = ('attachment; filename=pagos.zip')

    return response