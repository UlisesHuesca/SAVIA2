import fitz  # PyMuPDF
import re
import PyPDF2


def encontrar_variables(texto):
    # Diccionario para almacenar los valores extraídos
    variables = {}

    # Definir los patrones de regex para cada variable
    patrones = {
        'fecha': r'Fecha de creación:\s*(\d{2}/\d{2}/\d{4})',
        'importe_operacion': r'(?:Importe|Importe de la operación):\s?([\d,.]+)',
        'cuenta_retiro': r'Cuenta de retiro:\s?(\d+)',
        'divisa_cuenta': r'Divisa de la cuenta:\s?([^\n\r]+)',
        'titular_cuenta_1': r'Titular de la cuenta:\s*([^\n\r]+)',
        'titular_cuenta_2': r'Titular de la cuenta:\s*([^\n\r]+)\s*Titular de la cuenta:\s*([^\n\r]+)',
        'motivo_pago': r'(?:Motivo de pago|Concepto de pago):\s*([^\n\r]+)',
        'folio_unico': r'Folio único:\s*(\d+)'
    }

    # Buscar cada patrón y extraer el valor
    for clave, patron in patrones.items():
        coincidencia = re.search(patron, texto, re.DOTALL)
        if coincidencia:
            try:
                if clave in ['importe_operacion']:
                    valor = coincidencia.group(1)
                    if valor:
                        if clave == 'importe_operacion':
                            valor = valor.replace('MXP', '').replace(',', '')
                        variables[clave] = valor
                    else:
                        variables[clave] = 'No disponible'
                elif clave == 'titular_cuenta_2':
                    valor1 = coincidencia.group(1)
                    valor2 = coincidencia.group(2)
                    if valor1 and valor2:
                        variables['titular_cuenta_1'] = valor1.strip()
                        variables['titular_cuenta_2'] = valor2.strip()
                    else:
                        variables['titular_cuenta_1'] = 'No disponible'
                        variables['titular_cuenta_2'] = 'No disponible'
                elif clave == 'titular_cuenta_1':
                    valor = coincidencia.group(1)
                    if valor:
                        variables[clave] = valor.strip()
                    else:
                        variables[clave] = 'No disponible'
                else:
                    valor = coincidencia.group(1)
                    if valor:
                        variables[clave] = valor.strip()
                    else:
                        variables[clave] = 'No disponible'
            except IndexError:
                variables[clave] = 'No disponible'
        else:
            variables[clave] = 'No disponible'


    # Imprimir para depuración
    #print(f"Variables extraídas: {variables}")

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