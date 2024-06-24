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
        'motivo_pago': r'(?:Motivo de pago|Concepto de pago):\s*([^\n\r]+)'
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
    print(f"Variables extraídas: {variables}")

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