"""Generador PDF de preevaluaciones para SAVIA 2.1 (ReportLab)."""
import io
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.utils import ImageReader

AZUL = colors.HexColor('#16324F')
GRIS = colors.HexColor('#EAF0F5')


def _texto(valor):
    return escape(str(valor if valor is not None else '—'))


def _nombre_perfil(perfil):
    if not perfil or not getattr(perfil, 'staff', None):
        return 'No registrado'
    nombre = perfil.staff.get_full_name().strip()
    return nombre or perfil.staff.get_username()


def _configuracion(evaluacion):
    tipo = getattr(getattr(evaluacion, 'tipo_evaluacion', None), 'nombre', None)
    if tipo == 'Simplificada':
        return {
            'titulo': 'Reporte de evaluación inicial simplificada',
            'codigo': 'F-ADQ-N4-01.04',
            'grupos': [(
                'Criterios para la evaluación inicial de proveedores - productos generales',
                [
                    ('Verificar que el producto cumple con las especificaciones requeridas', 'especs_ver', 'especs_b'),
                    ('Comparar los precios ofrecidos con al menos otras dos cotizaciones de diferentes proveedores, emitidas dentro del último año', 'precios_ver', 'precios_b'),
                ],
                'Para productos y servicios generales se requiere cumplir todos los criterios para obtener la preaprobación. Adjuntar documentación de respaldo, comparación de precios y evidencia de cumplimiento de especificaciones.',
            )],
        }
    if tipo == 'Inicial':
        return {
            'titulo': 'Reporte de evaluación inicial',
            'codigo': 'F-ADQ-N4-01.03',
            'grupos': [
                (
                    'Compras críticas',
                    [
                        ('Verificación del Sistema de Gestión de la Calidad del proveedor', 'verif_calidad', 'verif_calidad_b'),
                        ('Control en la cadena de suministro del proveedor', 'control_cadena_suministro', 'control_cadena_b'),
                        ('Evaluación de la capacidad del proveedor', 'capacidad_proveedor', 'capacidad_proveedor_b'),
                    ],
                    'Para productos y servicios críticos se requiere el cumplimiento total de los criterios para obtener la preaprobación. Adjuntar la documentación de respaldo.',
                ),
                (
                    'Compras no críticas',
                    [
                        ('Verificación del Sistema de Gestión de la Calidad del proveedor', 'requisitos_sgc_ver', 'sgc_b'),
                        ('Evaluación del proveedor respecto a los requisitos de compra de la organización', 'eval_compra', 'eval_compra_b'),
                        ('Evaluación del producto después de la entrega o de las actividades finalizadas', 'eval_actividades', 'eval_actividades_b'),
                    ],
                    'Para productos y servicios no críticos se requiere el cumplimiento de al menos uno de los requisitos para obtener la preaprobación. Adjuntar la documentación de respaldo.',
                ),
            ],
        }
    raise ValueError(f'Tipo de evaluación no admitido: {tipo!r}')


def _encabezado(canvas, doc, config):
    canvas.saveState()
    ancho, alto = letter
    logo = finders.find('images/logo_vordcab_documento.png')
    if logo:
        canvas.drawImage(ImageReader(logo), 17*mm, alto-22*mm, width=31*mm, height=13*mm, preserveAspectRatio=True, anchor='c', mask='auto')
    canvas.setFillColor(AZUL)
    canvas.rect(17*mm, alto-34*mm, ancho-34*mm, 9*mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 11)
    canvas.drawCentredString(ancho/2, alto-31*mm, config['titulo'])
    canvas.setFillColor(colors.black)
    canvas.setFont('Helvetica', 7)
    canvas.drawRightString(ancho-17*mm, alto-17*mm, f"Documento: {config['codigo']}")
    canvas.drawRightString(ancho-17*mm, alto-21*mm, 'Clasificación: Registro  |  Nivel: N5')
    canvas.setStrokeColor(colors.HexColor('#B9C5CE'))
    canvas.line(17*mm, 19*mm, ancho-17*mm, 19*mm)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(17*mm, 14*mm, 'SAVIA | Preevaluación de proveedores')
    canvas.drawRightString(ancho-17*mm, 14*mm, f'Página {doc.page}')
    canvas.restoreState()


def generar_pdf_preevaluacion(preevaluacion):
    config = _configuracion(preevaluacion)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=17*mm, leftMargin=17*mm,
                            topMargin=42*mm, bottomMargin=25*mm, title=config['titulo'])
    normal = ParagraphStyle('SaviaNormal', fontName='Helvetica', fontSize=8.5, leading=12, alignment=TA_LEFT)
    encabezado = ParagraphStyle('SaviaEncabezado', parent=normal, fontName='Helvetica-Bold', textColor=colors.white, fontSize=8)
    seccion = ParagraphStyle('SaviaSeccion', parent=normal, fontName='Helvetica-Bold', fontSize=10, textColor=AZUL, spaceBefore=12, spaceAfter=7)
    nota = ParagraphStyle('SaviaNota', parent=normal, fontSize=7.5, leading=10, textColor=colors.HexColor('#495865'))
    P = lambda value: Paragraph(_texto(value), normal)
    historia = []
    fecha = getattr(preevaluacion, 'creado_at', None)
    fecha_texto = fecha.strftime('%d/%m/%Y %H:%M') if fecha else 'No registrada'
    proveedor = getattr(preevaluacion, 'nombre', None)
    historia.append(Paragraph('Información general', seccion))
    generales = [
        [P('Proveedor'), P(getattr(proveedor, 'razon_social', 'No registrado'))],
        [P('ID del proveedor'), P(getattr(proveedor, 'pk', 'No registrado'))],
        [P('Fecha de evaluación'), P(fecha_texto)],
        [P('Realizó la evaluación'), P(_nombre_perfil(getattr(preevaluacion, 'creado_por', None)))],
        [P('Comparativo asociado'), P(getattr(getattr(preevaluacion, 'comparativo_model', None), 'nombre', 'No asociado'))],
    ]
    tabla = Table(generales, colWidths=[44*mm, 134*mm], hAlign='LEFT')
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), GRIS), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.35, colors.HexColor('#D0D9E0')),
        ('LEFTPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    historia.append(tabla)

    for nombre, criterios, texto_nota in config['grupos']:
        historia.append(Paragraph(nombre, seccion))
        filas = [[Paragraph('Criterio', encabezado), Paragraph('Observaciones', encabezado), Paragraph('Cumplimiento', encabezado)]]
        for titulo, campo_detalle, campo_cumple in criterios:
            cumple = bool(getattr(preevaluacion, campo_cumple, False))
            filas.append([P(titulo), P(getattr(preevaluacion, campo_detalle, None)), P('Cumple' if cumple else 'No cumple')])
        tabla = Table(filas, colWidths=[63*mm, 81*mm, 34*mm], repeatRows=1, hAlign='LEFT')
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), AZUL), ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.35, colors.HexColor('#C4CDD5')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F5F8FA')]),
            ('LEFTPADDING', (0,0), (-1,-1), 7), ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ]))
        historia.extend([tabla, Spacer(1, 4*mm), Paragraph(_texto(texto_nota), nota)])

    historia.append(Spacer(1, 13*mm))
    firmas = Table([
        [P(_nombre_perfil(getattr(preevaluacion, 'creado_por', None))), P('Pendiente de definir')],
        [P('Realizador de la evaluación'), P('Autorización del Gerente General')],
    ], colWidths=[89*mm, 89*mm])
    firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LINEABOVE', (0,1), (-1,1), 0.6, colors.black),
        ('TOPPADDING', (0,1), (-1,1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    historia.append(KeepTogether(firmas))
    doc.build(historia, onFirstPage=lambda c,d: _encabezado(c,d,config),
              onLaterPages=lambda c,d: _encabezado(c,d,config))
    buffer.seek(0)
    return buffer


def generar_preevaluacion_pdf(preevaluacion):
    return generar_pdf_preevaluacion(preevaluacion)


def generar_preevaluacion_inicial_pdf(preevaluacion):
    return generar_pdf_preevaluacion(preevaluacion)
