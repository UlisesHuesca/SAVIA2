from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from tesoreria.views import cfdi_compras

from dashboard.models import Profile

# Ajusta este import a la ubicación real de tu decorador.
from user.decorators import perfil_seleccionado_required

from .filters import CFDIFilter
from .forms import CargaMasivaXMLForm
from .models import CFDI
from .services.parser_cfdi import CFDIError, parsear_cfdi
from .services.datos_pdf import preparar_datos_pdf

#PDF generator
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter
from reportlab.rl_config import defaultPageSize
from compras.tasks import convert_excel_matriz_compras_task
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageBreak
from bs4 import BeautifulSoup
from user.decorators import perfil_seleccionado_required

import qrcode
import tempfile
import io
from num2words import num2words

@perfil_seleccionado_required
def lista_cfdi(request):
    queryset = (
        CFDI.objects
        .select_related('subido_por')
        .all()
        .order_by('-fecha_timbrado', '-fecha_subido')
    )

    filtro = CFDIFilter(
        request.GET or None,
        queryset=queryset,
    )

    paginator = Paginator(filtro.qs, 25)
    pagina = paginator.get_page(request.GET.get('page'))

    parametros = request.GET.copy()
    parametros.pop('page', None)

    context = {
        'filtro': filtro,
        'pagina': pagina,
        'form_carga': CargaMasivaXMLForm(),
        'querystring': parametros.urlencode(),
    }

    return render(
        request,
        'boveda_xml/lista_cfdi.html',
        context,
    )


@perfil_seleccionado_required
def carga_masiva_xml(request):
    if request.method != 'POST':
        return redirect('boveda_xml:lista_cfdi')

    pk_profile = request.session.get('selected_profile_id')
    usuario = get_object_or_404(Profile, id=pk_profile)

    form = CargaMasivaXMLForm(request.POST, request.FILES)

    if not form.is_valid():
        queryset = (
            CFDI.objects
            .select_related('subido_por')
            .all()
            .order_by('-fecha_timbrado', '-fecha_subido')
        )

        filtro = CFDIFilter(request.GET or None, queryset=queryset)
        paginator = Paginator(filtro.qs, 25)

        context = {
            'filtro': filtro,
            'pagina': paginator.get_page(1),
            'form_carga': form,
            'querystring': '',
        }

        return render(
            request,
            'boveda_xml/lista_cfdi.html',
            context,
        )

    archivos = form.cleaned_data['archivos_xml']
    resultados = []
    uuids_del_lote = set()

    guardados = 0
    rechazados = 0

    fecha_actual = timezone.localdate()

    for archivo in archivos:
        resultado = {
            'archivo': archivo.name,
            'uuid': None,
            'estatus': 'RECHAZADO',
            'mensaje': '',
        }

        try:
            datos = parsear_cfdi(archivo)
            uuid = datos['uuid']

            resultado['uuid'] = uuid

            # Duplicado dentro de la misma selección.
            if uuid in uuids_del_lote:
                raise CFDIError(
                    'El UUID está repetido dentro del mismo lote.'
                )

            uuids_del_lote.add(uuid)

            # Duplicado previamente almacenado.
            cfdi_existente = CFDI.objects.filter(uuid=uuid).first()

            if cfdi_existente:
                raise CFDIError(
                    'El UUID ya se encuentra almacenado en la bóveda.'
                )

            fecha_timbrado = datos['fecha_timbrado']

            if fecha_timbrado is None:
                raise CFDIError(
                    'El CFDI no contiene fecha de timbrado.'
                )

            fecha_timbrado_local = timezone.localtime(
                fecha_timbrado
            ).date()

            # Regla previamente definida:
            # solo se admiten CFDI del mes y año actuales.
            if (
                fecha_timbrado_local.month != fecha_actual.month or
                fecha_timbrado_local.year != fecha_actual.year
            ):
                raise CFDIError(
                    'La fecha de timbrado no corresponde al mes '
                    'y año actuales.'
                )

            archivo.seek(0)

            try:
                with transaction.atomic():
                    CFDI.objects.create(
                        archivo_xml=archivo,
                        subido_por=usuario,
                        **datos,
                    )

            except IntegrityError:
                raise CFDIError(
                    'El UUID ya fue cargado por otro usuario.'
                )

            resultado['estatus'] = 'GUARDADO'
            resultado['mensaje'] = 'XML guardado correctamente.'
            guardados += 1

        except CFDIError as error:
            resultado['mensaje'] = str(error)
            rechazados += 1

        except Exception as error:
            resultado['mensaje'] = (
                f'Ocurrió un error inesperado: {error}'
            )
            rechazados += 1

        finally:
            resultados.append(resultado)

    if guardados:
        messages.success(
            request,
            f'Se guardaron correctamente {guardados} XML.'
        )

    if rechazados:
        messages.warning(
            request,
            f'Se rechazaron {rechazados} XML.'
        )

    context = {
        'resultados': resultados,
        'guardados': guardados,
        'rechazados': rechazados,
        'total_archivos': len(resultados),
    }

    return render(
        request,
        'boveda_xml/resultado_carga.html',
        context,
    )
# Create your views here.
@perfil_seleccionado_required
def generar_cfdi(request, pk):
    factura = get_object_or_404(CFDI, id=pk)

    try:
        buffer = cfdi_pdf(factura)
    except ValueError as error:
        return HttpResponse(str(error), status=400)

    response = FileResponse(
        buffer,
        content_type='application/pdf',
    )

    response['Content-Disposition'] = (
        f'inline; filename="{factura.uuid}.pdf"'
    )

    return response


def cfdi_pdf(factura):
    data = preparar_datos_pdf(factura)

    if not data:
        raise ValueError(
            'No fue posible obtener la información del CFDI.'
        )

    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    if not data:
        return HttpResponse("Error al parsear el archivo XML", status=400)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Generar código QR
    qr_data = f"https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?id={data['uuid']}&re={data['rfc_emisor']}&rr={data['rfc_receptor']}&tt={data['total']}&fe={data['sello_cfd'][-8:]}"
    qr_img = qrcode.make(qr_data)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        qr_img.save(temp_file)
        temp_file.seek(0)
        qr_x = 500
        qr_y = height - 700
        qr_size = 2.75 * cm
        c.drawImage(temp_file.name, qr_x, qr_y, qr_size, qr_size)

    # Título
    c.setFillColor(prussian_blue)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, height - 40, "FACTURA GENERADA POR SAVIA 2.0")

    # Datos del Emisor
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, height - 80, "Datos del Emisor:")
    
    c.setFont("Helvetica", 8)
    alineado_x = 30
    alineado_y = height - 100
    alineado_y2 = alineado_y
    line_height = 12

    c.drawString(alineado_x, alineado_y, f"RFC: {data['rfc_emisor']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Nombre: {data['nombre_emisor']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Régimen Fiscal: {data['regimen_fiscal_emisor']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Lugar de Expedición: {data['lugar_expedicion']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Fecha y hora de expedición: {data['fecha']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Moneda: {data['moneda']}")
    alineado_y -= line_height
    c.drawString(alineado_x, alineado_y, f"Forma de Pago: {data['forma_pago']}")

    # Datos del Receptor
    alineado_y -= 2 * line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(alineado_x + 350, height - 80, "Datos del Receptor:")
    
    c.setFont("Helvetica", 8)
    alineado_y -= line_height
    c.drawString(alineado_x + 350, alineado_y2, f"RFC: {data['rfc_receptor']}")
    alineado_y2 -= line_height
    c.drawString(alineado_x + 350, alineado_y2, f"Nombre: {data['nombre_receptor']}")
    alineado_y2 -= line_height
    c.drawString(alineado_x + 350, alineado_y2, f"Régimen Fiscal: {data['regimen_fiscal_receptor']}")
    alineado_y2 -= line_height
    c.drawString(alineado_x + 350, alineado_y2, f"Régimen Fiscal: {data['codigo_postal']}")
    alineado_y2 -= line_height
    c.drawString(alineado_x + 350, alineado_y2, f"Uso del CFDI: {data['uso_cfdi']}")

    # Conceptos (Tabla)
    alineado_y -= line_height
    # Configuración del estilo para los párrafos
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.wordWrap = 'CJK'  # Ajusta automáticamente el texto
    # Crear un estilo personalizado
    custom_style = ParagraphStyle(
        'CustomStyle',
        parent=styleN,
        fontSize=6,  # Ajusta el tamaño del texto aquí
        leading=7,   # Ajusta el interlineado aquí si es necesario
    )

    # Preparamos los datos de la tabla
    table_data = [["CANT", "CLAVE", "CONCEPTO", "U DE M", "P.U.", "IMPORTE", "IMPUESTO", "TIPO TASA"]]
    for item in data['resultados']:
        descripcion = item['descripcion']
        cantidad = float(item['cantidad'])
        unidad = item['unidad']
        valor_unitario = float(item['precio'])
        importe = float(item['importe'])
        # Verificar y convertir solo si el valor no es 'N/A'
         # Inicializar las variables impuesto y tasa
        impuesto = item['impuesto']
        tasa = item['tasa_cuota']
        if impuesto != 'N/A':
            impuesto = float(impuesto)
        else:
            impuesto = 0.0  # o cualquier valor predeterminado que consideres adecuado
        
        if tasa != 'N/A':
            tasa = float(tasa)
        else:
            tasa = 0.0  # o cualquier valor predeterminado que consideres adecuado
        clave = item['clave']
         # Crear un párrafo para la descripción
        descripcion_paragraph = Paragraph(descripcion, custom_style)
        unidad_paragraph = Paragraph(unidad, custom_style)
        table_data.append([
            f"{cantidad:.2f}",
            clave,
            descripcion_paragraph,
            unidad_paragraph,
            f"{valor_unitario:,.2f}",
            f"{importe:,.2f}",
            f"{impuesto:,.2f}",
            f"{tasa:.2f}",
        ])

    # Crear la tabla
    table = Table(table_data, colWidths=[1.0 * cm, 1.5 * cm, 8.5 * cm, 1.5 * cm, 2 * cm, 2 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm])
    table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 0), (-1, 0), prussian_blue),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]))

    # Guardar la tabla en el PDF
    table.wrapOn(c, width, height)
    table.drawOn(c, alineado_x, alineado_y - len(table_data) * line_height)

    # Ajustar el alineado_y para seguir escribiendo debajo de la tabla
    alineado_y -= len(table_data) * line_height + 2 * line_height

    # Totales
    c.setFont("Helvetica-Bold", 12)
   
    c.setFont("Helvetica", 10)
    alineado_y -= line_height

     # Importe con letra
    alineado_y -= 2 * line_height
    c.drawString(alineado_x, alineado_y, "Importe con Letra:")
    total_letras = num2words(float(data['total']), lang='es', to='currency', currency='MXN')
    c.drawString(alineado_x, alineado_y - 10, total_letras)
    #c.drawRightString(alineado_x, alineado_y , f"{data['importe_con_letra']}")
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.setFillColor(prussian_blue)
    c.rect(alineado_x + 390 ,alineado_y - 50,110,62, fill=True, stroke=False) #Barra azul superior | Subtotal
    c.setFillColor(white)
    c.drawRightString(alineado_x + 500, alineado_y , f"Subtotal:")
    c.setFillColor(black)
    c.drawRightString(alineado_x + 555, alineado_y, f"{float(data['subtotal']):,.2f}")
    alineado_y -= line_height
    c.setFillColor(white)
    c.drawRightString(alineado_x + 500, alineado_y, f"Impuestos trasladados:")
    c.setFillColor(black)
    c.drawRightString(alineado_x + 555, alineado_y, f"{float(data['impuestos']):,.2f}")
    alineado_y -= line_height
  

    iva_retenido = data.get('iva_retenido') or 0
    isr_retenido = data.get('isr_retenido') or 0

    # IVA retenido
    if iva_retenido > 0:
        c.setFillColor(white)
        c.drawRightString(
            alineado_x + 500,
            alineado_y,
            "IVA retenido:",
        )

        c.setFillColor(black)
        c.drawRightString(
            alineado_x + 555,
            alineado_y,
            f"{float(iva_retenido):,.2f}",
        )

        alineado_y -= line_height

    # ISR retenido
    if isr_retenido > 0:
        c.setFillColor(white)
        c.drawRightString(
            alineado_x + 500,
            alineado_y,
            "ISR retenido:",
        )

        c.setFillColor(black)
        c.drawRightString(
            alineado_x + 555,
            alineado_y,
            f"{float(isr_retenido):,.2f}",
        )

        alineado_y -= line_height
    c.setFillColor(white)
    c.drawRightString(alineado_x + 500, alineado_y, f"Total:")
    c.setFillColor(black)
    c.drawRightString(alineado_x + 555, alineado_y, f"{float(data['total']):,.2f}")
    # Otros detalles
    

    otros_detalles = [
        ["Folio Fiscal", "Fecha y Hora de Certificación", "No. Certificado Digital", "Método de Pago"],
        [data['uuid'], data['fecha_timbrado'], data['no_certificado'], data['metodo_pago']]
    ]
    detalles_table = Table(otros_detalles, colWidths=[5 * cm, 5 * cm, 4.5 * cm, 4.5 * cm])
    detalles_table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), prussian_blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
    ]))

    # Guardar la tabla de detalles en el PDF
    detalles_table.wrapOn(c, width, height)
    detalles_table.drawOn(c, alineado_x, 180)
    alineado_y -= 4 * line_height
     # Utilizar Paragraph para las líneas largas
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]
    styleN.fontSize = 6
    c.setFont("Helvetica", 6)
    c.line(30,177,580,177)
    c.drawString(alineado_x, 170, f"ESTE DOCUMENTO ES UNA REPRESENTACIÓN IMPRESA DE UN CFDI v4.0")
    
    # Reducir el ancho de los párrafos
    reduced_width = width * 0.7  # Ajusta este valor según sea necesario

    sello_cfd_paragraph = Paragraph(f"Sello Digital del CFDI: {data['sello_cfd']}", styleN)
    sello_cfd_paragraph.wrapOn(c,  reduced_width, line_height * 4)
    sello_cfd_paragraph.drawOn(c, alineado_x, 130)
    alineado_y -= line_height * 5
    
    sello_sat_paragraph = Paragraph(f"Sello del SAT: {data['sello_sat']}", styleN)
    sello_sat_paragraph.wrapOn(c,  reduced_width, line_height * 4)
    sello_sat_paragraph.drawOn(c, alineado_x, 90)
    alineado_y -= line_height * 3
    c.drawString(alineado_x, 40, f"No. serie CSD SAT {data['no_certificadoSAT']}")

    sello_cfd_paragraph = Paragraph(f"Cadena Original del complemento de certificación digital del SAT: {data['cadena_original']}", styleN)
    sello_cfd_paragraph.wrapOn(c,  reduced_width, line_height * 4)
    sello_cfd_paragraph.drawOn(c, alineado_x, 50)
    alineado_y -= line_height * 5
    
   

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer