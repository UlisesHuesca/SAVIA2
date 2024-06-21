import fitz  # PyMuPDF
import re
import PyPDF2

def encontrar_variables(texto):
    # Diccionario para almacenar los valores extraídos
    variables = {}

    # Definir los patrones de regex para cada variable
    patrones = {
        'fecha': r'Fecha de creación:\s*(\d{2}/\d{2}/\d{4})',
        'importe_operacion': r'Importe|Importe de la operación:\s?([\d,.]+)',
        'cuenta_retiro': r'Cuenta de retiro:\s?(\d+)',
        'divisa_cuenta': r'Divisa de la cuenta:\s?([^\n\r]+)',
        'titular_cuenta': r'Titular de la cuenta:\s*([^\n\r]+)\s*Titular de la cuenta:\s*([^\n\r]+)',
        'motivo_pago': r'Motivo de pago:\s*([^\n\r]+)'
    }

    # Buscar cada patrón y extraer el valor
    for clave, patron in patrones.items():
        coincidencia = re.search(patron, texto)
        if coincidencia:
            if clave == 'importe_operacion':
                variables[clave] = coincidencia.group(1).replace('MXP','').replace(',', '') if 'importe_operacion' in clave else coincidencia.group(1)
            elif clave == 'titular_cuenta':
                variables[clave] = coincidencia.group(2)  # Captura solo el titular de la cuenta del lado derecho
            else:
                variables[clave] = coincidencia.group(1)
        else:
            variables[clave] = 'No disponible'


    return variables


def extraer_texto_de_pdf(pdf_file):
    pdf_file = fitz.open(stream= pdf_file, filetype='pdf')
    texto = ""
    for pagina in pdf_file:
        texto += pagina.get_text()
    return texto


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