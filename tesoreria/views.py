from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.core.mail import EmailMessage, BadHeaderError
import socket
from smtplib import SMTPException
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.db.models import Count, Q, Case, When, Value, CharField
from django.db.models.functions import Concat
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.dateparse import parse_date
from django.urls import reverse, NoReverseMatch
from user.models import Distrito
from compras.models import ArticuloComprado, Compra
from compras.forms import CompraForm
from compras.filters import CompraFilter
from compras.views import dof, attach_oc_pdf, attach_antisoborno_pdf, attach_codigo_etica_pdf, attach_aviso_privacidad_pdf, attach_politica_proveedor, generar_pdf #convert_excel_matriz_compras
from dashboard.models import Subproyecto
from .models import Pago, Cuenta, Facturas, Comprobante_saldo_favor, Saldo_Cuenta, Tipo_Pago, Complemento_Pago
from gastos.models import Solicitud_Gasto, Articulo_Gasto, Factura
from gastos.views import render_pdf_gasto,crear_pdf_cfdi_buffer
from viaticos.views import generar_pdf_viatico
from viaticos.models import Solicitud_Viatico, Viaticos_Factura
from requisiciones.views import get_image_base64
from .forms import PagoForm, Facturas_Form, Facturas_Completas_Form, Saldo_Form, ComprobanteForm, TxtForm, CompraSaldo_Form, Cargo_Abono_Form, Saldo_Inicial_Form, Transferencia_Form, UploadFileForm, UploadComplementoForm
from .filters import PagoFilter, Matriz_Pago_Filter
from viaticos.filters import Solicitud_Viatico_Filter
from gastos.filters import Solicitud_Gasto_Filter
from user.models import Profile
from .utils import extraer_texto_de_pdf, encontrar_variables, extraer_texto_pdf_prop
import pytz  # Si estás utilizando pytz para manejar zonas horarias
from io import BytesIO
from num2words import num2words
import qrcode
import tempfile
from PIL import Image
from django.utils import timezone
from django.urls import reverse
import re
from openpyxl.styles import numbers
from .tasks import validar_lote_facturas
from urllib.parse import urlencode

from datetime import date, datetime
import decimal
import os
import io
import zipfile
import xml.etree.ElementTree as ET


#Excel stuff
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt

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
import subprocess
import paramiko
import logging
from PyPDF2 import PdfMerger

#Para conectar con API del SAT
from zeep import Client
import time
# Configurar logger
LOG_PATH = '/home/savia/logs/pagos_sftp.log'
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


@perfil_seleccionado_required
def compras_por_pagar(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    almacenes_distritos = set(usuario.almacen.values_list('distrito__id', flat=True))
    if usuario.tipo.tesoreria == True:
        compras = Compra.objects.filter(autorizado2=True, para_pago = False, pagada=False, req__orden__distrito__in = almacenes_distritos).order_by('-folio')
   
    
    #compras = Compra.objects.filter(autorizado2=True, pagada=False).order_by('-folio')
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs
    
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)
    
    if request.method == 'POST' and 'btnReporte' in request.POST:
        if usuario.tipo.tesoreria:
            return convert_excel_matriz_compras_tesoreria(compras)
        else:
            return convert_excel_matriz_compras_autorizadas(compras)
       
    
    if request.method == 'POST':
        compra_ids = request.POST.getlist('compra_ids')
        print(compra_ids)
        if compra_ids:
            for compra_id in compra_ids:
                parcial = request.POST.get(f'parcial_{compra_id}')
                print(parcial)
                  # Asegurarte de que monto no sea None y que sea un número válido
                if parcial:
                    try:
                        parcial = float(parcial)
                    except ValueError:
                        parcial = 0  # O algún valor por defecto en caso de error
                Compra.objects.filter(id=compra_id).update(para_pago=True, parcial = parcial)
            # Después de la actualización, redirige para restablecer el conteo y sumatoria
            return redirect('compras-por-pagar')

    context= {
        'usuario':usuario,
        'compras':compras,
        'myfilter':myfilter,
        'compras_list':compras_list,
        }

    return render(request, 'tesoreria/compras_por_pagar.html',context)

# Create your views here.
@perfil_seleccionado_required
def compras_autorizadas(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    if usuario.tipo.tesoreria == True:
        if usuario.tipo.rh:
            compras = Compra.objects.none()
        else: 
            compras = Compra.objects.filter(para_pago=True,pagada=False,autorizado2=True, req__orden__distrito = usuario.distritos).annotate(
                total_facturas=Count('facturas', filter=Q(facturas__oc__isnull=False)),autorizadas=Count(Case(When(Q(facturas__autorizada=True, facturas__oc__isnull=False), then=Value(1))))
                ).order_by('-folio')
    
   
    
    #compras = Compra.objects.filter(autorizado2=True, pagada=False).order_by('-folio')
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs
    
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    for compra in compras_list:
        if compra.total_facturas == 0:
            compra.estado_facturas = 'sin_facturas'
        elif compra.autorizadas == compra.total_facturas:
            compra.estado_facturas = 'todas_autorizadas'
        else:
            compra.estado_facturas = 'pendientes'

    if request.method == 'POST' and 'btnReporte' in request.POST:
        return convert_excel_matriz_compras_autorizadas(compras)
    

    context= {
        'compras':compras,
        'myfilter':myfilter,
        'compras_list':compras_list,
        }

    return render(request, 'tesoreria/compras_autorizadas.html',context)

@perfil_seleccionado_required
def transferencia_cuentas(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    tipos_pago = Tipo_Pago.objects.all()
    cargo = tipos_pago.get(id = 1)
    abono = tipos_pago.get(id = 2)
    transaccion, created = Pago.objects.get_or_create(tesorero = usuario, hecho=False, tipo = cargo)
    transaccion2, created = Pago.objects.get_or_create(tesorero = usuario, hecho=False, tipo = abono)
    form = Cargo_Abono_Form(instance=transaccion)
    form_transferencia = Transferencia_Form(prefix='abono')

    error_messages = []

    form.fields['tipo'].queryset = Tipo_Pago.objects.filter(id = 3)
    print(Tipo_Pago.objects.filter(id=3))
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
      
    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) +' '+ str(cuenta.moneda), 
         'moneda': str(cuenta.moneda),
        } for cuenta in cuentas]

    if request.method == 'POST':
        if "envio" in request.POST:
            form = Cargo_Abono_Form(request.POST, instance = transaccion)
            form_transferencia = Transferencia_Form(request.POST, instance = transaccion2, prefix='abono')
            
            if form.is_valid() and form_transferencia.is_valid():
                cargo = form.save(commit=False)
                cargo.pagado_date = date.today()
                cargo.tipo = Tipo_Pago.objects.get(id = 1)
                cargo.pagado_hora = datetime.now().time() 
                cargo.hecho = True
                
                abono = form_transferencia.save(commit=False)
                abono.monto = cargo.monto
                #abono.tipo = Tipo_Pago.objects.get(id = 2)
                abono.comentario = f"{cargo.comentario} (Relacionado con cuenta {cargo.cuenta})"
                abono.pagado_real = cargo.pagado_real
                abono.pagado_date = date.today()
                abono.pagado_hora = datetime.now().time()
                abono.hecho = True
                abono.save()

                cargo.comentario = f"{cargo.comentario} (Relacionado con cuenta {abono.cuenta})"
                cargo.save()
                messages.success(request,f'{usuario.staff.staff.first_name}, Has agregado correctamente la transferencia')
                return redirect('control-bancos')
            else:
                for field, errors in form.errors.items():
                    error_messages.append(f"{field}: {errors.as_text()}")
                for field, errors in form_transferencia.errors.items():
                    error_messages.append(f"{field}: {errors.as_text()}")

    context= {
        'form':form,
        'form_transferencia': form_transferencia,
        'cuentas_para_select2': cuentas_para_select2,
        'error_messages': error_messages,
    }

    return render(request, 'tesoreria/transferencia_cuentas.html',context)

@perfil_seleccionado_required
def cargo_abono(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    enproceso = Tipo_Pago.objects.get(id = 3)
    transaccion, created = Pago.objects.get_or_create(tesorero = usuario, hecho=False, tipo = enproceso)
    form = Cargo_Abono_Form(instance=transaccion)
    #form_transferencia = Transferencia_Form(instance = tran)


    form.fields['tipo'].queryset = Tipo_Pago.objects.exclude(id=3)
    #print(Tipo_Pago.objects.filter(id=3))
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
      
    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) +' '+ str(cuenta.moneda), 
         'moneda': str(cuenta.moneda),
        } for cuenta in cuentas]

    if request.method == 'POST':
        if "envio" in request.POST:
            form = Cargo_Abono_Form(request.POST, instance = transaccion)
            if form.is_valid():
                pago = form.save(commit = False)
                pago.pagado_date = date.today()
                pago.pagado_hora = datetime.now().time()
                pago.hecho = True
                #Se elimina el concepto del movimiento directo a la cuenta, todos son movimientos separados que suman y restan cuando deba sacarse el cálculo
                #cuenta = Cuenta.objects.get(cuenta = pago.cuenta.cuenta, moneda = pago.cuenta.moneda)               
                pago.save()   
                return redirect('control-bancos')
            else:
                messages.error(request,f'{usuario.staff.staff.first_name}, No está validando')

    context= {
        'form':form,
        #'form_transferencia': form_transferencia,
        'cuentas_para_select2': cuentas_para_select2,
    }

    return render(request, 'tesoreria/cargo_abono.html',context)


@perfil_seleccionado_required
def saldo_inicial(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    saldo, created = Saldo_Cuenta.objects.get_or_create(hecho=False)
    form = Saldo_Inicial_Form(instance = saldo)

    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
      
    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) +' '+ str(cuenta.moneda), 
         'moneda': str(cuenta.moneda),
        } for cuenta in cuentas]
    
    if request.method == 'POST' and "envio" in request.POST:
        form = Saldo_Inicial_Form(request.POST, instance = saldo)
        if form.is_valid():
            saldo = form.save(commit = False)
            saldo.updated = date.today()
            #saldo.pagado_hora = datetime.now().time()
            saldo.hecho = True
            saldo.updated_by = usuario
            #Se elimina el concepto del movimiento directo a la cuenta, todos son movimientos separados que suman y restan cuando deba sacarse el cálculo
            #cuenta = Cuenta.objects.get(cuenta = pago.cuenta.cuenta, moneda = pago.cuenta.moneda)               
            saldo.save()   
            messages.success(request,f'{usuario.staff.staff.first_name}, Has agregado correctamente el saldo inicial de la cuenta')
            return redirect('control-bancos')
        else:
            messages.error(request,f'{usuario.staff.staff.first_name}, No está validando')

    context = {
        'cuentas_para_select2':cuentas_para_select2,
        'form':form,
    }

    return render(request, 'tesoreria/saldo_inicial.html',context)



def prellenar_formulario(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        pdf_content = request.FILES.get('comprobante_pago')
        
        if not pdf_content:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        pdf_content = pdf_content.read()
        texto_extraido = extraer_texto_de_pdf(pdf_content)
        print("Texto extraído:", texto_extraido)
        datos_extraidos = encontrar_variables(texto_extraido)
        print("Datos extraídos:", datos_extraidos)
        
        fecha_str = datos_extraidos.get('fecha', '').strip()

        fecha_formato_correcto = None  # Valor por defecto en caso de que no se pueda procesar la fecha
        
        if fecha_str:
            try:
                fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y')
                fecha_formato_correcto = fecha_obj.strftime('%Y-%m-%d')
            except ValueError:
                # Opcional: Agregar alguna forma de logging o notificación de que la fecha no es válida
                print('Se lo llevó madres')
                pass
        
        numero_cuenta_extraido = datos_extraidos.get('cuenta_retiro', '').strip().lstrip('0')
        cuenta_objeto = None
        
        if numero_cuenta_extraido:
            try:
                cuenta_objeto = Cuenta.objects.get(cuenta__contains=numero_cuenta_extraido)
            except Cuenta.DoesNotExist:
                # Manejar el caso donde la cuenta no existe
                return JsonResponse({'error': 'Account not found'}, status=404)
        
        divisa_cuenta_extraida = datos_extraidos.get('divisa_cuenta', '').strip()
        
        datos_para_formulario = {
            'monto': datos_extraidos.get('importe_operacion', '').replace('MXP', '').replace(',', '').strip() or None,
            'pagado_real': fecha_formato_correcto,  # Valor procesado o None
            'cuenta': cuenta_objeto.id if cuenta_objeto else None,
            'divisa_cuenta': divisa_cuenta_extraida or None,
        }
        
        return JsonResponse(datos_para_formulario)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)




@perfil_seleccionado_required
def compras_pagos(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=pk)
    productos_criticos = productos.filter(producto__producto__articulos__producto__producto__critico=True)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    sub = Subproyecto.objects.get(id=compra.req.orden.subproyecto.id)
    pagos_alt = Pago.objects.filter(oc=compra.id, hecho=True)
    suma_pago = 0
    suma_pago_usd = 0
    
    for pago in pagos:
        
        if pago.oc.moneda.nombre == "DOLARES":
            if pago.cuenta.moneda.nombre == "PESOS":
                suma_pago = suma_pago + pago.monto
                monto_pago_usd = pago.monto/pago.tipo_de_cambio
                suma_pago_usd = suma_pago_usd + monto_pago_usd
            else:
                suma_pago = suma_pago + pago.monto * (pago.tipo_de_cambio or compra.tipo_de_cambio)
                suma_pago_usd = suma_pago_usd + pago.monto


    if compra.moneda.nombre == 'PESOS':
        cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
        remanente = compra.costo_plus_adicionales - suma_pago
    if compra.moneda.nombre == 'DOLARES':
        cuentas = Cuenta.objects.all()
        remanente = compra.costo_plus_adicionales - suma_pago_usd


    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) +' '+ str(cuenta.moneda), 
         'moneda': str(cuenta.moneda),
        } for cuenta in cuentas]


    pago, created = Pago.objects.get_or_create(tesorero = usuario, oc__req__orden__distrito = usuario.distritos, oc=compra, hecho=False)
    form = PagoForm(instance=pago)

    base_url = reverse('compras-autorizadas')
    filtros = {
        'proveedor': request.GET.get('proveedor', ''),
        'distrito': request.GET.get('distrito', ''),
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
    }
    # Codificar los parámetros
    query_string = urlencode(filtros)
    #print('query_string:',filtros)
    
   
   
    
    redirect_url = f"{base_url}?{query_string}" if query_string else base_url
    print('redirect_url',redirect_url)
    
    if request.method == 'POST' and "envio" in request.POST:
        form = PagoForm(request.POST, request.FILES or None, instance = pago)
        if form.is_valid():
            pago = form.save(commit = False)
            pago.pagado_date = date.today()
            pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            #Traigo la cuenta que se capturo en el form
            cuenta = Cuenta.objects.get(cuenta = pago.cuenta.cuenta, moneda = pago.cuenta.moneda)
            #La utilizo para sacar la información de todos los pagos relacionados con esa cuenta y sumarlos

            # Actualizo el saldo de la cuenta, no es necesario actualizar el saldo de la cuenta
            monto_actual = pago.monto
            if compra.moneda.nombre == "PESOS":
                sub.gastado = sub.gastado + monto_actual
            
            if compra.moneda.nombre == "DOLARES":
                if pago.cuenta.moneda.nombre == "PESOS": #Si la cuenta es en pesos
                    #Estoy aca
                    sub.gastado = sub.gastado + monto_actual * pago.tipo_de_cambio
                    monto_actual = monto_actual/pago.tipo_de_cambio
                    
                
                if pago.cuenta.moneda.nombre == "DOLARES":
                    tipo_de_cambio = decimal.Decimal(dof())
                    sub.gastado = sub.gastado + monto_actual * tipo_de_cambio
                #actualizar la cuenta de la que se paga
            print('monto_actual:',monto_actual)
            monto_total_pagado= monto_actual + suma_pago
            print('monto_total_pagado:',monto_total_pagado)
            compra.monto_pagado = monto_total_pagado
            costo_oc = compra.costo_plus_adicionales 
            monto_parcial = compra.parcial + suma_pago
            print('costo_oc:',round(costo_oc,0))
            print('monto_total_pagado',round(monto_total_pagado,0))
            print('monto_parcial:', round(monto_parcial,0))
            if monto_actual <= 0:
                messages.error(request,f'El pago {monto_actual} debe ser mayor a 0')
            elif round(monto_total_pagado,0) <= round(costo_oc,0):
                if round(monto_total_pagado,0) == round(monto_parcial,0):
                    compra.para_pago = False
                if round(monto_total_pagado,0) >= round(costo_oc,0):
                    compra.pagada= True
                archivo_oc = attach_oc_pdf(request, compra.id)
                pdf_antisoborno = attach_antisoborno_pdf(request)
                pdf_privacidad = attach_aviso_privacidad_pdf(request)
                pdf_etica = attach_codigo_etica_pdf(request)
                pdf_politica_proveedor = attach_politica_proveedor(request)
                static_path = settings.STATIC_ROOT
                img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
                img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
                image_base64 = get_image_base64(img_path)
                logo_v_base64 = get_image_base64(img_path2)
                articulos_html = """
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <thead>
                        <tr>
                            <th>Producto Crítico</th>
                            <th>Requisitos</th>
                            <th>Requerimiento</th>
                        </tr>
                    </thead>        
                    <tbody>
                """
                productos_criticos = productos_criticos
                for articulo in productos_criticos:
                    producto = articulo.producto.producto.articulos.producto.producto
                    requerimientos = producto.producto_calidad.requerimientos_calidad.all()

                    # Si el producto tiene requerimientos, agregar una fila por cada uno
                    if requerimientos.exists():
                        for requerimiento in requerimientos:
                            articulos_html += f"""
                                <tr>
                                    <td>{producto.codigo}</td>
                                    <td>{producto.producto_calidad.requisitos}</td>
                                    <td>{requerimiento.nombre}</td>
                                </tr>
                            """
                    else:
                        articulos_html += f"""
                            <tr>
                                <td>{producto.codigo}</td>
                                <td>{producto.producto_calidad.requisitos}</td>
                                <td>Sin requerimiento</td>
                            </tr>
                        """
                articulos_html += """
                    </tbody>
                </table>
                """
                #if compra.cond_de_pago.nombre == "CONTADO":
                pagos = Pago.objects.filter(oc=compra, hecho=True)
                html_message = f"""
                <html>
                    <head>
                        <meta charset="UTF-8">
                    </head>
                    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                        <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td align="center">
                                                <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="font-size: 18px; text-align: justify;">
                                                    <p>Estimado {compra.req.orden.staff.staff.staff.first_name} {compra.req.orden.staff.staff.staff.last_name},</p>
                                                </p>
                                                <p style="font-size: 16px; text-align: justify;">
                                                    Estás recibiendo este correo porque tu OC {compra.folio} | RQ: {compra.req.folio} |Sol: {compra.req.orden.folio} ha sido pagada por {pago.tesorero.staff.staff.first_name} {pago.tesorero.staff.staff.last_name},</p>
                                                <p>El siguiente paso del sistema: Recepción por parte de Almacén</p>
                                                </p>
                                                <p style="text-align: center; margin: 20px 0;">
                                                    <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                                </p>
                                                <p style="font-size: 14px; color: #999; text-align: justify;">
                                                    Este mensaje ha sido automáticamente generado por SAVIA 2.0
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                </html>
                """
                try:
                    email = EmailMessage(
                    f'OC Pagada {compra.folio}|RQ: {compra.req.folio} |Sol: {compra.req.orden.folio}',
                    body=html_message,
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    to= [compra.req.orden.staff.staff.staff.email,],
                    headers={'Content-Type': 'text/html'}
                    )
                    email.content_subtype = "html " # Importante para que se interprete como HTML
                    email.send()
                except (BadHeaderError, SMTPException, socket.gaierror) as e:
                    error_message = f'Correo de notificación 1: No enviado'
                html_message2 = f"""
                <html>
                    <head>
                        <meta charset="UTF-8">
                    </head>
                    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                        <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td align="center">
                                                <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="font-size: 18px; text-align: justify;">
                                                    <p>Estimado(a) {compra.proveedor.contacto}| Proveedor {compra.proveedor.nombre}:,</p>
                                                </p>
                                                <p style="font-size: 16px; text-align: justify;">
                                                    Estás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.folio}.</p>
                                                    <p>&nbsp;</p>
                                                    <p> Atte. {compra.creada_por.staff.staff.first_name} {compra.creada_por.staff.staff.last_name}</p> 
                                                    <p>GRUPO VORDCAB S.A. de C.V.</p>
                                                    {f"{articulos_html}" if productos_criticos.exists() else ""}
                                                </p>
                                                <p style="text-align: center; margin: 20px 0;">
                                                    <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                                </p>
                                                <p style="font-size: 14px; color: #999; text-align: justify;">
                                                    Este mensaje ha sido automáticamente generado por SAVIA 2.0
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                </html>
                """
                try:
                    email = EmailMessage(
                    f'Compra Autorizada {compra.folio}|SAVIA',
                    body=html_message2,
                    from_email =settings.DEFAULT_FROM_EMAIL,
                    to= ['ulises_huesc@hotmail.com', compra.creada_por.staff.staff.email, compra.proveedor.email,],
                    headers={'Content-Type': 'text/html'}
                    )
                    #print('Correo enviadoooooooooooo')
                    #print(compra.creada_por.staff.staff.email)
                    email.content_subtype = "html " # Importante para que se interprete como HTML
                    if compra.entrada_completa == False:
                        email.attach(f'OC_folio_{compra.folio}.pdf',archivo_oc,'application/pdf')
                    email.attach(f'Politica_antisoborno.pdf', pdf_antisoborno, 'application/pdf')
                    email.attach(f'Aviso_de_privacidad.pdf', pdf_privacidad, 'application/pdf')
                    email.attach(f'Codigo_de_etica.pdf', pdf_etica, 'application/pdf')
                    email.attach(f'Politica_de_proveedor.pdf', pdf_politica_proveedor, 'application/pdf')
                    #email.attach('Pago.pdf',request.FILES['comprobante_pago'].read(),'application/pdf')
                    archivo_comprobante = request.FILES.get('comprobante_pago')
                    if archivo_comprobante:  # Verifica que el archivo exista en el request
                        archivo_contenido = archivo_comprobante.read()
                        email.attach('Pago.pdf', archivo_contenido, 'application/pdf')
                    for archivo in pagos:
                        if archivo.comprobante_pago:  # Verificar que el archivo exista
                                with open(archivo.comprobante_pago.path, 'rb') as file:  # Abrir el archivo
                                    archivo_contenido = file.read()  # Leer el contenido
                                    nombre_archivo = f'Pago_{archivo.id}.pdf'  
                                    email.attach(nombre_archivo, archivo_contenido, 'application/pdf') 
                    # Adjuntar los archivos con nombres personalizados
                    for articulo in productos:
                        producto = articulo.producto.producto.articulos.producto.producto
                        if producto.critico:
                            requerimientos = producto.producto_calidad.requerimientos_calidad.all()
                            contador = 1  # Contador para evitar nombres duplicados
                            for requerimiento in requerimientos:
                                archivo_path = requerimiento.url.path
                                nombre_archivo = f"{producto.codigo}_requerimiento_{contador}{os.path.splitext(archivo_path)[1]}"
                                
                                # Abrir el archivo en modo binario y adjuntarlo directamente
                                with open(archivo_path, 'rb') as archivo:
                                    email.attach(nombre_archivo, archivo.read())

                                contador += 1  # Incrementar el contador para el siguiente archivo
                    email.send()
                    messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.staff.first_name}')
                except (BadHeaderError, SMTPException, socket.gaierror) as e:
                    error_message = f'Gracias por registrar tu pago, {usuario.staff.staff.first_name} Atencion: el correo de notificación no ha sido enviado debido a un error: {e}'
                    messages.warning(request, error_message)
            elif round(monto_total_pagado,2) > round(costo_oc,2):
                messages.error(request,f'El monto total pagado es mayor que el costo de la compra {monto_total_pagado} > {costo_oc}')

            pago.save()
            compra.save()
            form.save()
            sub.save()
            cuenta.save()
            messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.staff.first_name}')
            return redirect(redirect_url)#No content to render nothing and send a "signal" to javascript in order to close window
            #elif monto_pagado > compra.costo_oc:
            #    messages.error(request,f'El monto total pagado es mayor que el costo de la compra {monto_pagado} > {compra.costo_oc}')
        else:
            form = PagoForm()
            messages.error(request,f'{usuario.staff.staff.first_name}, No se pudo subir tu documento')
    #else:
    #    messages.error(request,f'{usuario.staff.staff.first_name}, No está validando')

    context= {
        'compra':compra,
        'pago':pago,
        'form':form,
        'monto':suma_pago,
        'suma_pago_usd': suma_pago_usd,
        'pagos_alt':pagos_alt,
        'cuentas_para_select2': cuentas_para_select2,
        'remanente':remanente,
    }

    return render(request, 'tesoreria/compras_pagos.html',context)

@perfil_seleccionado_required
def edit_pago(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    pago = Pago.objects.get(id=pk)
    print('pago_id',pk)
     
    compra = Compra.objects.get(id = pago.oc.id)
    productos = ArticuloComprado.objects.filter(oc=compra.id)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    sub = Subproyecto.objects.get(id=compra.req.orden.subproyecto.id)
    pagos_alt = Pago.objects.filter(oc=compra.id, hecho=True)
    suma_pago = 0

    for item in pagos:
        if item.oc.moneda.nombre == "DOLARES":
            if item.cuenta.moneda.nombre == "PESOS":
                monto_pago = item.monto/item.tipo_de_cambio
                suma_pago = suma_pago + monto_pago
            else:
                suma_pago = suma_pago + item.monto
        else:
            suma_pago = suma_pago + item.monto


    if compra.moneda.nombre == 'PESOS':
        cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
    if compra.moneda.nombre == 'DOLARES':
        cuentas = Cuenta.objects.all()

    remanente = compra.costo_oc - suma_pago
    # Verificar si es un POST para guardar los cambios
    print(pago)
    if request.method == "POST":
        form = PagoForm(request.POST, request.FILES or None, instance=pago)
        if "btn_actualizar" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request,f'Has actualizado el pago {pago.id} de manera satisfactoria')
                # Redirigir al usuario a donde quieras luego de guardar los cambios
                return redirect('compras-autorizadas')
        if "btn_eliminar" in request.POST:
            print('ya estoy aquí')
            if compra.moneda.nombre == "PESOS":
                sub.gastado = sub.gastado - pago.monto
            if compra.moneda.nombre == "DOLARES":
                if pago.cuenta.moneda.nombre == "PESOS": #Si la cuenta es en pesos
                    sub.gastado = sub.gastado - pago.monto * pago.tipo_de_cambio
                if pago.cuenta.moneda.nombre == "DOLARES":
                    tipo_de_cambio = decimal.Decimal(dof())
                    sub.gastado = sub.gastado - pago.monto * tipo_de_cambio
                messages.success(request,f'Has eliminado el pago {pago.id} de manera satisfactoria')
            pago.delete()
            return redirect('compras-autorizadas')
    else:
        # Si no es un POST, simplemente carga el formulario con el objeto Pago
        form = PagoForm(instance=pago)


    context= {
        'compra':compra,
        'pago':pago,
        'form':form,
        'monto':suma_pago,
        'suma_pagos': suma_pago,
        'pagos_alt':pagos_alt,
        'cuentas':cuentas,
        'remanente':remanente,
    }
    return render(request, 'tesoreria/compras_pagos.html', context)


@perfil_seleccionado_required
def edit_comprobante_pago(request, pk):
    pago = Pago.objects.get(id = pk)
    #print(pago.id)
    form = ComprobanteForm(instance = pago)

    if request.method == 'POST':
        form = ComprobanteForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'pago':pago,
        'form':form, 
    }
    
    return render(request, 'tesoreria/edit_comprobante_pago.html',context)


@perfil_seleccionado_required
def saldo_a_favor(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id=pk)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    saldo, created = Comprobante_saldo_favor.objects.get_or_create(oc=compra, hecho=False)
    form2 = Saldo_Form(instance = saldo)
    form = CompraSaldo_Form(instance = compra)
    suma_pago = 0
    for item in pagos:
        if item.oc.moneda.nombre == "DOLARES":
            if item.cuenta.moneda.nombre == "PESOS":
                monto_pago = item.monto/item.tipo_de_cambio
                suma_pago = suma_pago + monto_pago
            else:
                suma_pago = suma_pago + item.monto
        else:
            suma_pago = suma_pago + item.monto

    remanente = compra.costo_oc - suma_pago


    if request.method == 'POST':
        form2 = Saldo_Form(request.POST, request.FILES, instance = saldo)
        form = CompraSaldo_Form( request.POST, instance = compra)
        if form.is_valid() and form2.is_valid():
            form.save()
            saldo = form2.save(commit=False)
            saldo.subido_por = usuario
            saldo.fecha_subido = date.today()
            saldo.hora_subido = datetime.now().time()
            saldo.hecho = True
            saldo.save()
            if remanente <= compra.saldo_a_favor:
                compra.pagada = True
            compra.save()
            messages.success(request,f'El saldo se ha registrado correctamente, {usuario.staff.staff.first_name}')
            return HttpResponse(status=204) 

    context= {
        'compra':compra,
        'monto':suma_pago,
        'remanente':remanente,
        'form':form,
        'form2':form2,
    }

    return render(request, 'tesoreria/saldo_a_favor.html',context)

# Create your views here.
@perfil_seleccionado_required
def matriz_pagos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    almacenes_distritos = set(usuario.almacen.values_list('distrito__id', flat=True))
    if usuario.tipo.rh == True and usuario.tipo.documentos == True:
        pagos = Pago.objects.filter(
        gasto__distrito__in = almacenes_distritos, gasto__autorizar2 = True, gasto__tipo__tipo__in = ['APOYO DE MANTENIMIENTO', 'APOYO DE RENTA'] , 
        hecho=True
        ).annotate(
        # Detectar la relación que tiene facturas
        total_facturas=Count(
            'oc__facturas', filter=Q(oc__facturas__hecho=True)
        ) + Count(
            'gasto__facturas__hecho', filter=Q(gasto__facturas__hecho=True)
        ) + Count(
            'viatico__facturas__hecho', filter=Q(viatico__facturas__hecho=True)
        ),
        autorizadas=Count(
            Case(
                When(Q(oc__facturas__autorizada=True, oc__facturas__hecho=True), then=Value(1))
            )
        ) + Count(
            Case(
                When(Q(gasto__facturas__autorizada=True, gasto__facturas__hecho=True), then=Value(1))
            )
        ) + Count(
            Case(
                When(Q(viatico__facturas__autorizada=True, viatico__facturas__hecho=True), then=Value(1))
            )
        ),
        ).order_by('-pagado_real')  
    else:    
        pagos = Pago.objects.filter(
        Q(oc__req__orden__distrito__in =almacenes_distritos) & Q(oc__autorizado2=True) | 
        Q(viatico__distrito__in = almacenes_distritos) & Q(viatico__autorizar2=True) |
        Q(gasto__distrito__in = almacenes_distritos) & Q(gasto__autorizar2 = True), 
        hecho=True
        ).annotate(
        # Detectar la relación que tiene facturas
        total_facturas=Count(
            'oc__facturas', filter=Q(oc__facturas__hecho=True)
        ) + Count(
            'gasto__facturas__hecho', filter=Q(gasto__facturas__hecho=True)
        ) + Count(
            'viatico__facturas__hecho', filter=Q(viatico__facturas__hecho=True)
        ),
        autorizadas=Count(
            Case(
                When(Q(oc__facturas__autorizada=True, oc__facturas__hecho=True), then=Value(1))
            )
        ) + Count(
            Case(
                When(Q(gasto__facturas__autorizada=True, gasto__facturas__hecho=True), then=Value(1))
            )
        ) + Count(
            Case(
                When(Q(viatico__facturas__autorizada=True, viatico__facturas__hecho=True), then=Value(1))
            )
        ),
        ).order_by('-pagado_real')
    myfilter = Matriz_Pago_Filter(request.GET, queryset=pagos)
    pagos = myfilter.qs
    #Los distritos se definen de forma "dinámica" de acuerdo a los almacenes que tiene el usuario en el perfil
    distritos = Distrito.objects.filter(id__in=almacenes_distritos)
    tesoreros = Profile.objects.filter(tipo__nombre__in = ["Tesoreria","Tesoreria_Documentos" ], st_activo = True, distritos__in = almacenes_distritos)
    #Set up pagination
    p = Paginator(pagos, 50)
    page = request.GET.get('page')
    pagos_list = p.get_page(page)
    

    if request.method == 'POST': 
        if 'btnReporte' in request.POST:
            return convert_excel_matriz_pagos(pagos)
        elif 'btnDescargarFacturas' in request.POST:
            fecha_inicio = parse_date(request.POST.get('fecha_inicio'))
            fecha_fin = parse_date(request.POST.get('fecha_fin'))
            distrito_id = request.POST.get('distrito')
            tesorero_id = request.POST.get('tesorero')
            folio = request.POST.get('folio')
            validar_sat = request.POST.get('validacion') == 'on'
            

            if usuario.distritos.nombre == "MATRIZ":
                pagos = Pago.objects.filter(hecho=True)
                if fecha_inicio and fecha_fin:
                    pagos = Pago.objects.filter(Q(pagado_real__range=[fecha_inicio, fecha_fin])|Q(pagado_date__range=[fecha_inicio, fecha_fin]), hecho = True)
              
                    if distrito_id:
                        pagos = pagos.filter(
                            Q(gasto__distrito_id=distrito_id) |
                            Q(oc__req__orden__distrito_id=distrito_id) |
                            Q(viatico__distrito_id=distrito_id)
                        )

                    if tesorero_id:
                        pagos = pagos.filter(tesorero_id=tesorero_id)

                if folio:
                    pagos = Pago.objects.filter(hecho = True)
                    pagos = pagos.filter(
                        Q(gasto__folio=folio) |
                        Q(oc__folio=folio) |
                        Q(viatico__folio=folio)
                    )
                    print('pagos',pagos)
            else:
                pagos = pagos.filter(
                    Q(pagado_real__range=[fecha_inicio, fecha_fin])|Q(pagado_date__range=[fecha_inicio, fecha_fin]),
                    Q(gasto__distrito=usuario.distritos) |
                    Q(oc__req__orden__distrito=usuario.distritos) |
                    Q(viatico__distrito=usuario.distritos)
                )


            if validar_sat:
                ids_gastos = set()
                ids_compras = set()
                ids_viaticos = set()
                #print(f"Pagos: {pagos.count()}")
                for pago in pagos:
                    if pago.gasto:
                        ids_gastos.update(pago.gasto.facturas.values_list('id', flat=True))
                    elif pago.oc:
                        ids_compras.update(pago.oc.facturas.values_list('id', flat=True))
                    elif pago.viatico:
                        ids_viaticos.update(pago.viatico.facturas.values_list('id', flat=True))
                print(ids_gastos, ids_compras, ids_viaticos)
                validar_lote_facturas.delay(list(ids_gastos), list(ids_compras), list(ids_viaticos))
            else:
                zip_buffer = BytesIO()
                datos_xml_lista = []
                processed_docs = set()

                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    #zip_file.mkdir("GENERAL_PDFs")
                    #zip_file.mkdir("GENERAL_XMLs")

                    for pago in pagos:
                        if pago.gasto:
                            gasto = pago.gasto
                            carpeta = f'{pago.pagado_real}_GASTO_{gasto.folio}_{gasto.distrito.nombre}'
                            #zip_file.mkdir(carpeta)
                            for factura in gasto.facturas.all():
                                beneficiario = factura.solicitud_gasto.colaborador.staff.staff.first_name + ' ' + factura.solicitud_gasto.colaborador.staff.staff.last_name  if factura.solicitud_gasto.colaborador else factura.solicitud_gasto.staff.staff.staff.first_name + ' ' + factura.solicitud_gasto.staff.staff.staff.last_name
                                fecha_subida = factura.fecha_subida.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subida else 'No disponible'
                                if factura.archivo_pdf:
                                    zip_file.write(factura.archivo_pdf.path, os.path.join(carpeta, os.path.basename(factura.archivo_pdf.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    zip_file.write(factura.archivo_pdf.path, f"GENERAL_PDFs/{factura.id}_{uuid}.pdf")
                                if factura.archivo_xml:
                                    zip_file.write(factura.archivo_xml.path, os.path.join(carpeta, os.path.basename(factura.archivo_xml.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    gen_path = f"GENERAL_XMLs/{factura.id}_{uuid}.xml"
                                    zip_file.write(factura.archivo_xml.path, gen_path)
                                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.archivo_xml.path, f"G{gasto.folio}", fecha_subida, gasto.distrito.nombre, beneficiario, gen_path, factura))
                            if gasto.id not in processed_docs:
                                pdf_buf = render_pdf_gasto(gasto.id)
                                zip_file.writestr(os.path.join(carpeta, f'GASTO_{gasto.folio}.pdf'), pdf_buf.getvalue())
                                processed_docs.add(gasto.id)
                        elif pago.oc:
                            oc = pago.oc
                            carpeta = f'{pago.pagado_real}_COMPRA_{oc.folio}_{oc.req.orden.distrito.nombre}'
                            #zip_file.mkdir(carpeta)
                            for factura in oc.facturas.all():
                                if factura.factura_pdf:
                                    zip_file.write(factura.factura_pdf.path, os.path.join(carpeta, os.path.basename(factura.factura_pdf.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    zip_file.write(factura.factura_pdf.path, f"GENERAL_PDFs/{factura.id}_{uuid}.pdf")
                                if factura.factura_xml:
                                    zip_file.write(factura.factura_xml.path, os.path.join(carpeta, os.path.basename(factura.factura_xml.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    gen_path = f"GENERAL_XMLs/{factura.id}_{uuid}.xml"
                                    zip_file.write(factura.factura_xml.path, gen_path)
                                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, f"OC{oc.folio}", factura.fecha_subido, oc.req.orden.distrito.nombre, "NA", gen_path, factura))
                            if oc.id not in processed_docs:
                                pdf_buf = generar_pdf(oc)
                                zip_file.writestr(os.path.join(carpeta, f'OC_{oc.folio}.pdf'), pdf_buf.getvalue())
                                processed_docs.add(oc.id)
                        elif pago.viatico:
                            viatico = pago.viatico
                            carpeta = f'{pago.pagado_real}_VIATICO_{viatico.folio}_{viatico.distrito.nombre}'
                            #zip_file.mkdir(carpeta)
                            for factura in viatico.facturas.all():
                                beneficiario = factura.solicitud_viatico.colaborador.staff.staff.first_name + ' ' + factura.solicitud_viatico.colaborador.staff.staff.last_name  if factura.solicitud_viatico.colaborador else factura.solicitud_gasto.staff.staff.staff.first_name + ' ' + factura.solicitud_gasto.staff.staff.staff.last_name
                                fecha_subida = factura.fecha_subido.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subido else 'No disponible' # Formato YYYY-MM-DD
                                if factura.factura_pdf:
                                    zip_file.write(factura.factura_pdf.path, os.path.join(carpeta, os.path.basename(factura.factura_pdf.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    zip_file.write(factura.factura_pdf.path, f"GENERAL_PDFs/{factura.id}_{uuid}.pdf")
                                if factura.factura_xml:
                                    zip_file.write(factura.factura_xml.path, os.path.join(carpeta, os.path.basename(factura.factura_xml.path)))
                                    uuid = factura.uuid if factura.uuid else 'SIN_UUID'
                                    gen_path = f"GENERAL_XMLs/{factura.id}_{uuid}.xml"
                                    zip_file.write(factura.factura_xml.path, gen_path)
                                    datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, f"V{viatico.folio}", fecha_subida, viatico.distrito.nombre, beneficiario, gen_path, factura))
                            if viatico.id not in processed_docs:
                                pdf_buf = generar_pdf_viatico(viatico.id)
                                zip_file.writestr(os.path.join(carpeta, f'VIATICO_{viatico.folio}.pdf'), pdf_buf.getvalue())
                                processed_docs.add(viatico.id)

                        if pago.comprobante_pago:
                            zip_file.write(pago.comprobante_pago.path, os.path.join(carpeta, os.path.basename(pago.comprobante_pago.path)))

                        # Excel de resumen
                    output = BytesIO()
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Resumen XML"
                    columnas = ['Distrito','Folio','Fecha subida','Fecha factura', 'Razón Social', 'Folio Fiscal (UUID)', 
                                'Monto Total Factura', 'Tipo de Moneda', 'Forma de pago','Método de Pago',
                                'Receptor (Empresa) Nombre', 'Beneficiario', 'Archivo', 'Tipo de Documento','Fecha Validación SAT', 'EstadoSAT']
                    ws.append(columnas)
                    for dato in datos_xml_lista:
                        ws.append([dato.get(col, '') for col in columnas])
                    for col in ['G']:
                        for row in range(2, ws.max_row + 1):
                            ws[f"{col}{row}"].number_format = numbers.FORMAT_CURRENCY_USD_SIMPLE
                    wb.save(output)
                    zip_file.writestr("GENERAL_XMLs/reporte_facturas.xlsx", output.getvalue())

                zip_buffer.seek(0)
                response = HttpResponse(zip_buffer, content_type='application/zip')
                response.set_cookie('descarga_iniciada', 'true', max_age=20)
                response['Content-Disposition'] = 'attachment; filename=pagos.zip'
                return response
        
        elif 'btnDescargar' in request.POST:
            validar_sat = request.POST.get('validacion') == 'on'
            fecha_inicio = parse_date(request.POST.get('fecha_inicio'))
            fecha_fin = parse_date(request.POST.get('fecha_fin'))
            distrito_id = request.POST.get('distrito')
            tesorero_id = request.POST.get('tesorero')
            folio = request.POST.get('folio')
            print(folio)
            tipo_documento = request.POST.get('tipo_documento')

            facturas_gastos = Factura.objects.none()
            facturas_compras = Facturas.objects.none()
            facturas_viaticos = Viaticos_Factura.objects.none()
            
            if usuario.distritos.nombre == "MATRIZ":
                if tipo_documento in ["", "gastos"]:
                    facturas_gastos = Factura.objects.filter(Q(solicitud_gasto__pagosg__pagado_real__range=[fecha_inicio, fecha_fin])|Q(solicitud_gasto__pagosg__pagado_date__range=[fecha_inicio, fecha_fin]))
                if tipo_documento in ["", "compras"]:    
                    facturas_compras = Facturas.objects.filter(Q(oc__pagos__pagado_real__range=[fecha_inicio, fecha_fin])|Q(oc__pagos__pagado_date__range=[fecha_inicio, fecha_fin]), hecho = True)
                if tipo_documento in ["", "viaticos"]:
                    facturas_viaticos = Viaticos_Factura.objects.filter(Q(solicitud_viatico__pagosv__pagado_real__range=[fecha_inicio, fecha_fin])|Q(solicitud_viatico__pagosv__pagado_date__range=[fecha_inicio, fecha_fin]))

                if distrito_id:
                    facturas_gastos = facturas_gastos.filter(solicitud_gasto__distrito_id=distrito_id)
                    facturas_compras = facturas_compras.filter(oc__req__orden__distrito_id=distrito_id)
                    facturas_viaticos = facturas_viaticos.filter(solicitud_viatico__distrito_id=distrito_id)

                if tesorero_id:
                    facturas_gastos = facturas_gastos.filter(solicitud_gasto__pagosg__tesorero__id=tesorero_id)
                    facturas_compras = facturas_compras.filter(oc__pagos__tesorero__id=tesorero_id)
                    facturas_viaticos = facturas_viaticos.filter(solicitud_viatico__pagosv__tesorero__id=tesorero_id)
                
                if folio:
                    #print('folio',int(folio))
                    #viatico = Solicitud_Viatico.objects.get(folio = folio)
                    facturas_gastos = Factura.objects.filter(solicitud_gasto__folio = folio)
                    facturas_compras = Facturas.objects.filter(oc__folio= folio)
                    facturas_viaticos = Viaticos_Factura.objects.filter(solicitud_viatico__folio = folio)
                    #print('viatico',viatico)
                    #print('facturas_gastos',facturas_gastos)
                    #print('facturas_compras',facturas_compras)
                    #print('facturas_viaticos',facturas_viaticos)

            else:
                facturas_gastos = Factura.objects.filter(solicitud_gasto__approbado_fecha2__range=[fecha_inicio, fecha_fin], solicitud_gasto__distrito = usuario.distritos)
                facturas_compras = Facturas.objects.filter(oc__autorizado_at_2__range=[fecha_inicio, fecha_fin], oc__req__orden__distrito = usuario.distritos)
                facturas_viaticos = Viaticos_Factura.objects.filter(solicitud_viatico__approved_at2__range=[fecha_inicio, fecha_fin], solicitud_viatico__distrito = usuario.distritos)

            if validar_sat:
                ids_gastos = list(facturas_gastos.values_list('id', flat=True))
                ids_compras = list(facturas_compras.values_list('id', flat=True))
                ids_viaticos = list(facturas_viaticos.values_list('id', flat=True))
                #print(ids_viaticos)

                validar_lote_facturas.delay(ids_gastos, ids_compras, ids_viaticos)
                
                
                #for factura in facturas_gastos:
                #    if factura.archivo_xml:
                #        extraer_datos_validacion(factura.archivo_xml.path, factura)
                #for factura in facturas_compras:
                #    if factura.factura_xml:
                #        extraer_datos_validacion(factura.factura_xml.path, factura)
                
                #for factura in facturas_viaticos:
                #    if factura.factura_xml:
                #        extraer_datos_validacion(factura.factura_xml.path, factura)  

            else:
                zip_buffer = BytesIO()
                processed_ocs = set()  # Mantén un conjunto de OCs procesadas
                processed_gastos = set()  # Mantén un conjunto de gastos procesados
                processed_viaticos = set()  # Mantén un conjunto de viáticos procesados
                processed_pagos = set()  # Mantén un conjunto de pagos procesados
                datos_xml_lista = []  # Lista para el resumen en Excel

                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    #Se agrgean carpetas generales
                    general_pdfs_folder = "GENERAL_PDFs"
                    general_xmls_folder = "GENERAL_XMLs"
                    
                    #Se procesan facturas de gastos
                    for factura in facturas_gastos:
                        folder_name = f'GASTO_{factura.solicitud_gasto.folio}_{factura.solicitud_gasto.distrito.nombre}'
                        if factura.archivo_pdf:   
                            file_name = os.path.basename(factura.archivo_pdf.path)
                            zip_file.write(factura.archivo_pdf.path, os.path.join(folder_name, file_name))
                            if factura.archivo_xml:
                                # Guardar en la carpeta GENERAL_PDFs con nombre id_uuid.pdf
                                uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                                general_file_name = f'{factura.id}_{uuid_str}.pdf'
                            else:
                                general_file_name = file_name
                            zip_file.write(factura.archivo_pdf.path, os.path.join(general_pdfs_folder, general_file_name)) #Está línea guarda en el zip general de pdf
                        
                        beneficiario = factura.solicitud_gasto.colaborador.staff.staff.first_name + ' ' + factura.solicitud_gasto.colaborador.staff.staff.last_name  if factura.solicitud_gasto.colaborador else factura.solicitud_gasto.staff.staff.staff.first_name + ' ' + factura.solicitud_gasto.staff.staff.staff.last_name
                        distrito = factura.solicitud_gasto.distrito.nombre  # Obtener distrito de la factura
                        folio = 'G' + str(factura.solicitud_gasto.folio)
                        fecha_subida = factura.fecha_subida.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subida else 'No disponible'
                        if factura.archivo_xml:
                            file_name = os.path.basename(factura.archivo_xml.path)
                            zip_file.write(factura.archivo_xml.path, os.path.join(folder_name, file_name))
                            uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                            general_file_name = f'{factura.id}_{uuid_str}.xml'

                            zip_file.write(factura.archivo_xml.path, os.path.join(general_xmls_folder, general_file_name)) #Está línea guarda en el zip general de xml's
                            datos_xml_lista.append(extraer_datos_xml_carpetas(factura.archivo_xml.path, folio, fecha_subida, distrito, beneficiario, general_file_name, factura))

                        if factura.solicitud_gasto.id not in processed_gastos:
                            buf = render_pdf_gasto(factura.solicitud_gasto.id)
                            gasto_file_name = f'GASTO_{factura.solicitud_gasto.folio}.pdf'
                            zip_file.writestr(os.path.join(folder_name, gasto_file_name), buf.getvalue())
                            processed_gastos.add(factura.solicitud_gasto.id)

                        pagos = Pago.objects.filter(gasto=factura.solicitud_gasto)
                        for pago in pagos:
                            if pago.comprobante_pago and pago.id not in processed_pagos:
                                texto_pago = extraer_texto_pdf_prop(pago.comprobante_pago)
                                variables_pago = encontrar_variables(texto_pago)

                                fecha_pago = variables_pago.get('fecha', '').replace('/', '-')
                                titular_cuenta_2 = variables_pago.get('titular_cuenta_2', '')
                                importe_operacion = variables_pago.get('importe_operacion', '').split('.')[0].replace(',', '')

                                # Validamos si todas las variables son válidas:
                                if fecha_pago and fecha_pago != 'No disponible' and titular_cuenta_2 and titular_cuenta_2 != 'No disponible' and importe_operacion and importe_operacion != 'No disponible':
                                    pago_file_name = f'{fecha_pago} {titular_cuenta_2} ${importe_operacion}.pdf'
                                else:
                                    # Si no, conservamos el nombre original
                                    pago_file_name = os.path.basename(pago.comprobante_pago.path)
                                
                                #pago_file_name = os.path.basename(pago.comprobante_pago.path)
                                zip_file.write(pago.comprobante_pago.path, os.path.join(folder_name, f'{pago_file_name}'))
                                processed_pagos.add(pago.id)
                    
                    #Se procesan facturas de compras
                    for factura in facturas_compras:
                        folder_name = f'COMPRA_{factura.oc.folio}_{factura.oc.req.orden.distrito.nombre}'
                        if factura.factura_pdf:
                            #folder_name = f'COMPRA_{factura.oc.folio}_{factura.oc.req.orden.distrito.nombre}'
                            file_name = os.path.basename(factura.factura_pdf.path)
                            zip_file.write(factura.factura_pdf.path, os.path.join(folder_name, file_name))
                            if factura.factura_xml:
                                # Guardar en la carpeta GENERAL_PDFs con nombre id_uuid.pdf
                                uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                                general_file_name = f'{factura.id}_{uuid_str}.pdf'
                            else:
                                general_file_name = file_name

                            zip_file.write(factura.factura_pdf.path, os.path.join(general_pdfs_folder, file_name))

                        beneficiario = "NA"
                        distrito = factura.oc.req.orden.distrito.nombre  # Obtener distrito de la factura
                        folio = factura.oc.folio
                        fecha_subida = factura.fecha_subido if factura.fecha_subido else 'No disponible'
                        if factura.factura_xml:
                            file_name = os.path.basename(factura.factura_xml.path)
                            zip_file.write(factura.factura_xml.path, os.path.join(folder_name, file_name))
                            uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                            general_file_name = f'{factura.id}_{uuid_str}.xml'
                            
                            zip_file.write(factura.factura_xml.path, os.path.join(general_xmls_folder, general_file_name))
                            datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, folio, fecha_subida, distrito, beneficiario, general_file_name, factura))
                        
                        # Incluir la ficha de pago
                        pagos = Pago.objects.filter(oc=factura.oc)
                        for pago in pagos:
                            if pago.comprobante_pago and pago.id not in processed_pagos:
                                texto_pago = extraer_texto_pdf_prop(pago.comprobante_pago)
                                variables_pago = encontrar_variables(texto_pago)

                                fecha_pago = variables_pago.get('fecha', '').replace('/', '-')
                                titular_cuenta_2 = variables_pago.get('titular_cuenta_2', '')
                                importe_operacion = variables_pago.get('importe_operacion', '').split('.')[0].replace(',', '')


                                if fecha_pago and fecha_pago != 'No disponible' and titular_cuenta_2 and titular_cuenta_2 != 'No disponible' and importe_operacion and importe_operacion != 'No disponible':
                                    pago_file_name = f'{fecha_pago} {titular_cuenta_2} ${importe_operacion}.pdf'
                                else:
                                    pago_file_name = os.path.basename(pago.comprobante_pago.path)
                                #pago_file_name = os.path.basename(pago.comprobante_pago.path)

                                zip_file.write(pago.comprobante_pago.path, os.path.join(folder_name, f'{pago_file_name}'))
                                processed_pagos.add(pago.id)
                        
                        # Generar e incluir la OC en el ZIP solo si no ha sido procesada
                        if factura.oc.id not in processed_ocs:
                            buf = generar_pdf(factura.oc)
                            oc_file_name = f'OC_{factura.oc.folio}.pdf'
                            zip_file.writestr(os.path.join(folder_name, oc_file_name), buf.getvalue())
                            processed_ocs.add(factura.oc.id)
                    

                    for factura in facturas_viaticos:
                        folder_name = f'VIATICO_{factura.solicitud_viatico.folio}_{factura.solicitud_viatico.distrito.nombre}'
                        if factura.factura_pdf:

                            file_name = os.path.basename(factura.factura_pdf.path)
                            zip_file.write(factura.factura_pdf.path, os.path.join(folder_name, file_name))
                            if factura.factura_xml:
                                # Guardar en la carpeta GENERAL_PDFs con nombre id_uuid.pdf
                                uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                                general_file_name = f'{factura.id}_{uuid_str}.pdf'
                            else:
                                general_file_name = file_name
                            zip_file.write(factura.factura_pdf.path, os.path.join(general_pdfs_folder, general_file_name))

                        beneficiario = factura.solicitud_viatico.colaborador.staff.staff.first_name + ' ' + factura.solicitud_viatico.colaborador.staff.staff.last_name  if factura.solicitud_viatico.colaborador else factura.solicitud_gasto.staff.staff.staff.first_name + ' ' + factura.solicitud_gasto.staff.staff.staff.last_name
                        distrito = factura.solicitud_viatico.distrito.nombre  # Obtener distrito de la factura
                        folio = 'V' + str(factura.solicitud_viatico.folio)
                        fecha_subida = factura.fecha_subido.astimezone(tz=None).replace(tzinfo=None) if factura.fecha_subido else 'No disponible' # Formato YYYY-MM-DD
                        if factura.factura_xml:
                            file_name = os.path.basename(factura.factura_xml.path)
                            zip_file.write(factura.factura_xml.path, os.path.join(folder_name, file_name))
                            uuid_str = factura.uuid if factura.uuid else 'SIN_UUID'
                            general_file_name = f'{factura.id}_{uuid_str}.xml'

                            zip_file.write(factura.factura_xml.path, os.path.join(general_xmls_folder, general_file_name))
                            datos_xml_lista.append(extraer_datos_xml_carpetas(factura.factura_xml.path, folio, fecha_subida, distrito, beneficiario, general_file_name, factura))

                        if factura.solicitud_viatico.id not in processed_viaticos:
                            buf = generar_pdf_viatico(factura.solicitud_viatico.id)
                            viatico_file_name = f'VIATICO_{factura.solicitud_viatico.folio}.pdf'
                            zip_file.writestr(os.path.join(folder_name, viatico_file_name), buf.getvalue())
                            processed_viaticos.add(factura.solicitud_viatico.id)

                    
                        
                        pagos = Pago.objects.filter(viatico=factura.solicitud_viatico)
                        for pago in pagos:
                            if pago.comprobante_pago and pago.id not in processed_pagos:
                                texto_pago = extraer_texto_pdf_prop(pago.comprobante_pago)
                                variables_pago = encontrar_variables(texto_pago)

                                fecha_pago = variables_pago.get('fecha', '').replace('/', '-')
                                titular_cuenta_2 = variables_pago.get('titular_cuenta_2', '')
                                importe_operacion = variables_pago.get('importe_operacion', '').split('.')[0].replace(',', '')

                                if fecha_pago and fecha_pago != 'No disponible' and titular_cuenta_2 and titular_cuenta_2 != 'No disponible' and importe_operacion and importe_operacion != 'No disponible':
                                    pago_file_name = f'{fecha_pago} {titular_cuenta_2} ${importe_operacion}.pdf'
                                else:
                                    pago_file_name = os.path.basename(pago.comprobante_pago.path)
                                
                                #pago_file_name = os.path.basename(pago.comprobante_pago.path)
                                zip_file.write(pago.comprobante_pago.path, os.path.join(folder_name, f'{pago_file_name}'))
                                processed_pagos.add(pago.id)

                    # Crear archivo Excel con los datos extraídos
                    output = BytesIO()
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Resumen XML"

                    columnas = ['Distrito','Folio','Fecha subida','Fecha factura', 'Razón Social', 'Folio Fiscal (UUID)', 
                                'Monto Total Factura', 'Tipo de Moneda', 'Forma de pago','Método de Pago',
                                'Receptor (Empresa) Nombre', 'Beneficiario', 'Archivo', 'Tipo de Documento','Fecha Validación SAT', 'EstadoSAT'
                                ]
                    ws.append(columnas)

                    for dato in datos_xml_lista:
                        ws.append([dato.get(col, '') for col in columnas])

                    # Formatos de Excel
                    for col in ['G']:  # Monto Total Factura
                        for row in range(2, ws.max_row + 1):
                            ws[f"{col}{row}"].number_format = numbers.FORMAT_CURRENCY_USD_SIMPLE

                    wb.save(output)
                    zip_file.writestr("GENERAL_XMLs/reporte_facturas.xlsx", output.getvalue())

                zip_buffer.seek(0)
                response = HttpResponse(zip_buffer, content_type='application/zip')
                response.set_cookie('descarga_iniciada', 'true', max_age=20)
                response['Content-Disposition'] = 'attachment; filename=facturas.zip'
                return response
    for pago in pagos_list:
        if pago.total_facturas == 0:
            pago.estado_facturas = 'sin_facturas'
        elif pago.autorizadas == pago.total_facturas:
            pago.estado_facturas = 'todas_autorizadas'
        else:
            pago.estado_facturas = 'pendientes'
    context= {
        'pagos_list':pagos_list,
        'pagos':pagos,
        'myfilter':myfilter,
        'tesoreros':tesoreros,
        'distritos':distritos,
        'usuario':usuario,
        }

    return render(request, 'tesoreria/matriz_pagos.html',context)

@perfil_seleccionado_required
def control_cuentas(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    
    cuentas = Cuenta.objects.filter(encargado = usuario)
    
    context= {
        'cuentas': cuentas,
        }

    return render(request, 'tesoreria/control_cuentas.html',context)


@perfil_seleccionado_required
def control_bancos(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    #usuario = Profile.objects.get(id = pk_profile)
    # Obtener la cuenta seleccionada en el filtro
    
    cuenta = Cuenta.objects.get(id=pk)
    pagos = Pago.objects.filter(cuenta = cuenta, hecho= True).order_by('-indice')

    myfilter = Matriz_Pago_Filter(request.GET, queryset=pagos)
    pagos = myfilter.qs
    
    p = Paginator(pagos, 25)
    page = request.GET.get('page')
    pagos_list = p.get_page(page)

    if request.method == 'POST' and 'btnReporte' in request.POST:
        #pagos = pagos.order_by('pagado_real')
        return convert_excel_control_bancos(pagos)
           

    context= {
        'pagos_list':pagos_list,
        'pagos':pagos,
        'myfilter':myfilter,
        'latest_balance': saldo_inicial,
        }

    return render(request, 'tesoreria/control_bancos.html',context)


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
    try:
        # Parsear el archivo XML
        archivo_xml.seek(0)
        tree = ET.parse(archivo_xml)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"Error al parsear el archivo XML: {e}")
        return None, None  # Si ocurre un error, devuelve None
    
    # Identificar la versión del XML y el espacio de nombres
    version = root.tag
    ns = {}
    if 'http://www.sat.gob.mx/cfd/3' in version:
        ns = {
            'cfdi': 'http://www.sat.gob.mx/cfd/3',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
            'if': 'https://www.interfactura.com/Schemas/Documentos',
        }
    elif 'http://www.sat.gob.mx/cfd/4' in version:
        ns = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
            'if': 'https://www.interfactura.com/Schemas/Documentos',
        }
    else:
        print(f"Versión del documento XML no reconocida")
        return None, None
    
    # Buscar el complemento donde se encuentra el UUID y la fecha de timbrado
    complemento = root.find('cfdi:Complemento', ns)
    if complemento is not None:
        timbre_fiscal = complemento.find('tfd:TimbreFiscalDigital', ns)
        if timbre_fiscal is not None:
            uuid = timbre_fiscal.get('UUID')
            fecha_timbrado = timbre_fiscal.get('FechaTimbrado') or root.get('Fecha')
            return uuid, fecha_timbrado  # Devolver UUID y fecha de timbrado
        else:
            print("Timbre Fiscal Digital no encontrado")
            return None, None
    else:
        print("Complemento no encontrado")
        return None, None
    
import xml.etree.ElementTree as ET

def extraer_datos_del_complemento(ruta_xml):
    try:
        # Parsear el archivo XML
        tree = ET.parse(ruta_xml)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"Error al parsear el archivo XML: {e}")
        return None, None  # Si ocurre un error, devolver None
    
    # Definir espacios de nombres
    ns = {
        'cfdi': 'http://www.sat.gob.mx/cfd/4',
        'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        'pago20': 'http://www.sat.gob.mx/Pagos20'
    }
    
    # Buscar el UUID en TimbreFiscalDigital
    uuid = None
    complemento = root.find('cfdi:Complemento', ns)
    if complemento is not None:
        timbre_fiscal = complemento.find('tfd:TimbreFiscalDigital', ns)
        if timbre_fiscal is not None:
            uuid = timbre_fiscal.get('UUID', '')

    # Buscar el IdDocumento dentro de DoctoRelacionado
    docto_relacionado_id = None
    pagos = complemento.find('pago20:Pagos', ns) if complemento is not None else None
    if pagos is not None:
        pago = pagos.find('pago20:Pago', ns)
        if pago is not None:
            docto_relacionado = pago.find('pago20:DoctoRelacionado', ns)
            if docto_relacionado is not None:
                docto_relacionado_id = docto_relacionado.get('IdDocumento', '')

    return uuid, docto_relacionado_id  # Devolver UUID y IdDocumento


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
        'Monto Total Factura': monto_total,
        'Tipo de Moneda': moneda,
        'Método de Pago': metodo_pago,
        'Forma de pago': forma_pago,
        'Receptor (Empresa) Nombre': receptor.get('Nombre') if receptor is not None else '',
        'Archivo': nombre_general,
        'EstadoSAT': factura.estado_sat or '',
        'Fecha Validación SAT': timezone.localtime(factura.fecha_validacion_sat).strftime("%Y-%m-%d %H:%M:%S") if factura.fecha_validacion_sat else '',
    }
    return datos



def generar_archivo_zip(facturas, compra):
    nombre = compra.folio if compra.folio else ''
    zip_filename = f'facturas_compragasto-{nombre}.zip'
    
    # Crear un archivo zip en memoria
    in_memory_zip = io.BytesIO()

    with zipfile.ZipFile(in_memory_zip, 'w') as zip_file:
        for factura in facturas:
            if factura.factura_pdf:
                pdf_path = factura.factura_pdf.path
                zip_file.write(pdf_path, os.path.basename(pdf_path))
            if factura.factura_xml:
                # Generar el PDFreader
                response = generar_cfdi(None, factura.id)
                pdf_filename = f"{factura.id}.pdf" if factura.id else f"factura_{factura.id}.pdf"
                # Añadir el contenido del PDF al ZIP
                zip_file.writestr(pdf_filename, response.content)
                #Añadir el xml
                xml_path = factura.factura_xml.path
                zip_file.write(xml_path, os.path.basename(xml_path))

    # Resetear el puntero del archivo en memoria
    in_memory_zip.seek(0)

    return in_memory_zip, zip_filename

@perfil_seleccionado_required
def matriz_facturas_nomodal(request, pk):
    #print('estoy en matriz_facturas_nomodal')
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)

    try:
        if perfil.tipo.nombre == "PROVEEDOR_EXTERNO":
            base_url = reverse('matriz-oc-proveedores')
            compra = get_object_or_404(Compra, id=pk, proveedor__nombre = perfil.proveedor)
        else:
            compra = get_object_or_404(Compra, id=pk)
            next_url = request.GET.get('next', 'matriz-compras')
            try:
                base_url = reverse(next_url)
            except NoReverseMatch:
                base_url = next_url

    except Http404:
        messages.error(request, "No tienes acceso a esta orden de compra.")
        #return redirect(next_url)
    facturas = Facturas.objects.filter(oc = compra, hecho=True)
    pagos = Pago.objects.filter(oc = compra)
    form = Facturas_Completas_Form(instance=compra)
    # Construir los parámetros de filtro
    print('base_url',base_url)
    filtros = {
        'proveedor': request.GET.get('proveedor', ''),
        'distrito': request.GET.get('distrito', ''),
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
    }
    # Codificar los parámetros
    query_string = urlencode(filtros)
    #print('query_string:',filtros)
    
    for pago in pagos:
        fecha_pdf = None
        if pago.comprobante_pago:
            try:
                texto = extraer_texto_pdf_prop(pago.comprobante_pago)
                variables = encontrar_variables(texto)
                fecha_pdf = variables.get('fecha', 'No disponible')
            except Exception as e:
                fecha_pdf = f"Error: {str(e)}"

        pago.fecha_pdf = fecha_pdf  # Asignar el valor a la variable de instancia
        #print(pago.fecha_pdf)  # Imprimir el valor de fecha_pdf
   
    if request.method == 'POST':
        #connector = '&' if '?' in base_url else '?'
        #print(query_string)
        redirect_url = f"{base_url}?{query_string}" if query_string else base_url
        #print('imprimiendo',redirect_url)
        form = Facturas_Completas_Form(request.POST, instance=compra)
        if "btn_factura_completa" in request.POST:
            fecha_hora = datetime.today()
            for factura in facturas:
                checkbox_name = f'autorizar_factura_{factura.id}'
                #print("Nombre del checkbox esperado:", checkbox_name)  # Imprimir el nombre esperado
                if checkbox_name in request.POST:
                    factura.autorizada = True
                    factura.autorizada_por = perfil
                    factura.autorizada_el = fecha_hora
                else:
                    factura.autorizada = False
                factura.save()
            if form.is_valid():
                form.save()
                messages.success(request,'Has cambiado el status de facturas completas')
                return redirect(redirect_url)
            else:
                messages.error(request,'No está validando')
        elif "btn_descargar_todo" in request.POST:
            in_memory_zip, zip_filename = generar_archivo_zip(facturas, compra)
            response = HttpResponse(in_memory_zip, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response
        elif 'salir' in request.POST:
            return redirect(redirect_url)

    context={
        'pagos':pagos,
        'form':form,
        'facturas':facturas,
        'compra':compra,
        }

    return render(request, 'tesoreria/matriz_factura_no_modal.html', context)

@perfil_seleccionado_required
def matriz_complementos(request, pk):
    print('estoy en matriz_complementos')
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)

    try:
        if perfil.tipo.nombre == "PROVEEDOR_EXTERNO":
            next_url = 'matriz-oc-proveedores'
            print(next_url)
            factura = get_object_or_404(Facturas, id=pk, oc__proveedor__nombre = perfil.proveedor)
        else:
            factura = get_object_or_404(Facturas, id=pk)
            next_url = request.GET.get('next','matriz-compras')
    except Http404:
        messages.error(request, "No tienes acceso a esta orden de compra.")
        return redirect(next_url)
    complementos = Complemento_Pago.objects.filter(facturas=factura, hecho=True)
    #pagos = Factura.objects.filter(oc = compra)
    #form = Facturas_Completas_Form(instance=compra)
    

    if request.method == 'POST':
        #form = Facturas_Completas_Form(request.POST, instance=compra)
        #if "btn_factura_completa" in request.POST:
        #    fecha_hora = datetime.today()
        #    for factura in facturas:
        #        checkbox_name = f'autorizar_factura_{factura.id}'
                #print("Nombre del checkbox esperado:", checkbox_name)  # Imprimir el nombre esperado
        #        if checkbox_name in request.POST:
        #            factura.autorizada = True
        #            factura.autorizada_por = perfil
        #            factura.autorizada_el = fecha_hora
        #        else:
        #            factura.autorizada = False
        #        factura.save()
        #    if form.is_valid():
        #        form.save()
        #        messages.success(request,'Haz cambiado el status de facturas completas')
        #        return redirect(next_url)
        #    else:
        #        messages.error(request,'No está validando')
        #elif "btn_descargar_todo" in request.POST:
        #    in_memory_zip, zip_filename = generar_archivo_zip(facturas, compra)
        #    response = HttpResponse(in_memory_zip, content_type='application/zip')
        #    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        #    return response
        print(request.POST)
        if 'salir' in request.POST:
            return redirect(next_url)

    context={
        #'pagos':pagos,
        #'form':form,
        'factura':factura,
        'complementos':complementos,
        }

    return render(request, 'tesoreria/matriz_complementos.html', context)



def guardar_factura(factura, archivo_procesado, nombre_archivo,  uuid_extraido, fecha_timbrado_extraida, usuario, comentario):
    factura.factura_xml.save(nombre_archivo, archivo_procesado)
    factura.uuid = uuid_extraido
    factura.fecha_timbrado = fecha_timbrado_extraida
    factura.hecho = True
    factura.fecha_subido = date.today()
    factura.hora_subido = datetime.now().time()
    factura.subido_por = usuario
    factura.comentario = comentario
    factura.save()

@perfil_seleccionado_required
def factura_nueva(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)

    form = UploadFileForm()

    if request.method == 'POST':
        if 'btn_registrar' in request.POST:
            form = UploadFileForm(request.POST, request.FILES or None)
            if form.is_valid():
                archivos_pdf = request.FILES.getlist('archivo_pdf')
                archivos_xml = request.FILES.getlist('archivo_xml')
                if not archivos_pdf and not archivos_xml:
                    messages.error(request, 'Debes subir al menos un archivo PDF o XML.')
                    return HttpResponse(status=204)
                
                # Iterar sobre el número máximo de archivos en cualquiera de las listas
                max_len = max(len(archivos_pdf), len(archivos_xml))
                facturas_registradas = []
                facturas_duplicadas = []
                facturas_mes_invalido = []  # Lista para facturas fuera del mes
                comentario = request.POST.get('comentario', '')  # Extraer el comentario
                
                fecha_actual = datetime.today()
                mes_actual = fecha_actual.month
                año_actual = fecha_actual.year
                print(fecha_actual)

                for i in range(max_len):
                    archivo_pdf = archivos_pdf[i] if i < len(archivos_pdf) else None
                    archivo_xml = archivos_xml[i] if i < len(archivos_xml) else None
                    factura, created = Facturas.objects.get_or_create(oc=compra, hecho=False)
                    if archivo_xml:
                        archivo_procesado = eliminar_caracteres_invalidos(archivo_xml)

                        # Guardar temporalmente para extraer datos
                        #factura_temp = Factura(archivo_xml=archivo_xml)
                        #factura_temp.archivo_xml.save(archivo_xml.name, archivo_procesado, save=False)

                        uuid_extraido, fecha_timbrado_extraida = extraer_datos_del_xml(archivo_procesado)
                        if fecha_timbrado_extraida:
                            try:
                                # Si la fecha incluye la hora, parsearla correctamente
                                fecha_timbrado_dt = datetime.strptime(fecha_timbrado_extraida, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                print(f"⚠️ Error: Formato de fecha desconocido -> {fecha_timbrado_extraida}")
                                fecha_timbrado_dt = None
                        else:
                            print("⚠️ Advertencia: No se extrajo ninguna fecha de timbrado")
                            fecha_timbrado_dt = None
                        mes_factura = fecha_timbrado_dt.month  # Obtener el mes de la factura
                        año_factura = fecha_timbrado_dt.year  # Obtener el año de la factura

                        # Validar que el mes y el año de la factura sea el mismo que el actual
                        # Se quita por el momento la restricción del mes
                        #if mes_factura != mes_actual or año_factura != año_actual:
                        #    facturas_mes_invalido.append(uuid_extraido)
                        #    continue  # Saltar la factura si no cumple la condición
                        # Verificar si ya existe una factura con el mismo UUID y fecha de timbrado en cualquiera de las tablas
                        factura_existente = Factura.objects.filter(uuid=uuid_extraido, fecha_timbrado=fecha_timbrado_extraida).first()
                        facturas_existentes = Facturas.objects.filter(uuid=uuid_extraido, fecha_timbrado=fecha_timbrado_extraida).first()
                        viaticos_factura_existente = Viaticos_Factura.objects.filter(uuid=uuid_extraido, fecha_timbrado=fecha_timbrado_extraida).first()

                        if factura_existente or facturas_existentes or viaticos_factura_existente:
                            # Si una factura existente se encuentra, verificamos si su solicitud no está aprobada
                            if factura_existente and (factura_existente.solicitud_gasto.autorizar is False or factura_existente.solicitud_gasto.autorizar2 is False):
                                factura_existente.delete()
                                guardar_factura(factura, archivo_procesado, archivo_xml.name, uuid_extraido, fecha_timbrado_extraida, usuario, comentario)

                            elif facturas_existentes and (facturas_existentes.oc.autorizado1 is False or facturas_existentes.oc.autorizado2 is False):
                                facturas_existentes.delete()
                                guardar_factura(factura, archivo_procesado, archivo_xml.name, uuid_extraido, fecha_timbrado_extraida, usuario, comentario)

                            elif viaticos_factura_existente and (viaticos_factura_existente.solicitud_viatico.autorizar is False or viaticos_factura_existente.solicitud_viatico.autorizar2 is False):
                                viaticos_factura_existente.delete()
                                guardar_factura(factura, archivo_procesado, archivo_xml.name, uuid_extraido, fecha_timbrado_extraida, usuario, comentario)

                            else:
                                # Si no cumple las condiciones de eliminación, consideramos la factura duplicada
                                facturas_duplicadas.append(uuid_extraido)
                                continue  # Saltar al siguiente archivo si se encuentra duplicado
                        else:
                            # Si no existe ninguna factura, guardar la nueva
                            guardar_factura(factura, archivo_procesado, archivo_xml.name, uuid_extraido, fecha_timbrado_extraida, usuario, comentario)
                            #messages.success(request, 'Las facturas se registraron de manera exitosa')
                    if archivo_pdf:
                        factura.factura_pdf = archivo_pdf
                        factura.hecho = True
                        factura.fecha_subido = date.today()
                        factura.hora_subido = datetime.now().time()
                        factura.subido_por = usuario
                        factura.comentario = comentario
                        factura.save()
                      
                        facturas_registradas.append(uuid_extraido if archivo_xml else f"Factura PDF {archivo_pdf.name}")
                    #messages.success(request, 'Los facturas se registraron de manera exitosa')
                     # Mensajes de éxito o duplicados
                #return HttpResponse(status=204)
                # Mensajes de éxito o advertencias
                if facturas_duplicadas:
                    messages.warning(request, f'Las siguientes no se pudieron subir porque ya estaban registradas: {", ".join(facturas_duplicadas)}')
                if facturas_mes_invalido:
                    messages.error(request, f'Las siguientes facturas no se pudieron registrar porque no corresponden al mes y año actual: {", ".join(facturas_mes_invalido)}')
                #return HttpResponse(status=204)

            else:
                messages.error(request,'No se pudo subir tu documento')

    context={
        'form':form,
        'compra':compra,
        }

    return render(request, 'tesoreria/registrar_nueva_factura.html', context)


@perfil_seleccionado_required
def complemento_nuevo(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    #factura = Facturas.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)

    form = UploadComplementoForm()

    if request.method == 'POST' and 'btn_registrar' in request.POST:
        form = UploadComplementoForm(request.POST, request.FILES or None)
        if form.is_valid():
            archivos_pdf = request.FILES.getlist('complemento_pdf')
            archivos_xml = request.FILES.getlist('complemento_xml')
           
            if not archivos_pdf and not archivos_xml:
                messages.error(request, 'Debes subir al menos un archivo PDF o XML.')
                return HttpResponse(status=204)

            # Listas de seguimiento
            complementos_invalidos = []
            complementos_duplicados = []
            complementos_registrados = []
            pdf_sin_complemento = []
            comentario = request.POST.get('comentario', '')
            print(comentario)
            
            # Determinar el número máximo de archivos a procesar
            max_len = max(len(archivos_pdf), len(archivos_xml))

            for i in range(max_len):
                archivo_pdf = archivos_pdf[i] if i < len(archivos_pdf) else None
                archivo_xml = archivos_xml[i] if i < len(archivos_xml) else None
                complemento_final = None  # Variable para almacenar el complemento en el que se trabajará

                # Procesar XML si está presente
                if archivo_xml:
                    try:
                        archivo_procesado = eliminar_caracteres_invalidos(archivo_xml)

                        # Guardar el archivo XML en un archivo temporal para procesarlo
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp:
                            for chunk in archivo_procesado.chunks():
                                tmp.write(chunk)
                            tmp_path = tmp.name

                        try:
                            # Extraer datos desde el archivo temporal
                            uuid_complemento, _ = extraer_datos_del_complemento(tmp_path)
                        finally:
                            # Asegurar que el archivo temporal se borre aunque falle
                            os.remove(tmp_path)


                        # Validaciones de UUID y relación con factura
                        if not uuid_complemento:
                            complementos_invalidos.append(archivo_xml.name)
                            continue

                        complemento_existente = Complemento_Pago.objects.filter(uuid=uuid_complemento).first()
                        if complemento_existente:
                            complementos_duplicados.append(uuid_complemento)
                            complemento_final = complemento_existente  # Reusar complemento existente
                        else:
                            # Crear nuevo complemento sin facturas aún
                            complemento_final = Complemento_Pago.objects.create(
                                complemento_xml=archivo_xml,
                                uuid=uuid_complemento,
                                subido_por=usuario,
                                fecha_subido=date.today(),
                                hora_subido=datetime.now().time(),
                                comentario=comentario,
                                hecho=True
                            )
                            # Llamar la property que extrae los UUIDs de facturas
                            info_xml = complemento_final.emisor
                            if info_xml and 'doctos_relacionados_uuids' in info_xml:
                                uuids_facturas = info_xml['doctos_relacionados_uuids']
                                facturas_relacionadas = Facturas.objects.filter(uuid__in=uuids_facturas)

                                if facturas_relacionadas.exists():
                                    complemento_final.facturas.set(facturas_relacionadas)
                                    complementos_registrados.append(uuid_complemento)
                                else:
                                    complemento_final.delete()  # limpia si no hay facturas válidas
                                    complementos_invalidos.append(f"No se encontraron facturas relacionadas con UUIDs: {', '.join(uuids_facturas)}")
                                    continue
                            else:
                                complemento_final.delete()
                                complementos_invalidos.append(f"{archivo_xml.name} no contiene facturas relacionadas.")
                                continue


                          

                    except Exception as e:
                        messages.error(request, f"Error al procesar {archivo_xml.name}: {e}")
                        continue

                # Procesar PDF y asociarlo con el mismo complemento
                if archivo_pdf:
                    if complemento_final:
                        complemento_final.complemento_pdf = archivo_pdf  # ✅ ADHERIR PDF AL COMPLEMENTO EXISTENTE
                        complemento_final.save()
                        complementos_registrados.append(f"PDF: {archivo_pdf.name}")
                    else:
                        pdf_sin_complemento.append(archivo_pdf.name)  # 📌 Registrar PDFs sin complemento

            # Generar mensajes para el usuario
            if complementos_registrados:
                messages.success(request, f'Se han registrado los siguientes complementos: {", ".join(complementos_registrados)}')
            if complementos_duplicados:
                messages.warning(request, f'Los siguientes complementos ya estaban registrados y no se duplicaron: {", ".join(complementos_duplicados)}')
            if complementos_invalidos:
                messages.error(request, f'Los siguientes archivos no tienen factura relacionada o están mal estructurados: {", ".join(complementos_invalidos)}')
            if pdf_sin_complemento:
                messages.error(request, f'Los siguientes archivos PDF no tienen un complemento de pago asociado y no se guardaron: {", ".join(pdf_sin_complemento)}')

        else:
            messages.error(request, 'No se pudo subir tu documento.')

    context={
        'form':form,
        }

    return render(request, 'tesoreria/registrar_nuevo_complemento.html', context)

@perfil_seleccionado_required
def factura_compra_edicion(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    factura = Facturas.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)
    #factura, created = Facturas.objects.get_or_create(pago=pago, hecho=False)
    form = Facturas_Form(instance= factura)

    if request.method == 'POST':
        if 'btn_edicion' in request.POST:
            form = Facturas_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit = False)
                factura.subido_por = usuario
                factura.save()
                form.save()
                messages.success(request,'Las facturas se subieron de manera exitosa')
            else:
                messages.error(request,'No se pudo subir tu documento')


    context={
        'factura':factura,
        'form':form,
        }

    return render(request, 'tesoreria/factura_compra_edicion.html', context)

@perfil_seleccionado_required
def factura_eliminar(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    factura = Facturas.objects.get(id = pk)
    compra = factura.oc
    comentario = request.POST.get('comentario')
    # Obtener el parámetro `next` de la URL
    next_url = request.GET.get('next', None)

    # Construir la URL de la matriz de facturas de viáticos
    matriz_url = reverse('matriz-facturas-nomodal', args=[compra.id])

    static_path = settings.STATIC_ROOT
    img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
    img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
    image_base64 = get_image_base64(img_path)
    logo_v_base64 = get_image_base64(img_path2)
    # Crear el mensaje HTML
    html_message = f"""
    <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
            <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                            <tr>
                                <td align="center">
                                    <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px;">
                                    <p style="font-size: 18px; text-align: justify;">
                                        <p>Estimado {factura.subido_por.staff.staff.first_name} {factura.subido_por.staff.staff.last_name},</p>
                                    </p>
                                    <p style="font-size: 16px; text-align: justify;">
                                        Estás recibiendo este correo porque tu factura subida el: <strong>{factura.fecha_subido}</strong> en la compra <strong>{factura.oc.folio}</strong> ha sido eliminada.</p>
                                    <p>Comentario:</p>
                                    {comentario}
                                    </p>
                                <p style="font-size: 16px; text-align: justify;">
                                    Att: {perfil.staff.staff.first_name} {perfil.staff.staff.last_name}
                                </p>
                                    <p style="text-align: center; margin: 20px 0;">
                                        <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                    </p>
                                    <p style="font-size: 14px; color: #999; text-align: justify;">
                                        Este mensaje ha sido automáticamente generado por SAVIA 2.0
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    try:
        email = EmailMessage(
            f'Factura eliminada',
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[compra.creada_por.staff.staff.email],
            headers={'Content-Type': 'text/html'}
            )
        email.content_subtype = "html " # Importante para que se interprete como HTML
        if factura.factura_pdf:
            pdf_path = factura.factura_pdf.path
            if os.path.exists(pdf_path):  # Verificar si el archivo realmente existe
                with open(pdf_path, 'rb') as pdf_file:
                    email.attach(factura.factura_pdf.name, pdf_file.read(), 'application/pdf')
            else:
                print(f"El archivo PDF no se encuentra en la ruta: {pdf_path}")

        if factura.factura_xml:
            xml_path = factura.factura_xml.path
            if os.path.exists(xml_path):  # Verificar si el archivo realmente existe
                with open(xml_path, 'rb') as xml_file:
                    email.attach(factura.factura_xml.name, xml_file.read(), 'application/xml')
            else:
                print(f"El archivo XML no se encuentra en la ruta: {xml_path}")

        email.send()
        messages.success(request, f'La factura {factura.id} ha sido eliminada exitosamente')
    except (BadHeaderError, SMTPException, socket.gaierror) as e:
        error_message = f'La factura {factura.id} ha sido eliminada, pero el correo no ha sido enviado debido a un error: {e}'
        messages.success(request, error_message)
    factura.delete()

    # Redirigir a 'matriz-facturas-viaticos' con el parámetro `next` si existe
    if next_url:
        return redirect(f'{matriz_url}?next={next_url}')
    else:
        return redirect(matriz_url)
    

@perfil_seleccionado_required
def complemento_eliminar(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    complemento = Complemento_Pago.objects.get(id = pk)
    factura = complemento.facturas.first()
    comentario = request.POST.get('comentario')
    # Obtener el parámetro `next` de la URL
    next_url = request.GET.get('next', None)

    # Construir la URL de la matriz de facturas de viáticos
    matriz_url = reverse('matriz-complementos', args=[factura.id])

    static_path = settings.STATIC_ROOT
    img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
    img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
    image_base64 = get_image_base64(img_path)
    logo_v_base64 = get_image_base64(img_path2)
    # Crear el mensaje HTML
    html_message = f"""
    <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
            <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                            <tr>
                                <td align="center">
                                    <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px;">
                                    <p style="font-size: 18px; text-align: justify;">
                                        <p>Estimado {complemento.subido_por.staff.staff.first_name} {complemento.subido_por.staff.staff.last_name},</p>
                                    </p>
                                    <p style="font-size: 16px; text-align: justify;">
                                        Estás recibiendo este correo porque tu complemento subido el: <strong>{complemento.fecha_subido}</strong> en la compra <strong>{factura.oc.folio}</strong> ha sido eliminado.</p>
                                    <p>Comentario:</p>
                                    {comentario}
                                    </p>
                                <p style="font-size: 16px; text-align: justify;">
                                    Att: {perfil.staff.staff.first_name} {perfil.staff.staff.last_name}
                                </p>
                                    <p style="text-align: center; margin: 20px 0;">
                                        <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                    </p>
                                    <p style="font-size: 14px; color: #999; text-align: justify;">
                                        Este mensaje ha sido automáticamente generado por SAVIA 2.0
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    try:
        email = EmailMessage(
            f'Complemento eliminado',
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[factura.oc.creada_por.staff.staff.email],
            headers={'Content-Type': 'text/html'}
            )
        email.content_subtype = "html " # Importante para que se interprete como HTML
        if complemento.complemento_pdf:
            pdf_path = complemento.complemento_pdf.path
            if os.path.exists(pdf_path):  # Verificar si el archivo realmente existe
                with open(pdf_path, 'rb') as pdf_file:
                    email.attach(complemento.complemento_pdf.name, pdf_file.read(), 'application/pdf')
            else:
                print(f"El archivo PDF no se encuentra en la ruta: {pdf_path}")

        if complemento.complemento_xml:
            xml_path = complemento.complemento_xml.path
            if os.path.exists(xml_path):  # Verificar si el archivo realmente existe
                with open(xml_path, 'rb') as xml_file:
                    email.attach(complemento.complemento_xml.name, xml_file.read(), 'application/xml')
            else:
                print(f"El archivo XML no se encuentra en la ruta: {xml_path}")

        email.send()
        messages.success(request, f'El complemento de pago {complemento.id} ha sido eliminado exitosamente')
    except (BadHeaderError, SMTPException, socket.gaierror) as e:
        error_message = f'El complemento {complemento.id} ha sido eliminado, pero el correo no ha sido enviado debido a un error: {e}'
        messages.success(request, error_message)
    complemento.delete()

    # Redirigir a 'matriz-facturas-viaticos' con el parámetro `next` si existe
    if next_url:
        return redirect(f'{matriz_url}?next={next_url}')
    else:
        return redirect(matriz_url)

@perfil_seleccionado_required
def mis_gastos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    gastos = Solicitud_Gasto.objects.filter(
        Q(staff = usuario) |Q(colaborador = usuario), 
        complete=True
        ).order_by('-folio')
    myfilter = Solicitud_Gasto_Filter(request.GET, queryset=gastos)
    gastos = myfilter.qs



    for gasto in gastos:
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=gasto)

        proyectos = set()
        subproyectos = set()

        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        gasto.proyectos = ', '.join(proyectos)
        gasto.subproyectos = ', '.join(subproyectos)

    p = Paginator(gastos, 20)
    page = request.GET.get('page')
    gastos_list = p.get_page(page)

    if request.method =='POST' and 'btnExcel' in request.POST:
        return convert_excel_gasto(gastos)

    context= {
        'gastos':gastos,
        'myfilter':myfilter,
        'gastos_list': gastos_list,
        }

    return render(request, 'tesoreria/mis_gastos.html',context)

@perfil_seleccionado_required
def mis_viaticos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    viaticos = Solicitud_Viatico.objects.filter(Q(staff = usuario) |Q(colaborador = usuario), complete=True).order_by('-folio')
    myfilter = Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    context= {
        'viaticos':viaticos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_viaticos.html',context)

@perfil_seleccionado_required
def mis_comprobaciones_gasto(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    año_actual = datetime.now().year
    año_anterior = año_actual - 1
    inicio = datetime(año_anterior, 1, 1)
    fin = datetime(año_actual, 12, 31, 23, 59, 59)

    print(año_actual)
    print(año_anterior)
    gastos = Solicitud_Gasto.objects.filter(
        Q(staff=usuario) | Q(colaborador=usuario),
        autorizar2=True,
        created_at__range=(inicio, fin),
        complete=True
    ).annotate(
        facturas_hechas=Count('facturas', filter=Q(facturas__hecho=True))
    ).order_by('-folio')
    
    #).annotate(total_facturas=Count('facturas', filter=Q(facturas__hecho=True)),autorizadas=Count(Case(When(Q(facturas__hecho=True), then=Value(1))))
    #            ).order_by('-folio')
    print('gastos:',gastos)
    #myfilter = Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    #viaticos = myfilter.qs

    #p = Paginator(pagos, 25)
    #page = request.GET.get('page')
    #pagos_list = p.get_page(page)
    
    suma = decimal.Decimal(0)
    total_monto_gastos = decimal.Decimal(0)
    total_todas_facturas = decimal.Decimal(0)
    for gasto in gastos:
        suma = decimal.Decimal('0')
        total_monto_gastos += gasto.get_total_solicitud
        for factura in gasto.facturas.all():
            if factura.archivo_xml and factura.hecho: 
                try:
                    if factura.emisor is not None:
                        suma += decimal.Decimal(factura.emisor['total'])
                except FileNotFoundError:
                    # Ignorar o registrar si el archivo XML no existe
                    pass
        gasto.suma_total_facturas = suma
        total_todas_facturas += gasto.suma_total_facturas

    # Agrega la suma del gasto actual al total general
    #total_todas_facturas += gasto.suma_total_facturas
    #total_monto_gastos += gasto.get_total_solicitud

    if request.method =='POST':
        if 'btnExcel' in request.POST:
            return convert_comprobacion_gastos_to_xls2(gastos, año_actual,total_todas_facturas,total_monto_gastos)
            
        if 'btnImprimir' in request.POST or 'btnCorreo' in request.POST:
            # Obtener los IDs de los gastos seleccionados
            ids = request.POST.getlist('gastos')
            print(ids)
            tabla_gastos = """
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-size: 14px; width: 100%;">
                <thead style="background-color: #eaeaea;">
                    <tr>
                        <th>Folio</th>
                        <th>Monto Solicitado</th>
                        <th>Monto Comprobado</th>
                        <th>Diferencia</th>
                    </tr>
                </thead>
                <tbody>
            """
            gastos_enviar = Solicitud_Gasto.objects.filter(id__in=ids).prefetch_related('facturas', 'articulos')
            merger = PdfMerger()
            folios_gastos_enviados = []
           
            for gasto in gastos_enviar:
                # 1. Generar la carátula en memoria
                buffer = render_pdf_gasto(gasto.id)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_caratula:
                    temp_caratula.write(buffer.read())
                    caratula_path = temp_caratula.name
                merger.append(caratula_path)
                folios_gastos_enviados.append(str(gasto.folio))
                # 2. Comprobantes de pago (justo después de la carátula)
                for pago in gasto.pagosg.filter(hecho=True):
                    #print('esta entrando pago',pago)
                    if pago.comprobante_pago and os.path.exists(pago.comprobante_pago.path):
                        try:
                            merger.append(pago.comprobante_pago.path, import_outline=False)
                        except Exception as e:
                            print(f"Error al agregar comprobante de pago para gasto {gasto.folio}: {e}")

                suma = 0
                for factura in gasto.facturas.all():
                    
                    if factura.archivo_pdf and factura.hecho: 
                        path = factura.archivo_pdf.path
                        if os.path.exists(path):  # ✅ Validación que te faltó
                            merger.append(path)
                        else:
                            print(f"Archivo no encontrado: {path}")
                    elif factura.archivo_xml and factura.hecho:
                        try:
                            buffer = crear_pdf_cfdi_buffer(factura)  # <-- aquí llamas a tu función que genera el PDF desde XML
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                                temp_pdf.write(buffer.read())
                                temp_pdf.flush()
                                merger.append(temp_pdf.name, import_outline=False)
                        except Exception as e:
                            print(f"Error al generar PDF desde XML para factura {factura.id}: {str(e)}") 

                    if factura.archivo_xml and factura.hecho: 
                        try:
                            if factura.emisor is not None:
                                suma += decimal.Decimal(factura.emisor['total'])
                        except FileNotFoundError:
                            # Ignorar o registrar si el archivo XML no existe
                            pass
                        gasto.suma_total_facturas = suma    
                    
                    
                
                comprobado = gasto.suma_total_facturas
                monto = gasto.get_total_solicitud  # o gasto.monto si lo prefieres
                diferencia = comprobado - monto
                tabla_gastos += f"""
                    <tr>
                        <td>{gasto.folio}</td>
                        <td>${monto:,.2f}</td>
                        <td>${comprobado:,.2f}</td>
                        <td style="color: {'green' if diferencia > 0 else 'red' if diferencia < 0 else 'black'};">
                            ${diferencia:,.2f}
                        </td>
                    </tr>
                """


                 # ⚠️ Salimos del bucle antes de escribir o cerrar
            if not merger.pages:
                return HttpResponse("No hay facturas válidas para imprimir.", content_type="text/plain")

           
           
            if 'btnImprimir' in request.POST:
                tipo = 'gasto'
                acuse_buffer = generar_acuse_recibo(usuario, gastos_enviar, tipo)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_acuse:
                    temp_acuse.write(acuse_buffer.read())
                    acuse_path = temp_acuse.name
                merger.append(acuse_path)
            
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                merger.write(temp_file.name)
                temp_file_path = temp_file.name

           
            merger.close()
            print('temp_file_path:', temp_file_path)
            if 'btnImprimir' in request.POST:
                #return FileResponse(open(temp_file_path, 'rb'), content_type='application/pdf')
                # Guarda la ruta del archivo temporal en la sesión
                request.session['temp_pdf_path'] = temp_file_path
                return redirect('mostrar-pdf')
            if 'btnCorreo' in request.POST:
                # 2. Leer el contenido del archivo temporal
                with open(temp_file_path, 'rb') as f:
                    contenido_pdf = f.read()
                nombre_archivo = f"Comprobacion_gastos_{'_'.join(folios_gastos_enviados)}.pdf"
                static_path = settings.STATIC_ROOT
                img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
                img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
                image_base64 = get_image_base64(img_path)
                logo_v_base64 = get_image_base64(img_path2)
                html_message = f"""
                <html>
                    <head>
                        <meta charset="UTF-8">
                    </head>
                    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                        <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td align="center">
                                                <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="font-size: 18px; text-align: justify;">
                                                    A quien corresponda,
                                                </p>
                                                <p style="font-size: 18px; text-align: justify;">
                                                    Adjunto la comprobación de gastos de los siguientes folios: {', '.join(folios_gastos_enviados)},
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                            {tabla_gastos}
                                            </td>
                                        </tr>
                                    </table>
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td>
                                                <p style="font-size: 18px; text-align: justify;">
                                                Atte.
                                                </p>
                                                <p style="font-size: 18px; text-align: justify;">
                                                {request.user.get_full_name()}
                                                </p>
                                                <p style="text-align: center; margin: 20px 0;">
                                                    <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                                </p>
                                                <p style="font-size: 14px; color: #999; text-align: justify;">
                                                    Este mensaje ha sido generado por SAVIA 2.0
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                </html>
                """
                # Lista base con el remitente y alguien más si quieres
                correos = [request.user.email]
                #otros_correos = []
                # Si se marcó el checkbox de RH
                if request.POST.get('enviarRH'):
                    personal_rh = Profile.objects.filter(tipo__rh=True, distritos=usuario.distritos, st_activo = True, tipo__documentos = True)
                    for persona in personal_rh:
                        if persona.staff.staff.email:
                            correos.append(persona.staff.staff.email)

                # Si se marcó el checkbox de contabilidad y tesorería
                if request.POST.get('enviarContabilidad'):
                    personal_ct = Profile.objects.filter(tipo__tesoreria=True, tipo__rh = False, distritos=usuario.distritos, st_activo = True, tipo__documentos = True)
                    for persona in personal_ct:
                        if persona.staff.staff.email:
                            correos.append(persona.staff.staff.email)

                # Elimina duplicados
                correos = list(set(correos))
                print('correos:',correos)
                email = EmailMessage(
                subject=f"Comprobación de Gastos - {request.user.get_full_name()} - G{', '.join(folios_gastos_enviados)}",
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to = correos,   
                headers={'Content-Type': 'text/html'}
            )
            email.attach(nombre_archivo, contenido_pdf, 'application/pdf')
            # Adjuntar los XMLs de las facturas
            for gasto in gastos_enviar:
                for factura in gasto.facturas.all():
                    if factura.archivo_xml and factura.hecho:
                        try:
                            path = factura.archivo_xml.path
                            if os.path.exists(path):
                                nombre_xml = f"G{gasto.folio}_F{factura.uuid}.xml"
                                with open(path, 'rb') as f:
                                    email.attach(nombre_xml, f.read(), 'application/xml')
                            else:
                                print(f"XML no encontrado: {path}")
                        except Exception as e:
                            print(f"Error al adjuntar XML: {e}")
            email.content_subtype = "html"
            email.send()

            messages.success(request, "El correo fue enviado exitosamente.")
            return redirect('mis-comprobaciones-gasto')
        
    
    context= {
        'gastos':gastos,
        'total_todas_facturas':total_todas_facturas,
        'total_monto_gastos':total_monto_gastos,
        'año_actual':str(año_actual),
        'año_anterior':str(año_anterior),
        #'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_comprobaciones_gasto.html',context)

@perfil_seleccionado_required
def mis_comprobaciones_viaticos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    año_actual = datetime.now().year
    año_anterior = año_actual - 1
    inicio = datetime(año_anterior, 1, 1)
    fin = datetime(año_actual, 12, 31, 23, 59, 59)



    viaticos = Solicitud_Viatico.objects.filter(
        Q(staff=usuario) | Q(colaborador=usuario),
        autorizar2=True,
        created_at__range=(inicio, fin),
        complete=True
    ).annotate(
        total_facturas=Count('facturas', filter=Q(facturas__hecho=True))                    
    ).order_by('-folio')
    print(viaticos)
    suma = decimal.Decimal(0)
    total_monto_viaticos = decimal.Decimal(0)
    total_todas_facturas = decimal.Decimal(0)
    for viatico in viaticos:
        suma = decimal.Decimal('0')
        total_monto_viaticos += viatico.get_total
        for factura in viatico.facturas.all():
            if factura.factura_xml and factura.hecho: 
                try:
                    if factura.emisor is not None:
                        suma += decimal.Decimal(factura.emisor['total'])
                except FileNotFoundError:
                    # Ignorar o registrar si el archivo XML no existe
                    pass
        viatico.suma_total_facturas = suma
        total_todas_facturas += viatico.suma_total_facturas

    
    if request.method =='POST':
        if 'btnExcel' in request.POST:
            return convert_comprobacion_viaticos_to_xls2(viaticos, año_actual,total_todas_facturas,total_monto_viaticos)
        if 'btnImprimir' in request.POST or 'btnCorreo' in request.POST:
            # Obtener los IDs de los gastos seleccionados
            ids = request.POST.getlist('gastos')
            print(ids)
            tabla_viaticos = """
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-size: 14px; width: 100%;">
                <thead style="background-color: #eaeaea;">
                    <tr>
                        <th>Folio</th>
                        <th>Monto Solicitado</th>
                        <th>Monto Comprobado</th>
                        <th>Diferencia</th>
                    </tr>
                </thead>
                <tbody>
            """
            viaticos_enviar = Solicitud_Viatico.objects.filter(id__in=ids).prefetch_related('facturas', 'conceptos')
            merger = PdfMerger()
            folios_viaticos_enviados = []
           
            for viatico in viaticos_enviar:
                # 1. Generar la carátula en memoria
                buffer =generar_pdf_viatico(viatico.id) # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_caratula:
                    temp_caratula.write(buffer.read())
                    caratula_path = temp_caratula.name
                merger.append(caratula_path)
                folios_viaticos_enviados.append(str(viatico.folio))
                # 2. Comprobantes de pago (justo después de la carátula)
                for pago in viatico.pagosv.filter(hecho=True):
                    #print('esta entrando pago',pago)
                    if pago.comprobante_pago and os.path.exists(pago.comprobante_pago.path):
                        try:
                            merger.append(pago.comprobante_pago.path, import_outline=False)
                        except Exception as e:
                            print(f"Error al agregar comprobante de pago para gasto {viatico.folio}: {e}")

                suma = 0
                for factura in viatico.facturas.all():
                    
                    if factura.factura_pdf and factura.hecho: 
                        path = factura.factura_pdf.path
                        if os.path.exists(path):  # ✅ Validación que te faltó
                            merger.append(path)
                        else:
                            print(f"Archivo no encontrado: {path}")
                    elif factura.factura_xml and factura.hecho:
                        try:
                            buffer = crear_pdf_cfdi_buffer(factura)  # <-- aquí llamas a tu función que genera el PDF desde XML
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                                temp_pdf.write(buffer.read())
                                temp_pdf.flush()
                                merger.append(temp_pdf.name, import_outline=False)
                        except Exception as e:
                            print(f"Error al generar PDF desde XML para factura {factura.id}: {str(e)}") 

                    if factura.factura_xml and factura.hecho: 
                        try:
                            if factura.emisor is not None:
                                suma += decimal.Decimal(factura.emisor['total'])
                        except FileNotFoundError:
                            # Ignorar o registrar si el archivo XML no existe
                            pass
                        viatico.suma_total_facturas = suma    
                    
                    
                
                comprobado = viatico.suma_total_facturas
                monto = viatico.get_total  # o gasto.monto si lo prefieres
                diferencia = comprobado - monto
                tabla_viaticos += f"""
                    <tr>
                        <td>{viatico.folio}</td>
                        <td>${monto:,.2f}</td>
                        <td>${comprobado:,.2f}</td>
                        <td style="color: {'green' if diferencia > 0 else 'red' if diferencia < 0 else 'black'};">
                            ${diferencia:,.2f}
                        </td>
                    </tr>
                """


                 # ⚠️ Salimos del bucle antes de escribir o cerrar
            if not merger.pages:
                return HttpResponse("No hay facturas válidas para imprimir.", content_type="text/plain")

           
           
            if 'btnImprimir' in request.POST:
                tipo = 'viatico'
                acuse_buffer = generar_acuse_recibo(usuario, viaticos_enviar, tipo)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_acuse:
                    temp_acuse.write(acuse_buffer.read())
                    acuse_path = temp_acuse.name
                merger.append(acuse_path)
            
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                merger.write(temp_file.name)
                temp_file_path = temp_file.name

           
            merger.close()
            print('temp_file_path:', temp_file_path)
            if 'btnImprimir' in request.POST:
                #return FileResponse(open(temp_file_path, 'rb'), content_type='application/pdf')
                # Guarda la ruta del archivo temporal en la sesión
                request.session['temp_pdf_path'] = temp_file_path
                return redirect('mostrar-pdf')
            if 'btnCorreo' in request.POST:
                # 2. Leer el contenido del archivo temporal
                with open(temp_file_path, 'rb') as f:
                    contenido_pdf = f.read()
                nombre_archivo = f"Comprobacion_viaticos_{'_'.join(folios_viaticos_enviados)}.pdf"
                static_path = settings.STATIC_ROOT
                img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
                img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
                image_base64 = get_image_base64(img_path)
                logo_v_base64 = get_image_base64(img_path2)
                html_message = f"""
                <html>
                    <head>
                        <meta charset="UTF-8">
                    </head>
                    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                        <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f4f4; padding: 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td align="center">
                                                <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 100px; height: auto;" />
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="font-size: 18px; text-align: justify;">
                                                    A quien corresponda,
                                                </p>
                                                <p style="font-size: 18px; text-align: justify;">
                                                    Adjunto la comprobación de viáticos de los siguientes folios: {', '.join(folios_viaticos_enviados)},
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 20px;">
                                            {tabla_viaticos}
                                            </td>
                                        </tr>
                                    </table>
                                    <table width="600px" cellspacing="0" cellpadding="0" style="background-color: #ffffff; padding: 20px; border-radius: 10px;">
                                        <tr>
                                            <td>
                                                <p style="font-size: 18px; text-align: justify;">
                                                Atte.
                                                </p>
                                                <p style="font-size: 18px; text-align: justify;">
                                                {request.user.get_full_name()}
                                                </p>
                                                <p style="text-align: center; margin: 20px 0;">
                                                    <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                                </p>
                                                <p style="font-size: 14px; color: #999; text-align: justify;">
                                                    Este mensaje ha sido generado por SAVIA 2.0
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                </html>
                """
                # Lista base con el remitente y alguien más si quieres
                correos = [request.user.email]
                #otros_correos = []
                # Si se marcó el checkbox de RH
                if request.POST.get('enviarRH'):
                    personal_rh = Profile.objects.filter(tipo__rh=True, distritos=usuario.distritos, st_activo = True, tipo__documentos = True)
                    for persona in personal_rh:
                        if persona.staff.staff.email:
                            correos.append(persona.staff.staff.email)

                # Si se marcó el checkbox de contabilidad y tesorería
                if request.POST.get('enviarContabilidad'):
                    personal_ct = Profile.objects.filter(tipo__tesoreria=True, tipo__rh = False, distritos=usuario.distritos, st_activo = True, tipo__documentos = True)
                    for persona in personal_ct:
                        if persona.staff.staff.email:
                            correos.append(persona.staff.staff.email)

                # Elimina duplicados
                correos = list(set(correos))
                print('correos:',correos)
                email = EmailMessage(
                subject=f"Comprobación de Viáticos - {request.user.get_full_name()} - G{', '.join(folios_viaticos_enviados)}",
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to = correos,   
                headers={'Content-Type': 'text/html'}
            )
            email.attach(nombre_archivo, contenido_pdf, 'application/pdf')
            # Adjuntar los XMLs de las facturas
            for viatico in viaticos_enviar:
                for factura in viatico.facturas.all():
                    if factura.factura_xml and factura.hecho:
                        try:
                            path = factura.factura_xml.path
                            if os.path.exists(path):
                                nombre_xml = f"V{viatico.folio}_F{factura.uuid}.xml"
                                with open(path, 'rb') as f:
                                    email.attach(nombre_xml, f.read(), 'application/xml')
                            else:
                                print(f"XML no encontrado: {path}")
                        except Exception as e:
                            print(f"Error al adjuntar XML: {e}")
            email.content_subtype = "html"
            email.send()

            messages.success(request, "El correo fue enviado exitosamente.")
            return redirect('mis-comprobaciones-gasto')
    

    context= {
        'viaticos':viaticos,
        'total_todas_facturas':total_todas_facturas,
        'total_monto_viaticos':total_monto_viaticos,
        'año_actual':str(año_actual),
        'año_anterior':str(año_anterior),
        #'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_comprobaciones_viaticos.html',context)

#@perfil_seleccionado_required
def mostrar_pdf(request):
    pdf_path = request.session.get('temp_pdf_path')

    if not pdf_path or not os.path.exists(pdf_path):
        return HttpResponse("Archivo PDF no encontrado.", status=404)

    return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')


def convert_comprobacion_gastos_to_xls2(entradas, año_actual, total_todas_facturas, total_monto_gastos):
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Mis_gastos_" + str(año_actual))

     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})

    #columns = ['Folio Solicitud', 'Solicitante', 'Almacenista','Proyecto', 'Subproyecto', 'Fecha creación','Productos','Tipo','Autorizada','Fecha autorización','Comentario']
    columns = ['Folio Gasto','Comentario', 'Solicitante', 'Importe','Monto XML',]

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA 2.0 Vordcab. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Grupo Vordcab S.A. de C.V.', messages_style)
    worksheet.write(2, columna_max - 1, 'Monto total de facturas:', messages_style)
    worksheet.write(2, columna_max, total_todas_facturas, messages_style)
    worksheet.write(3, columna_max - 1, 'Monto total de importe: ', messages_style)
    worksheet.write(3, columna_max, total_monto_gastos, messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    row_num = 0
    for gasto in entradas:
        row_num += 1
        # Crear la lista de productos con nombre y cantidad
        #productos_lista = [
        #    f"{producto['producto__producto__nombre']} (Cantidad: {producto['cantidad']})"
        #    for producto in dev.solicitud.productos.values('producto__producto__nombre', 'cantidad')
        #]
        # Unir la lista en una cadena
        #productos_str = ", ".join(productos_lista)

        row = [
            gasto.folio,
            gasto.comentario,
            f"{gasto.staff.staff.staff.first_name} {gasto.staff.staff.staff.last_name}",
            gasto.get_total_solicitud,
            gasto.suma_total_facturas,
        ]
        
        for col_num, cell_value in enumerate(row):
        # Define el formato por defecto
            cell_format = body_style

            # Finalmente, escribe la celda con el valor y el formato correspondiente
            worksheet.write(row_num, col_num, cell_value, cell_format)

      
        #worksheet.write_formula(row_num, 19, f'=IF(ISBLANK(R{row_num+1}), L{row_num+1}, L{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Mis_gastos_{año_actual} {dt.date.today()}.xlsx'

      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response

def convert_comprobacion_viaticos_to_xls2(entradas, año_actual, total_todas_facturas, total_monto_viaticos):
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Mis_viaticos_" + str(año_actual))

     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})

    #columns = ['Folio Solicitud', 'Solicitante', 'Almacenista','Proyecto', 'Subproyecto', 'Fecha creación','Productos','Tipo','Autorizada','Fecha autorización','Comentario']
    columns = ['Folio Viatico','Motivo', 'Solicitante', 'Importe','Monto XML',]

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA 2.0 Vordcab. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Grupo Vordcab S.A. de C.V.', messages_style)
    worksheet.write(2, columna_max - 1, 'Monto total de facturas:', messages_style)
    worksheet.write(2, columna_max, total_todas_facturas, messages_style)
    worksheet.write(3, columna_max - 1, 'Monto total de importe: ', messages_style)
    worksheet.write(3, columna_max, total_monto_viaticos, messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    row_num = 0
    for viatico in entradas:
        row_num += 1
        # Crear la lista de productos con nombre y cantidad
        #productos_lista = [
        #    f"{producto['producto__producto__nombre']} (Cantidad: {producto['cantidad']})"
        #    for producto in dev.solicitud.productos.values('producto__producto__nombre', 'cantidad')
        #]
        # Unir la lista en una cadena
        #productos_str = ", ".join(productos_lista)

        row = [
            viatico.folio,
            viatico.motivo,
            f"{viatico.staff.staff.staff.first_name} {viatico.staff.staff.staff.last_name}",
            viatico.get_total,
            viatico.suma_total_facturas,
        ]
        
        for col_num, cell_value in enumerate(row):
        # Define el formato por defecto
            cell_format = body_style

            # Finalmente, escribe la celda con el valor y el formato correspondiente
            worksheet.write(row_num, col_num, cell_value, cell_format)

      
        #worksheet.write_formula(row_num, 19, f'=IF(ISBLANK(R{row_num+1}), L{row_num+1}, L{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Mis_viaticos_{año_actual} {dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response

def convert_excel_matriz_compras_autorizadas(compras):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Pendientes_de_pago_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Compras Autorizadas')
    #Comenzar en la fila 1
    row_num = 1

    #Create heading style and adding to workbook | Crear el estilo del encabezado y agregarlo al Workbook
    head_style = NamedStyle(name = "head_style")
    head_style.font = Font(name = 'Arial', color = '00FFFFFF', bold = True, size = 11)
    head_style.fill = PatternFill("solid", fgColor = '00003366')
    wb.add_named_style(head_style)
    #Create body style and adding to workbook
    body_style = NamedStyle(name = "body_style")
    body_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(body_style)
    #Create messages style and adding to workbook
    messages_style = NamedStyle(name = "mensajes_style")
    messages_style.font = Font(name="Arial Narrow", size = 11)
    wb.add_named_style(messages_style)
    #Create date style and adding to workbook
    date_style = NamedStyle(name='date_style', number_format='DD/MM/YYYY')
    date_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(date_style)
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Folio','Fecha Autorización','Proyecto','Subproyecto','Distrito','Proveedor','C. Pago',
               'Importe', 'Moneda','Tipo de cambio','Total en Pesos','Fecha Creación','Recibida']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5: #Columna del proveedor
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30
        if col_num == 2:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 20

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de OC's").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos Pendientes").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(K:K)").style = money_resumen_style
  
    
   
    
    for compra in compras:
        row_num = row_num + 1    
        #productos = ArticuloComprado.objects.filter(oc = compra)

        # Unir los nombres de los productos en una sola cadena separada por comas
        #productos_texto = ', '.join([producto.nombre for producto in productos])
        # Manejar autorizado_at_2
        if compra.autorizado_at_2 and isinstance(compra.autorizado_at_2, datetime):
        # Si autorizado_at_2 es timezone-aware, conviértelo a timezone-naive
            autorizado_at_2_naive = compra.autorizado_at_2.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            autorizado_at_2_naive = ''
        
        # Manejar created_at
        if compra.created_at and isinstance(compra.created_at, datetime):
        # Si created_at es timezone-aware, conviértelo a timezone-naive
            created_at_naive = compra.created_at.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            created_at_naive = ''

        recibida = "Recibida" if compra.entrada_completa else "No Recibida"

        row = [
            compra.folio,
            autorizado_at_2_naive,
            compra.req.orden.proyecto.nombre,
            compra.req.orden.subproyecto.nombre,
            compra.req.orden.distrito.nombre,
            compra.proveedor.nombre.razon_social,
            compra.cond_de_pago.nombre,
            compra.costo_plus_adicionales,
            compra.moneda.nombre,
            compra.tipo_de_cambio if compra.tipo_de_cambio else '',
            f'=IF(J{row_num}="",H{row_num},H{row_num}*J{row_num})',  # Calcula total en pesos usando la fórmula de Excel
            created_at_naive,
            recibida,
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 1 or col_num == 11:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 7 or col_num == 9 or col_num == 10:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    return(response)

def convert_excel_matriz_compras_tesoreria(compras):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Pendientes_de_pago_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Compras Autorizadas')
    #Comenzar en la fila 1
    row_num = 1

    #Create heading style and adding to workbook | Crear el estilo del encabezado y agregarlo al Workbook
    head_style = NamedStyle(name = "head_style")
    head_style.font = Font(name = 'Arial', color = '00FFFFFF', bold = True, size = 11)
    head_style.fill = PatternFill("solid", fgColor = '00003366')
    wb.add_named_style(head_style)
    #Create body style and adding to workbook
    body_style = NamedStyle(name = "body_style")
    body_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(body_style)
    #Create messages style and adding to workbook
    messages_style = NamedStyle(name = "mensajes_style")
    messages_style.font = Font(name="Arial Narrow", size = 11)
    wb.add_named_style(messages_style)
    #Create date style and adding to workbook
    date_style = NamedStyle(name='date_style', number_format='DD/MM/YYYY')
    date_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(date_style)
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Folio OC','Fecha Autorización OC','Folio UUID','Fecha_Timbrado','Proyecto','Subproyecto','Distrito','Proveedor','Producto','Banco', 'Cuenta Bancaria','Clabe','Moneda',
                'Tipo de cambio','Importe','Total en Pesos','Importe Pagado','Importe Restante','C. Pago', 'Días de Crédito','Fecha Creación','Recibida','Factura']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5: #Columna del proveedor
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30
        if col_num == 2:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 20

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de OC's").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos Pendientes").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(R:R)").style = money_resumen_style
  
    
   
    
    for compra in compras:
        row_num = row_num + 1    
        productos = ArticuloComprado.objects.filter(oc = compra)

        # Unir los nombres de los productos en una sola cadena separada por comas
        productos_texto = ', '.join([producto.producto.producto.articulos.producto.producto.nombre for producto in productos])
        # Manejar autorizado_at_2
        if compra.autorizado_at_2 and isinstance(compra.autorizado_at_2, datetime):
        # Si autorizado_at_2 es timezone-aware, conviértelo a timezone-naive
            autorizado_at_2_naive = compra.autorizado_at_2.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            autorizado_at_2_naive = ''
        
        # Manejar created_at
        if compra.created_at and isinstance(compra.created_at, datetime):
        # Si created_at es timezone-aware, conviértelo a timezone-naive
            created_at_naive = compra.created_at.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            created_at_naive = ''

        if compra.facturas.filter(factura_xml__isnull=False).exists():
            tiene_facturas = 'Sí'
            uuids = compra.facturas.filter(factura_xml__isnull=False, uuid__isnull=False).values_list('uuid', flat=True)
            uuid_string = "///".join(uuids)
            fechas_timbrado = compra.facturas.filter(factura_xml__isnull=False, fecha_timbrado__isnull=False).values_list('fecha_timbrado', flat=True)
            fecha_timbrado_string = ">>>".join([fecha.strftime("%d/%m/%Y") for fecha in fechas_timbrado])
        else:
            tiene_facturas = 'No'
            uuid_string = ''  # O None, según lo que necesites
            fecha_timbrado_string = ''

        recibida = "Recibida" if compra.entrada_completa else "No Recibida"

        row = [
            compra.folio,
            autorizado_at_2_naive,
            uuid_string,
            fecha_timbrado_string,
            compra.req.orden.proyecto.nombre,
            compra.req.orden.subproyecto.nombre,
            compra.req.orden.distrito.nombre,
            compra.proveedor.nombre.razon_social,
            productos_texto,
            compra.proveedor.banco.nombre,
            compra.proveedor.cuenta,
            compra.proveedor.clabe,
            compra.moneda.nombre,
            compra.tipo_de_cambio if compra.tipo_de_cambio else '',
            compra.costo_plus_adicionales,
            # Calcula total en pesos usando la fórmula de Excel
            f'=IF(N{row_num}="",O{row_num},O{row_num}*N{row_num})', 
            compra.monto_pagado,
            f'=P{row_num} - Q{row_num}',
            compra.cond_de_pago.nombre,
            compra.dias_de_credito if compra.dias_de_credito else '',
            created_at_naive,
            recibida,
            tiene_facturas,
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num in [1, 20]:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num in [13, 14,15, 16, 17]:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    return(response)

def convert_excel_matriz_pagos(pagos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Matriz_pagos_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Pagos')
    #Comenzar en la fila 1
    row_num = 1

    # Función para manejar los IDs de las compras, gastos o viáticos
    def get_transaction_id(pago):
        if pago.oc:
            return 'OC'+str(pago.oc.folio)
        elif pago.gasto:
            return 'G'+str(pago.gasto.folio)
        elif pago.viatico:
            return 'V'+str(pago.viatico.folio)
        else:
            return None

    #Create heading style and adding to workbook | Crear el estilo del encabezado y agregarlo al Workbook
    head_style = NamedStyle(name = "head_style")
    head_style.font = Font(name = 'Arial', color = '00FFFFFF', bold = True, size = 11)
    head_style.fill = PatternFill("solid", fgColor = '00003366')
    wb.add_named_style(head_style)
    #Create body style and adding to workbook
    body_style = NamedStyle(name = "body_style")
    body_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(body_style)
    #Create messages style and adding to workbook
    messages_style = NamedStyle(name = "mensajes_style")
    messages_style.font = Font(name="Arial Narrow", size = 11)
    wb.add_named_style(messages_style)
    #Create date style and adding to workbook
    date_style = NamedStyle(name='date_style', number_format='DD/MM/YYYY')
    date_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(date_style)
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Id','Compra/Gasto','Solicitado','Proyecto','Subproyecto','Proveedor/Colaborador','Facturas Completas','Tiene Facturas',
               'Importe','Fecha', 'Moneda','Tipo de cambio', 'Total en Pesos']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de Pagos").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(M:M)").style = money_resumen_style
  

   # Aquí debes extraer el conjunto completo de pagos en lugar de solo ciertos valores
    
    for pago in pagos:
        row_num = row_num + 1
        # Define los valores de las columnas basándote en el tipo de pago
        if pago.oc:
            proveedor = pago.oc.proveedor
            facturas_completas = pago.oc.facturas_completas
            cuenta_moneda = pago.cuenta.moneda.nombre if pago.cuenta else None
            #if pago.oc.facturas.exists():
                #print(pago.oc.facturas)
            #    tiene_facturas = 'Sí'
            #else:
            #    tiene_facturas = 'No'


            if pago.oc.facturas.filter(factura_xml__isnull=False).exists():
                tiene_facturas = 'Sí'
            else:
                tiene_facturas = 'No'

            if cuenta_moneda == 'PESOS':
                tipo_de_cambio = ''
            elif cuenta_moneda == 'DOLARES':
                 tipo_de_cambio = pago.tipo_de_cambio or pago.oc.tipo_de_cambio or 17
            else:
                tipo_de_cambio = ''  # default si no se cumplen las condiciones anteriores
        elif pago.gasto:
            if pago.gasto.colaborador:
                proveedor = pago.gasto.colaborador.staff.staff.first_name + ' ' + pago.gasto.colaborador.staff.staff.last_name
            else:
                proveedor = pago.gasto.staff.staff.staff.first_name + ' ' + pago.gasto.staff.staff.staff.last_name
            facturas_completas = pago.gasto.facturas_completas
            tipo_de_cambio = '' # Asume que no se requiere tipo de cambio para gastos
            if pago.gasto.facturas.exists():
                
                tiene_facturas = 'Sí'
            else:
                tiene_facturas = 'No'
            
        elif pago.viatico:
            if pago.viatico.colaborador:
                proveedor = pago.viatico.colaborador.staff.staff.first_name + ' ' + pago.viatico.colaborador.staff.staff.last_name
            else:
                proveedor = pago.viatico.staff.staff.staff.first_name + ' ' + pago.viatico.staff.staff.staff.last_name
            facturas_completas = pago.viatico.facturas_completas
            tipo_de_cambio = '' # Asume que no se requiere tipo de cambio para viáticos
            if pago.viatico.facturas.exists():
                tiene_facturas = 'Sí'
            else:
                tiene_facturas = 'No'
        else:
            proveedor = None
            facturas_completas = None
            tipo_de_cambio = ''

       

        row = [
            pago.id,
            get_transaction_id(pago),
            pago.oc.req.orden.staff.staff.staff.first_name + ' ' + pago.oc.req.orden.staff.staff.staff.last_name if pago.oc else '',
            pago.oc.req.orden.proyecto.nombre if pago.oc else '',
            pago.oc.req.orden.subproyecto.nombre if pago.oc else '',
            proveedor,
            facturas_completas,
            tiene_facturas,
            pago.monto,
            pago.pagado_date.strftime('%d/%m/%Y') if pago.pagado_date else '',
            pago.oc.moneda.nombre if pago.oc else '',  # Modificación aquí
            tipo_de_cambio,
            f'=IF(L{row_num}="",I{row_num},I{row_num}*L{row_num})'  # Calcula total en pesos usando la fórmula de Excel
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 9:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 8 or col_num == 11 or col_num == 12:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    wb.save(response)

    return(response)

def mass_payment_view(request):
    if request.method == 'POST':
        request.session['compras_ids'] = request.POST.getlist('compra_id')
        return redirect('layout_pagos')  # No pasamos 'ids' porque usaremos la sesión

# Si necesitas pasar las IDs como parte del contexto a un nuevo template puedes hacerlo así:
def layout_pagos(request):
    compras_ids = request.session.get('compras_ids', [])
    compras_ids = [int(id) for id in compras_ids if str(id).isdigit()]
    compras = Compra.objects.filter(id__in=compras_ids)
    cuentas_disponibles = Cuenta.objects.all()

    if request.method == 'POST':
        try:
            root = ET.Element('Document', {
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xmlns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'
            })

            cstmr_cdt_trf_initn = ET.SubElement(root, 'CstmrCdtTrfInitn')
            grp_hdr = ET.SubElement(cstmr_cdt_trf_initn, 'GrpHdr')
            now_local = datetime.now()
            ET.SubElement(grp_hdr, 'MsgId').text = 'AUTO' +  now_local.strftime('%Y%m%d%H%M%S')
            ET.SubElement(grp_hdr, 'CreDtTm').text = now_local.isoformat()
            ET.SubElement(grp_hdr, 'NbOfTxs').text = str(len(compras))

            initg_pty = ET.SubElement(grp_hdr, 'InitgPty')
            id_ = ET.SubElement(initg_pty, 'Id')
            org_id = ET.SubElement(id_, 'OrgId')
            othr = ET.SubElement(org_id, 'Othr')
            ET.SubElement(othr, 'Id').text = 'VORDCA00H2H'
            
            for count, compra in enumerate(compras, start=1):
                cuenta_pago_id = request.POST.get(f'cuenta_{count}')
                cuenta_pago = cuentas_disponibles.get(id=cuenta_pago_id)

                
            
                monto = float(request.POST.get(f'monto_{count}', '0'))
                

                pmt_inf = ET.SubElement(cstmr_cdt_trf_initn, 'PmtInf')
                ET.SubElement(pmt_inf, 'PmtInfId').text = f'Pmt-{compra.id}'
                ET.SubElement(pmt_inf, 'PmtMtd').text = 'TRF'

                pmt_tp_inf = ET.SubElement(pmt_inf, 'PmtTpInf')
                svc_lvl = ET.SubElement(pmt_tp_inf, 'SvcLvl')
                ET.SubElement(svc_lvl, 'Cd').text = 'URGP'

                ET.SubElement(pmt_inf, 'ReqdExctnDt').text = now_local.strftime('%Y-%m-%d')

                dbtr = ET.SubElement(pmt_inf, 'Dbtr')
                dbtr_id = ET.SubElement(dbtr, 'Id')
                dbtr_org_id = ET.SubElement(dbtr_id, 'OrgId')
                dbtr_othr = ET.SubElement(dbtr_org_id, 'Othr')
                ET.SubElement(dbtr_othr, 'Id').text = '123456789'

                dbtr_acct = ET.SubElement(pmt_inf, 'DbtrAcct')
                dbtr_acct_id = ET.SubElement(dbtr_acct, 'Id')
                dbtr_acct_othr = ET.SubElement(dbtr_acct_id, 'Othr')
                ET.SubElement(dbtr_acct_othr, 'Id').text = str(cuenta_pago.cuenta)
                
                #ET.SubElement(dbtr_acct, 'Ccy').text = compra.moneda.nombre

                dbtr_agt = ET.SubElement(pmt_inf, 'DbtrAgt')
                fin_instn_id = ET.SubElement(dbtr_agt, 'FinInstnId')
                ET.SubElement(fin_instn_id, 'BIC').text = 'BCMRMXMM'

                cdt_trf_tx_inf = ET.SubElement(pmt_inf, 'CdtTrfTxInf')

                pmt_id = ET.SubElement(cdt_trf_tx_inf, 'PmtId')
                instr_id = f'INST-{compra.id}'
                ET.SubElement(pmt_id, 'InstrId').text = instr_id
                ET.SubElement(pmt_id, 'EndToEndId').text = instr_id

                amt = ET.SubElement(cdt_trf_tx_inf, 'Amt')
                if compra.moneda.nombre == "PESOS":
                    moneda = "MXN"
                ET.SubElement(amt, 'InstdAmt', Ccy=moneda).text = f"{monto:.2f}"

                ET.SubElement(cdt_trf_tx_inf, 'ChrgBr').text = 'DEBT'

                cdtr_agt = ET.SubElement(cdt_trf_tx_inf, 'CdtrAgt')
                fin_instn_id_cdtr = ET.SubElement(cdtr_agt, 'FinInstnId')
                bic_banco_receptor = compra.proveedor.banco.bic if compra.proveedor.banco.bic else 'BICDESCONOCIDO'
                ET.SubElement(fin_instn_id_cdtr, 'BIC').text = bic_banco_receptor

                cdtr = ET.SubElement(cdt_trf_tx_inf, 'Cdtr')
                ET.SubElement(cdtr, 'Nm').text = compra.proveedor.nombre.razon_social

                PstlAdr = ET.SubElement(cdtr,'PstlAdr')
                ET.SubElement(PstlAdr, 'StrtNm').text = compra.proveedor.domicilio
                if compra.proveedor.estado:
                    ET.SubElement(PstlAdr, 'TwnNm').text = compra.proveedor.estado.nombre
                if compra.proveedor.nombre.extranjero == False:
                    ET.SubElement(PstlAdr, 'Ctry').text = 'MX'
                else:
                    ET.SubElement(PstlAdr, 'Ctry').text = 'EX'

                cdtr_id = ET.SubElement(cdtr, 'Id')
                cdtr_org_id = ET.SubElement(cdtr_id, 'OrgId')
                cdtr_othr = ET.SubElement(cdtr_org_id, 'Othr')
                ET.SubElement(cdtr_othr, 'Id').text = compra.proveedor.nombre.rfc


                cdtr_acct = ET.SubElement(cdt_trf_tx_inf, 'CdtrAcct')
                cdtr_acct_id = ET.SubElement(cdtr_acct, 'Id')
                cdtr_acct_othr = ET.SubElement(cdtr_acct_id, 'Othr')
                ET.SubElement(cdtr_acct_othr, 'Id').text = str(compra.proveedor.cuenta)

                rmt_inf = ET.SubElement(cdt_trf_tx_inf, 'RmtInf')
                ET.SubElement(rmt_inf, 'Ustrd').text = f"F-{compra.folio}"

            xml_bytes = ET.tostring(root, encoding='utf-8', method='xml')

            # Guardar XML en disco
            xml_path = '/home/savia/pagos_xml/pagos.xml'
            with open(xml_path, 'wb') as f:
                f.write(xml_bytes)
            logging.info(f'Archivo XML generado: {xml_path}')

            # Encriptar el archivo XML con GPG
            encrypted_path = '/home/savia/pagos_encrypted/pagos.xml.gpg'
            subprocess.run([
                '/usr/bin/gpg', '--yes', '--batch', '--trust-model', 'always',
                '--output', encrypted_path,
                '--encrypt', '--recipient', 'gruvor1i', xml_path
            ], check=True)
            logging.info(f'Archivo encriptado: {encrypted_path}')
            # 5. Enviar por SFTP

            host = os.getenv("BBVA_SFTP_HOST")
            port = int(os.getenv("BBVA_PORT"))
            username = os.getenv("BBVA_UP")
            password = os.getenv("BBVA_PP")
            remote_path = '/'

            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.chdir(remote_path)
            sftp.put(encrypted_path, 'pagos.xml.gpg')
            sftp.close()
            transport.close()
            logging.info(f'Archivo enviado a BBVA SFTP ({host}:{port}{remote_path})')

            messages.success(request, 'Archivo encriptado y enviado por SFTP a BBVA correctamente.')
            return redirect('compras-autorizadas')  # Cambiar por el nombre real de tu vista
        except Exception as e:
            logging.error(f'Error durante el proceso de envío: {str(e)}')
            messages.error(request, 'Ocurrió un error al enviar el archivo.')
            return redirect('compras-autorizadas')

    context = {
        'compras': compras,
        'cuentas_disponibles': cuentas_disponibles,
    }

    return render(request, 'tesoreria/layout_pagos.html', context)


def descargar_respuestas_bbva():
    host = os.getenv("BBVA_SFTP_HOST")
    port = int(os.getenv("BBVA_PORT"))
    username = os.getenv("BBVA_UG")   
    password = os.getenv("BBVA_PG")     
    remote_path = '/'                 
    local_path = '/home/savia/pagos_respuestas/'

    os.makedirs(local_path, exist_ok=True)

    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir(remote_path)

        archivos = sftp.listdir()
        logging.info(f'Se encontraron {len(archivos)} archivo(s) en {remote_path}.')

        logging.info("📂 Listado completo del directorio remoto:")
        for entry in sftp.listdir_attr(remote_path):
            tipo = '📁 Carpeta' if str(entry.longname).startswith('d') else '📄 Archivo'
            logging.info(f"{tipo}: {entry.filename}")

        for archivo in archivos:
            remote_file = f"{remote_path}{archivo}" if not remote_path.endswith('/') else f"{remote_path}{archivo}"
            local_file = os.path.join(local_path, archivo)

            sftp.get(remote_file, local_file)
            logging.info(f'Archivo encontrado en SFTP: {archivo}')
            logging.info(f'Archivo descargado: {archivo} → {local_file}')

            # Si es archivo .pgp, desencriptarlo
            if archivo.endswith('.pgp') or archivo.endswith('.gpg'):
                desencriptar_pgp(local_file)

        sftp.close()
        transport.close()
        logging.info('Conexión cerrada correctamente después de descargar archivos.')

    except Exception as e:
        logging.error(f'Error al descargar archivos desde BBVA: {str(e)}')

def es_respuesta_bbva(path_xml):
    try:
        tree = ET.parse(path_xml)
        root = tree.getroot()
        claves = ['respuesta', 'ack', 'estatus', 'resultado', 'codigo']
        return any(clave in root.tag.lower() for clave in claves)
    except Exception as e:
        logging.warning(f"No se pudo analizar {path_xml} como XML: {str(e)}")
        return False

def desencriptar_pgp(archivo_pgp):
    global desencriptados, errores
    archivo_xml = archivo_pgp.replace('.pgp', '.xml').replace('.gpg', '.xml')
    if os.path.exists(archivo_xml):
        logging.info(f"Archivo ya desencriptado: {archivo_xml}")
        return
    try:
        logging.info(f"Desencriptando {archivo_pgp}...")
        result = subprocess.run(
            ['gpg', '--batch', '--yes', '--output', archivo_xml, '--decrypt', archivo_pgp],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        logging.info(f"Desencriptado exitosamente: {archivo_xml}")
        desencriptados += 1
        if es_respuesta_bbva(archivo_xml):
            logging.info(f"✅ Archivo identificado como respuesta BBVA: {archivo_xml}")
        else:
            logging.info(f"ℹ️ Archivo desencriptado pero no parece respuesta BBVA: {archivo_xml}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error desencriptando {archivo_pgp}: {e.stderr.decode()}")
        errores += 1
    

def escanear_sftp_recursivo(sftp, remote_path, local_path):
    global descargados, errores
    os.makedirs(local_path, exist_ok=True)
    logging.info(f"📁 Visitando carpeta: {remote_path}")

    try:
        for item in sftp.listdir_attr(remote_path):
            remote_item_path = os.path.join(remote_path, item.filename)
            local_item_path = os.path.join(local_path, item.filename)

            if str(item.longname).startswith('d'):
                escanear_sftp_recursivo(sftp, remote_item_path, local_item_path)
            else:
                logging.info(f"📄 Archivo encontrado: {remote_item_path}")
                try:
                    sftp.get(remote_item_path, local_item_path)
                    logging.info(f"Archivo descargado: {remote_item_path} → {local_item_path}")
                    descargados += 1
                    if item.filename.endswith(('.pgp', '.gpg')):
                        desencriptar_pgp(local_item_path)
                except Exception as e:
                    logging.error(f"Error descargando {remote_item_path}: {str(e)}")
                    errores += 1
    except IOError as e:
        logging.warning(f"No se pudo acceder a {remote_path}: {str(e)}")
        errores += 1


def escanear_todo_bbva():
    global descargados, desencriptados, errores
    descargados = 0
    desencriptados = 0
    errores = 0

    host = os.getenv("BBVA_SFTP_HOST")
    port = int(os.getenv("BBVA_PORT"))
    username = os.getenv("BBVA_UG")   
    password = os.getenv("BBVA_PG")     
    remote_root = '/'                 
    local_root = '/home/savia/pagos_respuestas/'

    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        logging.info(f"🔍 Iniciando escaneo completo en SFTP desde: {remote_root}")

        escanear_sftp_recursivo(sftp, remote_root, local_root)

        sftp.close()
        transport.close()
        logging.info("✅ Escaneo completo finalizado correctamente.")
        logging.info(f"📦 Archivos descargados: {descargados}")
        logging.info(f"🔐 Archivos desencriptados: {desencriptados}")
        logging.info(f"❌ Errores durante el proceso: {errores}")

    except Exception as e:
        logging.error(f"❌ Error en escaneo de SFTP: {str(e)}")
        
def convert_excel_control_bancos(pagos):
    # Reordenar los pagos en orden ascendente por 'pagado_real'
    pagos = pagos.order_by('pagado_real')
    static_path = settings.STATIC_ROOT
    img_path2 = os.path.join(static_path, 'images', 'logo_vordcab.jpg')
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Matriz_Compras")
     # Ajustar la altura de las filas 1 y 2
   
     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '#16324F', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    d_cell_format = workbook.add_format({'num_format': 'dd/mm/yyyy','align': 'center', 'valign': 'vcenter', 'border': 1})
    title_format = workbook.add_format({'font_name': 'Calibri', 'font_size': 18, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    vordcab_format = workbook.add_format({'font_color': 'FFFFFF', 'bg_color': '#16324F','font_name': 'Calibri', 'font_size': 18, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    h_money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    # Ajustar el ancho de las columnas
    worksheet.set_column('A:A', 20)  # Fecha
    #worksheet.set_column('B:B', 20)  # Empresa
    worksheet.set_column('B:B', 35)  # Empresa/Proveedor
    worksheet.set_column('C:C', 25)  # Cuenta
    worksheet.set_column('D:D', 20)  # Concepto/Servicio
    worksheet.set_column('E:E', 25)  # Contrato
    worksheet.set_column('F:F', 25)  # Sector
    worksheet.set_column('G:G', 20)  # Distrito
    worksheet.set_column('H:H', 20)  # Monto
    worksheet.set_column('I:I', 20)  # Saldo
    worksheet.set_column('J:J', 20)  # Saldo


    worksheet.set_row(0, 40)  # Fila 1 (índice 0) con altura 40
    worksheet.set_row(1, 30)  # Fila 2 (índice 1) con altura 30

    # Insertar el logo en la hoja de trabajo
    worksheet.insert_image('A1', img_path2, {'x_scale': 1, 'y_scale': 1})

    # Agregar y fusionar celdas para el encabezado
    worksheet.write('I1', 'Preparado Por:', header_format)
    worksheet.write('I2', 'SUBD FIN', cell_format)
    worksheet.write('J1', 'Aprobación', header_format)
    worksheet.write('J2', 'DG', cell_format)

    worksheet.merge_range('C1:H2', 'CONTROL DE BANCOS', title_format)
    worksheet.merge_range('A3:B3', 'Número de documento', header_format)
    worksheet.merge_range('A4:B4', 'SEOV-TES-N4-01.03', cell_format)
    
    worksheet.merge_range('C3:D3', 'Clasificación del documento', header_format)
    worksheet.merge_range('C4:D4', 'Controlado', cell_format)
    worksheet.write('E3', 'Nivel del documento', header_format)
    worksheet.write('E4', 'N5', cell_format)
    
    worksheet.merge_range('F3:G3', 'Revisión No.', header_format)
    worksheet.merge_range('F4:G4', '000', cell_format)
    worksheet.write('H3', 'Fecha de emisión', header_format)
    worksheet.write('H4', '12/09/2022', d_cell_format)
    worksheet.merge_range('I3:J3', 'Fecha Revisión', header_format)
    worksheet.merge_range('I4:J4', '', cell_format)
    worksheet.write('H3', 'Fecha de emisión', header_format)
    
    worksheet.merge_range('A5:J8', 'GRUPO VORDCAB, S.A. DE C.V.', vordcab_format)
    cuenta =  pagos.first().cuenta if pagos.exists() else None
    worksheet.merge_range('A9:B9', 'INSTITUCIÓN BANCARIA: '+ str(cuenta.banco.nombre), header_format)
   
    
    worksheet.merge_range('A10:B10', 'CUENTA BANCARIA: '+ str(cuenta.cuenta), header_format)
    worksheet.merge_range('A11:B11', 'DISTRITO: ' + str(cuenta.encargado.distritos), header_format)
    worksheet.merge_range('A12:B12', 'RESPONSABLE DE CUENTA: ' + str(cuenta.encargado.staff.staff.first_name)+ ' '+ str(cuenta.encargado.staff.staff.last_name), header_format)

    worksheet.write('H9', 'PERIODO:', header_format)
    #worksheet.write('I9', 'MES', cell_format)
    #worksheet.write('J9', 'AÑO', cell_format)
   
    
    worksheet.write('I10', 'SALDO INICIAL' , header_format)
    #worksheet.write('J10', saldo_inicial, h_money_style)
    worksheet.write('I11', 'SALDO FINAL', header_format)
    
    worksheet.write('J12', '', header_format)
    

    columns = ['Fecha','Empresa/Colaborador','Cuenta','Concepto/Servicio','Proyecto','Subproyecto','Distrito','Cargo','Comentarios','Saldo']

    columna_max = len(columns)+2

    #worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA Vordcab. UH', messages_style)
    #worksheet.write(1, columna_max - 1, 'Software desarrollado por Grupo Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    
    for col_num, header in enumerate(columns):
        worksheet.write(12, col_num, header, head_style)

    folios_unicos = set()  # Mantener un conjunto de folios únicos

    row_num = 13
    for pago in pagos:

        fecha = pago.pagado_real
        empresa = pago.cuenta.empresa.nombre
        if hasattr(pago, 'oc') and pago.oc:
            proveedor = pago.oc.proveedor.nombre.razon_social
        elif hasattr(pago, 'gasto') and pago.gasto:
            if pago.gasto.colaborador:
                proveedor = f"{pago.gasto.colaborador.staff.staff.first_name} {pago.gasto.colaborador.staff.staff.last_name}"
            else:
                proveedor = f"{pago.gasto.staff.staff.staff.first_name} {pago.gasto.staff.staff.staff.last_name}"
        elif hasattr(pago, 'viatico') and pago.viatico:
            if pago.viatico.colaborador:
                proveedor = f"{pago.viatico.colaborador.staff.staff.first_name} {pago.viatico.colaborador.staff.staff.last_name}"
            else:
                proveedor = f"{pago.viatico.staff.staff.first_name} {pago.viatico.staff.staff.last_name}"
        else:
            proveedor = f"{pago.tesorero.staff.staff.first_name} {pago.tesorero.staff.staff.last_name}"

        cuenta = pago.cuenta.cuenta
        if hasattr(pago, 'detalles_comprobante') and pago.detalles_comprobante and hasattr(pago.detalles_comprobante, 'cuenta_retiro') and pago.detalles_comprobante.cuenta_retiro != "No disponible":
            concepto_servicio = pago.detalles_comprobante.motivo_pago
        elif hasattr(pago, 'oc') and pago.oc:
            concepto_servicio = f"OC{pago.oc.folio}"
        elif hasattr(pago, 'gasto') and pago.gasto:
            concepto_servicio = f"G{pago.gasto.folio}"
        elif hasattr(pago, 'viatico') and pago.viatico:
            concepto_servicio = f"V{pago.viatico.folio}"
        else:
            concepto_servicio = str(pago.tipo)
        if pago.comentario != None:
            concepto_servicio = str(concepto_servicio) + ' '+ str(pago.comentario)

        # Determinar contrato y sector
        if hasattr(pago, 'oc') and pago.oc:
            contrato = pago.oc.req.orden.proyecto.nombre
            sector = pago.oc.req.orden.subproyecto.nombre
            comentarios = pago.oc.req.orden.comentario
        elif hasattr(pago, 'viatico') and pago.viatico:
            contrato = pago.viatico.proyecto.nombre
            sector = pago.viatico.subproyecto.nombre
            comentarios = pago.viatico.comentario_general
        elif hasattr(pago, 'gasto') and pago.gasto:
            articulos_gasto = Articulo_Gasto.objects.filter(gasto=pago.gasto)
            comentarios = pago.gasto.comentario
            proyectos = set()
            subproyectos = set()
            for articulo in articulos_gasto:
                if articulo.proyecto:
                    proyectos.add(str(articulo.proyecto.nombre))
                if articulo.subproyecto:
                    subproyectos.add(str(articulo.subproyecto.nombre))
            contrato = ', '.join(proyectos)
            sector = ', '.join(subproyectos)
        else:
            contrato = ''
            sector = ''
        
        distrito = pago.oc.req.orden.distrito.nombre if hasattr(pago, 'oc') and pago.oc else (pago.gasto.distrito.nombre if hasattr(pago, 'gasto') and pago.gasto else (pago.viatico.subproyecto.nombre if hasattr(pago, 'viatico') and pago.viatico else ''))
        cargo = ''
        if pago.tipo == None or pago.tipo.nombre == "CARGO":
            cargo = pago.monto
        abono = pago.monto if pago.tipo and pago.tipo.nombre == "ABONO"  else ''
        #saldo = pago.saldo
        
   

        # Escribir los datos en el archivo Excel
        worksheet.write(row_num, 0, fecha.strftime('%d/%m/%Y') if fecha else '', date_style)
        worksheet.write(row_num, 1, empresa)
        worksheet.write(row_num, 1, proveedor)
        worksheet.write(row_num, 2, cuenta)
        worksheet.write(row_num, 3, concepto_servicio)
        worksheet.write(row_num, 4, contrato)
        worksheet.write(row_num, 5, sector)
        worksheet.write(row_num, 6, distrito)
        worksheet.write(row_num, 7, cargo, money_style)
        worksheet.write(row_num, 8, abono, money_style)
        worksheet.write(row_num, 8, comentarios)
        #if row_num == 13:
        #    worksheet.write(row_num, 9, saldo_acumulado, money_style)
        #else:
        #    if row_num > 13:
                # Restar la celda (row_num - 1, 10) - (row_num, 8)
        #        formula = f'=IF(H{row_num + 1}>0,  J{row_num} - H{row_num + 1}, J{row_num} + I{row_num + 1} )'
        #        worksheet.write_formula(row_num, 9, formula, money_style)

        last_filled_row = row_num
        row_num += 1

    last_filled_cell = f'A{last_filled_row+1}'
    worksheet.write_formula('J11', '=J14', h_money_style)
    worksheet.write_formula('I9', f'={last_filled_cell}', h_money_style)
    worksheet.write_formula('J9', '=A14', h_money_style)
     # Agregar el marco general desde A1 hasta J12
    border_format = workbook.add_format({
        'top': 1,
        'bottom': 1,
        'left': 1,
        'right': 1
    })
    

    # Aplicar el borde derecho
    #for row in range(12):
        #worksheet.write(row, 9, '', border_format)
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Control_Bancos_{dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response


def generar_cfdi(request, pk):
    factura = Facturas.objects.get(id=pk)
    data = factura.emisor
    # Verificar y asignar un valor predeterminado para impuestos si es None
    if data['impuestos'] is None:
        data['impuestos'] = 0.0

    # Verificar y asignar un valor predeterminado para total si es None
    if data['total'] is None:
        data['total'] = 0.0

    # Verificar y asignar un valor predeterminado para subtotal si es None
    if data['subtotal'] is None:
        data['subtotal'] = 0.0
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
    if data['iva_retenido'] > 0:
        c.setFillColor(white)
        c.drawRightString(alineado_x + 500, alineado_y, f"Impuestos retenidos:")
        c.setFillColor(black)
        c.drawRightString(alineado_x + 555, alineado_y, f"{float(data['iva_retenido']):,.2f}")
        alineado_y -= line_height
    if data['isr_retenido'] > 0:
        c.setFillColor(white)
        c.drawRightString(alineado_x + 500, alineado_y, f"ISR:")
        c.setFillColor(black)
        c.drawRightString(alineado_x + 555, alineado_y, f"{float(data['isr_retenido']):,.2f}")
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
    # Crear la respuesta HTTP con el PDF
    folio_fiscal = data['uuid']
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{folio_fiscal}.pdf"'

    return response

def generar_qr(data):
    # URL del acceso al servicio
    url = "https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx"
    
    # Construcción de la cadena de datos para el QR
    qr_data = f"{url}?id={data['uuid']}&re={data['rfc_emisor']}&rr={data['rfc_receptor']}&tt={float(data['total']):.6f}&fe={data['sello_cfd'][-8:]}"
    
    # Generar el código QR
    qr = qrcode.make(qr_data)
    
    # Guardar el QR como imagen temporal
    qr_img = io.BytesIO()
    qr.save(qr_img, format='PNG')
    qr_img.seek(0)
    
    return qr_img



def convert_excel_gasto(gastos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Gastos_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Gastos')
    #Comenzar en la fila 1
    row_num = 1

    #Create heading style and adding to workbook | Crear el estilo del encabezado y agregarlo al Workbook
    head_style = NamedStyle(name = "head_style")
    head_style.font = Font(name = 'Arial', color = '00FFFFFF', bold = True, size = 11)
    head_style.fill = PatternFill("solid", fgColor = '00003366')
    wb.add_named_style(head_style)
    #Create body style and adding to workbook
    body_style = NamedStyle(name = "body_style")
    body_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(body_style)
    #Create messages style and adding to workbook
    messages_style = NamedStyle(name = "mensajes_style")
    messages_style.font = Font(name="Arial Narrow", size = 11)
    wb.add_named_style(messages_style)
    #Create date style and adding to workbook
    date_style = NamedStyle(name='date_style', number_format='DD/MM/YYYY')
    date_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(date_style)
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Folio','Fecha Autorización','Distrito','Proyectos','Subproyectos','Colaborador','Solicitado para',
               'Importe','Fecha Creación','Status','Autorizado por','Facturas','Status Pago']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5: #Columna del proveedor
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30
        if col_num == 2:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 20

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de Gastos").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos Pendientes").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(F:F)").style = money_resumen_style
  

   
    
    for gasto in gastos:
        row_num = row_num + 1    
        
        # Manejar autorizado_at_2
        if gasto.approbado_fecha2 and isinstance(gasto.approbado_fecha2, datetime):
        # Si autorizado_at_2 es timezone-aware, conviértelo a timezone-naive
            autorizado_at_2_naive = gasto.approbado_fecha2.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            autorizado_at_2_naive = ''
        
        # Manejar created_at
        if gasto.created_at and isinstance(gasto.created_at, datetime):
        # Si created_at es timezone-aware, conviértelo a timezone-naive
           created_at_naive = gasto.created_at.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            created_at_naive = ''

        if gasto.pagada:
            pagada = "Con Pago"
        else:
            pagada = "Sin Pago"

        if gasto.facturas.exists():
            facturas = "Con Facturas"
        else:
            facturas = "Sin Facturas"
        
        if gasto.autorizar2:
            status = "Autorizado"
            
            if gasto.distrito.nombre == "MATRIZ":
                autorizado_por = str(gasto.superintendente.staff.staff.first_name) + ' ' + str(gasto.superintendente.staff.staff.last_name)
            elif gasto.autorizado_por2:
                autorizado_por = str(gasto.autorizado_por2.staff.staff.first_name) + ' ' + str(gasto.autorizado_por2.staff.staff.last_name)
            else:
                autorizado_por = "NR"
        elif gasto.autorizar2 == False:
            status = "Cancelado"
            if gasto.distrito.nombre == "MATRIZ":
                autorizado_por = str(gasto.superintendente.staff.staff.first_name) + ' ' + str(gasto.superintendente.staff.staff.last_name)
            elif gasto.autorizado_por2:
                autorizado_por = str(gasto.autorizado_por2.staff.staff.first_name) + ' ' + str(gasto.autorizado_por2.staff.staff.last_name)
            else:
                autorizado_por = "NR"
        elif gasto.autorizar:
            autorizado_por =str(gasto.superintendente.staff.staff.first_name) + ' ' + str(gasto.superintendente.staff.staff.last_name)
            status = "Autorizado | Falta una autorización"
            if gasto.facturas:
                facturas = gasto.facturas.exists()
            else:
                facturas = False
        elif gasto.autorizar == False:
            status = "Cancelado"
            autorizado_por = str(gasto.superintendente.staff.staff.last_name)
        else:
            autorizado_por = "Faltan autorizaciones"
            status = "Faltan autorizaciones"

        proyectos = set()
        subproyectos = set()
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=gasto)
        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        proyectos_str = ', '.join(proyectos)
        subproyectos_str = ', '.join(subproyectos)

        row = [
            gasto.folio,
            autorizado_at_2_naive,
            gasto.distrito.nombre,
            proyectos_str,
            subproyectos_str,
            gasto.staff.staff.staff.first_name + ' ' + gasto.staff.staff.staff.last_name,
            gasto.colaborador.staff.staff.first_name + ' '  + gasto.colaborador.staff.staff.last_name if gasto.colaborador else '',
            gasto.get_total_solicitud,
            created_at_naive,
            status,
            autorizado_por,
            facturas,
            pagada
            #f'=IF(I{row_num}="",G{row_num},I{row_num}*G{row_num})',  # Calcula total en pesos usando la fórmula de Excel
            #created_at_naive,
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num ==1 or col_num == 6:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)


def generar_acuse_recibo(usuario, gastos_enviar, tipo):
      #Configuration of the PDF object
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    custom_style = ParagraphStyle(
        name='CustomStyle',
        parent=normal_style,
        fontSize=10,
        alignment=1,  # Alineación centrada (0 = izquierda, 1 = centro, 2 = derecha)
    )
    #Azul Vordcab
    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    rojo = Color(0.59375, 0.05859375, 0.05859375)
    #Encabezado
    c.setFillColor(black)
    c.setLineWidth(.2)
    c.setFont('Helvetica',8)
    caja_iso = 760
    #Elaborar caja
    #c.line(caja_iso,500,caja_iso,720)



    #Encabezado
    c.drawString(420,caja_iso,'Preparado por:')
    c.drawString(420,caja_iso-10,'S2')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(520,caja_iso-10,'---')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'--------')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'--------')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, '--------')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'04/2024')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Solicitud
    c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    c.rect(20,615,565,2, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    if tipo == 'gasto':
        c.drawCentredString(280,755,'Acuse de Recibo Gastos')
    if tipo == 'viatico':
        c.drawCentredString(280,755,'Acuse de Recibo Viáticos')
    c.setLineWidth(.3) #Grosor
    c.line(20,caja_proveedor-8,20,615) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(584,caja_proveedor-8,584,615) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    #c.drawString(120,caja_proveedor,'Infor')
    c.drawString(300,caja_proveedor, 'Detalles')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(30,caja_proveedor-20,'Presentó:')
    c.drawString(30,caja_proveedor-40,'Distrito:')
    c.drawString(30,caja_proveedor-60,'Fecha:')
    # Segunda columna del encabezado
    #c.drawString(30,caja_proveedor-80,'Empresa')


    folios_str = ', '.join(str(g.folio) for g in gastos_enviar)
    fecha_hoy = datetime.today().strftime("%d/%m/%Y")
    c.setFont('Helvetica-Bold',12)
    c.drawString(300,caja_proveedor-20,'FOLIOS:')
    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(350,caja_proveedor-20, folios_str)

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(100,caja_proveedor-20, usuario.staff.staff.first_name+' '+ usuario.staff.staff.last_name)
    c.drawString(100,caja_proveedor-40, usuario.distritos.nombre)
    c.drawString(100,caja_proveedor-60, fecha_hoy)

    # --- Tabla de resumen de gastos ---
    tabla_gastos_data = [['Folio', 'Monto Solicitado', 'Monto Comprobado', 'Diferencia']]
    for gasto in gastos_enviar:
        if tipo == 'gasto':
            monto = gasto.get_total_solicitud
            comprobado = gasto.suma_total_facturas if hasattr(gasto, 'suma_total_facturas') else Decimal('0.00')
        if tipo == 'viatico':
            monto = gasto.get_total
            comprobado = gasto.suma_total_facturas if hasattr(gasto, 'suma_total_facturas') else Decimal('0.00')
        diferencia = comprobado - monto
        color = colors.black
        if diferencia > 0:
            color = colors.green
        elif diferencia < 0:
            color = colors.red

        tabla_gastos_data.append([
            str(gasto.folio),
            f"${monto:,.2f}",
            f"${comprobado:,.2f}",
            Paragraph(f"${diferencia:,.2f}", ParagraphStyle('diff', textColor=color, alignment=TA_RIGHT))
        ])

    # Crear la tabla
    tabla = Table(tabla_gastos_data, colWidths=[3*cm, 4*cm, 4*cm, 5*cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Posición de la tabla
    tabla.wrapOn(c, 500, 200)
    tabla.drawOn(c, 80, 500)  # Ajusta esta posición si necesitas moverla más arriba/abajo


    c.setFont("Helvetica", 10)
    c.drawString(100, 280, "Nombre y firma de quien recibe:")
    c.line(100, 245, 500, 245)

    c.drawString(100, 230, "Fecha de recepción:")
    c.line(100, 205, 300, 205)

    c.drawString(100, 190, "Comentarios u observaciones:")
    c.rect(100, 100, 400, 80)  # cuadro para observaciones (de 300 a 380)

    # Línea final del documento (opcional)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(300, 80, "Este acuse de recibo corresponde a la comprobación de gastos generada por SAVIA 2.0.")
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer