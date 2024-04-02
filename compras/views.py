from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, FileResponse
from django.views.decorators.cache import cache_page
from django.db.models import F, Avg, Value, ExpressionWrapper, fields, Sum, Q
from django.db.models.functions import Concat
from django.utils import timezone
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, BadHeaderError
from smtplib import SMTPException
from django.core.paginator import Paginator
from django.conf import settings
from .tasks import convert_excel_matriz_compras_task, convert_excel_solicitud_matriz_productos_task
from dashboard.models import Inventario, Order, ArticulosOrdenados, ArticulosparaSurtir
from requisiciones.models import Requis, ArticulosRequisitados
from user.models import Profile
from tesoreria.models import Pago, Facturas
from user.decorators import perfil_seleccionado_required
from .filters import CompraFilter, ArticulosRequisitadosFilter,  ArticuloCompradoFilter, HistoricalArticuloCompradoFilter
from .models import ArticuloComprado, Compra, Proveedor_direcciones, Cond_pago, Uso_cfdi, Moneda, Comparativo, Item_Comparativo, Proveedor
from .forms import CompraForm, ArticuloCompradoForm, ArticulosRequisitadosForm, ComparativoForm, Item_ComparativoForm, Compra_ComentarioForm, UploadFileForm, Compra_ComentarioGerForm
from requisiciones.forms import Articulo_Cancelado_Form
from requisiciones.filters import RequisFilter
from tesoreria.forms import Facturas_Form
from requisiciones.views import get_image_base64
from django.utils.timezone import make_aware, is_aware
import pytz
from io import BytesIO
import socket

import json
import time
import os
import io
import ssl
import decimal
from io import BytesIO
from datetime import date, datetime, timedelta
from num2words import num2words

#PDF generator
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter
from reportlab.rl_config import defaultPageSize

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from bs4 import BeautifulSoup

import urllib.request, urllib.parse, urllib.error

# Import Excel Stuff
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name


from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt
#from urllib.parse import (
#    ParseResult,
#    SplitResult,
#    _coerce_args,
#    _splitnetloc,
#    _splitparams,
#    scheme_chars,
#)
#from urllib.parse import urlencode as original_urlencode
#from urllib.parse import uses_params

# Create your views here.

@login_required(login_url='user-login')
def requisiciones_autorizadas(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)
    if perfil.tipo.compras == True:
        requis = Requis.objects.filter(orden__distrito = perfil.distritos, autorizar=True, colocada=False, complete = True).order_by('-approved_at')
    else:
        requis = Requis.objects.filter(autorizar=True, colocada=False, complete =True)
    #requis = Requis.objects.filter(autorizar=True, colocada=False)

    myfilter = RequisFilter(request.GET, queryset=requis)
    requis = myfilter.qs

    tag = dof()

     #Set up pagination
    p = Paginator(requis, 50)
    page = request.GET.get('page')
    requis_list = p.get_page(page)

    context= {
        'myfilter': myfilter,
        'requis':requis,
        'tags':tag,
        'requis_list':requis_list,
        }

    return render(request, 'compras/requisiciones_autorizadas.html',context)

@login_required(login_url='user-login')
def productos_pendientes(request):
    perfil = Profile.objects.get(staff__id=request.user.id)
    if perfil.tipo.compras == True:
        requis = Requis.objects.filter(autorizar=True, colocada=False)
    else:
        requis = Requis.objects.filter(complete=None)

    articulos = ArticulosRequisitados.objects.filter(req__autorizar = True, req__colocada=False, cancelado = False)
    myfilter = ArticulosRequisitadosFilter(request.GET, queryset=articulos)
    articulos = myfilter.qs

    #Set up pagination
    p = Paginator(articulos, 50)
    page = request.GET.get('page')
    articulos_list = p.get_page(page)

    context= {
        'requis':requis,
        'articulos':articulos,
        'articulos_list':articulos_list,
        'myfilter':myfilter,
        }

    return render(request, 'compras/productos_pendientes.html',context)


@perfil_seleccionado_required
def eliminar_articulos(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador = Profile.objects.all()
    perfil = colaborador.get(id = pk_perfil)
    #perfil = Profile.objects.get(staff__id=request.user.id)
    productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"), cancelado=False)
    requis = Requis.objects.get(id = pk)

    form = Articulo_Cancelado_Form()

    if request.method == 'POST' and "btn_eliminar" in request.POST:
        pk = request.POST.get('id')
        producto = ArticulosRequisitados.objects.get(id=pk)
        form = Articulo_Cancelado_Form(request.POST,instance=producto)
        if form.is_valid():
            articulo = form.save()
            productos = ArticulosRequisitados.objects.filter(req = producto.req)
            productos_cancelados = productos.filter(cancelado = True).count()
            productos_requisitados = productos.count() - productos_cancelados
            productos_comprados = productos.filter(art_surtido = True).count()
            if productos_requisitados == productos_comprados:
                requis.colocada = True
                requis.save()
            email = EmailMessage(
                f'Producto Eliminado {producto.producto.articulos.producto.producto.nombre}',
                f'Estimado(a) {producto.req.orden.staff.staff.staff.first_name}:\n\nEstás recibiendo este correo porque el producto: {producto.producto.articulos.producto.producto.nombre} de la solicitud: {producto.req.orden.folio} ha sido eliminado, por la siguiente razón: {producto.comentario_cancelacion} \n\n Atte.{perfil.staff.staff.first_name}{perfil.staff.staff.last_name}  \nGRUPO VORDCAB S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDCAB',
                settings.DEFAULT_FROM_EMAIL,
                ['ulises_huesc@hotmail.com',producto.req.orden.staff.staff.staff.email],
                )
            email.send()
            messages.success(request,f' Has eliminado el {producto.producto.articulos.producto} correctamente')
            return redirect('requisicion-autorizada')




    context = {
        'form':form,
        'productos': productos,
        'requis': requis,
        }

    return render(request,'compras/eliminar_articulos.html', context)

def articulos_restantes(request, pk):
    productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"), cancelado=False)
    #productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"))
    requis = Requis.objects.get(id = pk)

    context = {
        'productos': productos,
        'requis': requis,
        }

    return render(request,'compras/articulos_restantes.html', context)

def dof():
#Trying to fetch DOF
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        url = 'https://www.dof.gob.mx/#gsc.tab=0'
        html = urllib.request.urlopen(url, context=ctx).read()
        soup = BeautifulSoup(html,'html.parser')
        #tags = soup.find_all('p')

        tags = []
        for tag in soup.find_all('p'):
        #for anchor in tag.find_all('span'):
            tags.append(tag.contents)

        #substr = 'DOLAR'
        #if any(substr in str for str in tags):
        #   tag = tags[str][1]


        tag = tags[4][3]

        return tag
    except Exception as e:
        # Manejo de la excepción - log, mensaje de error, etc.
        return f"Error al obtener datos: {e}"

def oc(request, pk):
    productos = ArticulosRequisitados.objects.filter(req = pk)
    req = Requis.objects.get(id = pk)
    usuario = Profile.objects.get(id=request.user.id)
    oc, created = Compra.objects.get_or_create(complete = False, req = req, creada_por = usuario)
    form_product = ArticuloCompradoForm()
    form = CompraForm(instance=oc)


    context= {
        'req':req,
        'form':form,
        'oc':oc,
        'productos':productos,
        'form_product':form_product,
        }

    return render(request, 'compras/oc.html',context)

def compras_devueltas(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador = Profile.objects.all()
    usuario = colaborador.get(id = pk_perfil)
    #usuario = Profile.objects.get(staff__id=request.user.id)
    compras = Compra.objects.filter(regresar_oc = True, req__orden__distrito = usuario.distritos)
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

    #form_product = ArticuloCompradoForm()
    #form = CompraForm(instance=oc)



    context= {
        'myfilter':myfilter,
        'compras_list':compras,
        }

    return render(request, 'compras/compras_devueltas.html',context)

def compra_edicion(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador = Profile.objects.all()
    usuario = colaborador.get(id = pk_perfil)
    oc = Compra.objects.get(id =pk)
    colaborador_sel = Profile.objects.all()
    productos_comp = ArticuloComprado.objects.filter(oc = oc)
    productos = ArticulosRequisitados.objects.filter(req = oc.req, sel_comp = False)
    req = Requis.objects.get(id = oc.req.id)
    comparativos = Comparativo.objects.filter(creada_por__distritos = usuario.distritos, completo =True)
    #proveedores = Proveedor_direcciones.objects.filter(
    #    Q(estatus__nombre='NUEVO') | Q(estatus__nombre='APROBADO'))
    
    proveedores = Proveedor_direcciones.objects.filter(id = oc.proveedor.id)
    form_product = ArticuloCompradoForm()
    form = CompraForm(instance=oc)
    error_messages = {}
    #'distrito__nombre','domicilio','estatus__nombre'
    proveedor_para_select2 = [
        {'id': proveedor.id, 
         'text': proveedor.nombre.razon_social,
         #'distrito': proveedor.
        } for proveedor in proveedores]


    productos_para_select2 = [
        {'id': producto.id,
         'text': str(producto), 
         'cantidad': str(producto.cantidad), 
         'cantidad_pendiente': str(producto.cantidad_comprada),
         'precioref': str(producto.producto.articulos.producto.producto.precioref),
         'porcentaje': str(producto.producto.articulos.producto.producto.porcentaje)
        } for producto in productos]
    
    productos_comp_to_function = [
        {
            'id': producto.id,
            'precio': str(producto.precio_unitario),
            'precio_ref': str(producto.producto.producto.articulos.producto.producto.precioref),
            'porcentaje': str(producto.producto.producto.articulos.producto.producto.porcentaje)
        } for producto in productos_comp
    ] 

    comparativos_para_select2 = [
        {
            'id': comparativo.id, 
            'text': str(comparativo.nombre)
        } for comparativo in comparativos
    ]



    tag = dof()
    subtotal = 0
    iva = 0
    total = 0
    dif_cant = 0
    #form.fields['deposito_comprador'].queryset = colaborador_sel
    for item in productos_comp:
        subtotal = decimal.Decimal(subtotal + item.cantidad * item.precio_unitario)
        if item.producto.producto.articulos.producto.producto.iva == True:
            iva = round(subtotal * decimal.Decimal(0.16),2)
        total = decimal.Decimal(subtotal + decimal.Decimal(iva))

    if request.method == 'POST' and  "crear" in request.POST:
        form = CompraForm(request.POST, instance=oc)
        costo_oc = 0
        costo_iva = 0
        articulos = ArticuloComprado.objects.filter(oc=oc)
        requisitados = ArticulosRequisitados.objects.filter(req = oc.req)
        cuenta_art_comprados = requisitados.filter(art_surtido = True).count()
        cuenta_art_totales = requisitados.count()
        if cuenta_art_totales == cuenta_art_comprados and cuenta_art_comprados > 0:
            req.colocada = True
        else:
            req.colocada = False
        for articulo in articulos:
            costo_oc = costo_oc + articulo.precio_unitario * articulo.cantidad
            if articulo.producto.producto.articulos.producto.producto.iva == True:
                costo_iva = decimal.Decimal(costo_oc * decimal.Decimal(0.16))
        for producto in requisitados:
            dif_cant = dif_cant + producto.cantidad - producto.cantidad_comprada
            if producto.art_surtido == False:
                producto.sel_comp = False
                producto.save()
        oc.complete = True
        if oc.tipo_de_cambio != None and oc.tipo_de_cambio > 0:
            oc.costo_iva = decimal.Decimal(costo_iva)
            oc.costo_oc = decimal.Decimal(costo_oc + costo_iva)
        else:
            oc.costo_iva = decimal.Decimal(costo_iva)
            oc.costo_oc = decimal.Decimal(costo_oc + costo_iva)
        if form.is_valid():
            #abrev= usuario.distrito.abreviado
            #oc.folio = str(abrev) + str(consecutivo).zfill(4)
            oc.regresar_oc = False
            form.save()
            oc.save()
            req.save()
            messages.success(request,f'{usuario.staff.staff.first_name}, Has modificado la OC {oc.folio} correctamente')
            return redirect('compras-devueltas')
    else:
        for field, errors in form.errors.items():
            error_messages[field] = errors.as_text()



    context= {
        'comparativos_para_select2': comparativos_para_select2,
        'proveedor_para_select2': proveedor_para_select2,
        'productos_comp_to_function': productos_comp_to_function,
        'error_messages': error_messages,
        'req':req,
        'form':form,
        'form_product':form_product,
        'productos_para_select2':productos_para_select2,
        #'proveedores':proveedores,
        'productos':productos,
        'oc':oc,
        'productos_comp':productos_comp,
        'subtotal':subtotal,
        'iva':iva,
        'total':total,
        }

    return render(request, 'compras/compra_edicion.html',context)



def update_oc(request):
    data= json.loads(request.body)
    action = data["action"]
    cantidad = data["val_cantidad"]
    producto_id = data["id"]
    pk = data["oc"]
    productos = ArticulosRequisitados.objects.get(id=producto_id)
    precio = data["val_precio"]
    oc = Compra.objects.get(id=pk)
    if action == "add":
        cantidad_total = productos.cantidad_comprada + decimal.Decimal(cantidad)
        if cantidad_total > productos.cantidad:
            messages.error(request,f'La cantidad que se quiere comprar sobrepasa la cantidad requisitada {cantidad_total} mayor que {productos.cantidad}')
        else:
            comp_item, created = ArticuloComprado.objects.get_or_create(oc=oc, producto=productos)
            productos.cantidad_comprada = productos.cantidad_comprada + decimal.Decimal(cantidad)
            #messages.success(request,f'Estos son los productos comprados ahora {productos.cantidad_comprada}')
            if productos.cantidad_comprada == productos.cantidad:
                productos.art_surtido = True
            if comp_item.cantidad == None:
                comp_item.cantidad = 0
            comp_item.cantidad = comp_item.cantidad + decimal.Decimal(cantidad)
            comp_item.precio_unitario = precio
            productos.sel_comp = True
            comp_item.save()
            productos.save()
            response_data = {
             'codigo': comp_item.producto.producto.articulos.producto.producto.nombre,
             'producto': comp_item.producto.producto.articulos.producto.producto.codigo,
             'cantidad': comp_item.cantidad,
             'precio': comp_item.precio_unitario,
            }

    if action == "remove":
        comp_item = ArticuloComprado.objects.get(oc = oc, producto = productos)
        productos.art_surtido = False
        productos.sel_comp = False
        productos.cantidad_comprada = productos.cantidad_comprada - comp_item.cantidad
        productos.save()
        comp_item.delete()
        response_data = {
            'item':action,
        }

    return JsonResponse(response_data)

#@cache_page(60 * 60)  # Cache la vista durante 1 hora
@perfil_seleccionado_required
def oc_modal(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador = Profile.objects.all()
    usuario = colaborador.get(id = pk_perfil)
    req = Requis.objects.get(id = pk)

    productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"), cancelado=False, sel_comp = False)
    compras = Compra.objects.all()
    comparativos = Comparativo.objects.filter(creada_por__distritos = usuario.distritos, completo =True)
    oc, created = compras.get_or_create(complete = False, req = req, creada_por = usuario)
    productos_comp = ArticuloComprado.objects.filter(oc=oc)
    form = CompraForm(instance=oc)
    form_product = ArticuloCompradoForm()
    
    
    tag = dof()
    subtotal = 0
    iva = 0
    total = 0
    dif_cant = 0

    last_oc = compras.filter(complete = True, req__orden__distrito = req.orden.distrito).order_by('-folio').first()
    if last_oc:
        folio = last_oc.folio + 1
    else:
        folio = 1
    #abrev = req.orden.distrito.abreviado
    folio_preview = folio
    error_messages = {}

    productos_para_select2 = [
        {'id': producto.id,
         'text': str(producto), 
         'cantidad': str(producto.cantidad), 
         'cantidad_pendiente': str(producto.cantidad_comprada),
         'precioref': str(producto.producto.articulos.producto.producto.precioref),
         'porcentaje': str(producto.producto.articulos.producto.producto.porcentaje)
        } for producto in productos]
    
    productos_comp_to_function = [
        {
            'id': producto.id,
            'precio': str(producto.precio_unitario),
            'precio_ref': str(producto.producto.producto.articulos.producto.producto.precioref),
            'porcentaje': str(producto.producto.producto.articulos.producto.producto.porcentaje)
        } for producto in productos_comp
    ] 
    comparativos_para_select2 = [
        {
            'id': comparativo.id, 
            'text': str(comparativo.nombre)
        } for comparativo in comparativos
    ]

    for item in productos_comp:
        subtotal = decimal.Decimal(subtotal + item.cantidad * item.precio_unitario)
        if item.producto.producto.articulos.producto.producto.iva == True:
            iva = round(subtotal * decimal.Decimal(0.16),2)
        total = decimal.Decimal(subtotal + decimal.Decimal(iva))

    if request.method == 'POST' and  "crear" in request.POST:
        form = CompraForm(request.POST, instance=oc)
        
        if form.is_valid():
            costo_oc = 0
            costo_iva = 0
            articulos = ArticuloComprado.objects.filter(oc=oc)
            requisitados = ArticulosRequisitados.objects.filter(req = oc.req)
            cuenta_art_comprados = requisitados.filter(art_surtido = True).count()
            cuenta_art_totales = requisitados.count()
            if cuenta_art_totales == cuenta_art_comprados and cuenta_art_comprados > 0: #Compara los artículos comprados vs artículos requisitados
                req.colocada = True
            else:
                req.colocada = False
            for articulo in articulos:
                costo_oc = costo_oc + articulo.precio_unitario * articulo.cantidad
                if articulo.producto.producto.articulos.producto.producto.iva == True:
                    costo_iva = decimal.Decimal(costo_oc * decimal.Decimal(0.16))
            for producto in requisitados:
                dif_cant = dif_cant + producto.cantidad - producto.cantidad_comprada
                if producto.art_surtido == False:
                    producto.sel_comp = False
                    producto.save()
           
            if oc.tipo_de_cambio != None and oc.tipo_de_cambio > 0:
                oc.costo_iva = decimal.Decimal(costo_iva)
                oc.costo_oc = decimal.Decimal(costo_oc + costo_iva)
            else:
                oc.costo_iva = decimal.Decimal(costo_iva)
                oc.costo_oc = decimal.Decimal(costo_oc + costo_iva)

            last_oc = Compra.objects.filter(complete = True, req__orden__distrito = req.orden.distrito).order_by('-folio').first()
            if last_oc:
                folio = last_oc.folio + 1
            else:
                folio = 1
            oc.complete = True
            oc.folio = folio
            oc.created_at = date.today()
            form.save()
            oc.save()
            req.save()
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
                <body>
                    <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                    <p>Estimado {oc.req.orden.staff.staff.staff.first_name} {oc.req.orden.staff.staff.staff.last_name},</p>
                    <p>Estás recibiendo este correo porque tu solicitud: {oc.req.orden.folio}| Req: {oc.req.folio} se ha convertido en la OC: {oc.folio},</p>
                    <p>creada por {oc.creada_por.staff.staff.first_name} {oc.creada_por.staff.staff.last_name}.</p>
                    <p>El siguiente paso del sistema: Autorización de OC por Superintedencia Administrativa</p>
                    <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                    <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                </body>
            </html>
            """
            try:
                email = EmailMessage(
                    f'OC Elaborada {oc.folio}',
                    body=html_message,
                    #f'Estimado {requi.orden.staff.staff.staff.first_name} {requi.orden.staff.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.staff.first_name} {requi.requi_autorizada_por.staff.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    to= ['ulises_huesc@hotmail.com',oc.req.orden.staff.staff.staff.email],
                    headers={'Content-Type': 'text/html'}
                    )
                email.content_subtype = "html " # Importante para que se interprete como HTML
                email.send()
                messages.success(request,f'{usuario.staff.staff.first_name}, Has generado la OC {oc.folio} correctamente')
            except (BadHeaderError, SMTPException) as e:
                error_message = f'{usuario.staff.staff.first_name}, Has generado la OC {oc.folio} correctamente pero el correo de notificación no ha sido enviado debido a un error: {e}'
                messages.success(request, error_message)
            return redirect('requisicion-autorizada')
        else:
            for field, errors in form.errors.items():
                error_messages[field] = errors.as_text()
    


    
    context= {
        'comparativos_para_select2': comparativos_para_select2,
        'productos_comp_to_function': productos_comp_to_function,
        'error_messages': error_messages,
        'req':req,
        'form':form,
        'form_product':form_product,
        'productos_para_select2':productos_para_select2,
        'oc':oc,
        'folio':folio_preview,
        'productos':productos,
        'tag':tag,
        'productos_comp':productos_comp,
        'subtotal':subtotal,
        'iva':iva,
        'total':total,
        }
    
    return render(request, 'compras/oc.html', context)

@login_required(login_url='user-login')
def mostrar_comparativo(request, pk):
    comparativo = Comparativo.objects.get(id=pk)
    productos = Item_Comparativo.objects.filter(comparativo = comparativo)
    
    context= {
        'comparativo':comparativo,
        'productos':productos,
        }

    return render(request, 'compras/mostrar_comparativo.html',context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def matriz_oc(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    compras = Compra.objects.filter(complete=True, req__orden__distrito = usuario.distritos).order_by('-folio')
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs
    compras_data = list(compras.values())
    # Obtienes las fechas de inicio y finalización del filtro
    start_date = myfilter.form.cleaned_data.get('start_date')
    end_date = myfilter.form.cleaned_data.get('end_date')
   
    num_approved_requis = 0
    num_requis_atendidas = 0
    # Asegúrate de que start_date y end_date son objetos datetime "aware"
    if start_date is not None and end_date is not None:
    # Si las fechas no tienen información de la zona horaria, hazlas "aware"
        # Filtrar las requisiciones aprobadas dentro del rango de fechas
        approved_requis = Requis.objects.filter(approved_at__gte=start_date, approved_at__lte=end_date, autorizar = True, orden__distrito = usuario.distritos)
        approved_requis_ids = approved_requis.values_list('id', flat=True)
        num_approved_requis = approved_requis.count() 

        # Contar el número de requisiciones aprobadas
        compras_colocadas_ids = Compra.objects.filter(
            created_at__gte=start_date, 
            created_at__lte=end_date, 
            req__colocada=True,
            req_id__in=approved_requis_ids,
            req__orden__distrito = usuario.distritos
        ).values_list('req', flat=True).distinct()

        num_requis_atendidas = len(set(compras_colocadas_ids))


    # Calcular el total de órdenes de compra
    total_de_oc = compras.count()
     # Calcular el número de OC que cumplen el criterio (created_at - approved_at <= 3)
    time_difference = ExpressionWrapper(F('created_at') - F('req__approved_at'), output_field=fields.DurationField())
    compras_con_criterio = compras.annotate(time_difference=time_difference).filter(time_difference__lte=timedelta(days=3))
    oc_cumplen = compras_con_criterio.count()

     # Calcular el indicador de cumplimiento (oc_cumplen / total_de_oc)
    #if total_de_oc > 0:
    #    cumplimiento = (oc_cumplen / total_de_oc)*100
    #else:
    #    cumplimiento = 0

     #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    context= {
        'usuario':usuario,
        #'num_approved_requis': num_approved_requis,
        'compras_list':compras_list,
        'compras':compras,
        'myfilter':myfilter,
        #'cumplimiento': cumplimiento,
        }
    #task_id = request.session.get('task_id')

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_matriz_compras(compras, num_requis_atendidas, num_approved_requis, start_date, end_date)
        #if not task_id:
            #task = convert_excel_matriz_compras_task.delay(compras_data, num_requis_atendidas, num_approved_requis, start_date, end_date)
            #task_id = task.id
            #request.session['task_id'] = task_id
            #context['task_id'] = task_id yes
            #cantidad = compras.count()
            #context['cantidad'] = cantidad
            #messages.success(request, f'Tu reporte se está generando {task_id}')
        

    

    return render(request, 'compras/matriz_compras.html',context)


#def generar_reporte(request):
    

from celery.result import AsyncResult

def verificar_estado_productos(request):
    task_id = request.session.get('task_id_producto')  # Asumiendo que el task_id se pasa como parámetro GET

    if not task_id:
        return JsonResponse({'error': 'No se proporcionó task_id'}, status=400)


    task_result = AsyncResult(task_id)

    if task_result.ready():
        if task_result.successful():
            result = task_result.result
            response_data = {'task_id': task_id, 'status': 'SUCCESS', 'result': result}
        elif task_result.failed():
            response_data = {'task_id': task_id, 'status': 'FAILURE', 'result': str(task_result.result)}
        else:
            response_data = {'task_id': task_id, 'status': task_result.status}
    else:
        response_data = {'task_id': task_id, 'status': 'PENDING'}

    return JsonResponse(response_data)

def clear_task_id_productos(request):
    if 'task_id_producto' in request.session:
        del request.session['task_id_producto']
    return JsonResponse({'status': 'success'})


def verificar_estado(request):
    task_id = request.session.get('task_id')  # Asumiendo que el task_id se pasa como parámetro GET

    if not task_id:
        return JsonResponse({'error': 'No se proporcionó task_id'}, status=400)


    task_result = AsyncResult(task_id)

    if task_result.ready():
        if task_result.successful():
            result = task_result.result
            response_data = {'task_id': task_id, 'status': 'SUCCESS', 'result': result}
        elif task_result.failed():
            response_data = {'task_id': task_id, 'status': 'FAILURE', 'result': str(task_result.result)}
        else:
            response_data = {'task_id': task_id, 'status': task_result.status}
    else:
        response_data = {'task_id': task_id, 'status': 'PENDING'}

    return JsonResponse(response_data)

def clear_task_id(request):
    if 'task_id' in request.session:
        del request.session['task_id']
    return JsonResponse({'status': 'success'})



@login_required(login_url='user-login')
def matriz_oc_productos(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    compras = Compra.objects.filter(complete=True)
    articulos = ArticuloComprado.objects.filter(oc__complete = True, oc__req__orden__distrito = usuario.distritos).order_by('-oc__created_at')
    myfilter = ArticuloCompradoFilter(request.GET, queryset=articulos)
    articulos = myfilter.qs
    articulos_data = list(articulos.values())
    
    #Set up pagination
    p = Paginator(articulos, 50)
    page = request.GET.get('page')
    articulos_list = p.get_page(page)

    context= {
        'articulos_list':articulos_list,
        'articulos':articulos,
        'compras':compras,
        'myfilter':myfilter,
        }
    
    task_id_producto = request.session.get('task_id_producto')

    if request.method == 'POST' and 'btnExcel' in request.POST:
        #return convert_excel_matriz_compras(compras)
        if not task_id_producto:
            task = convert_excel_solicitud_matriz_productos_task.delay(articulos_data)
            task_id_producto = task.id
            request.session['task_id_producto'] = task_id_producto
            context['task_id_producto'] = task_id_producto
            cantidad = articulos.count()
            context['cantidad'] = cantidad
            messages.success(request, f'Tu reporte se está generando {task_id_producto}')

    return render(request, 'compras/matriz_oc_productos.html',context)

@login_required(login_url='user-login')
def productos_oc(request, pk):
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=compra)


    context = {
        'compra':compra,
        'productos':productos,
    }

    return render(request,'compras/oc_producto.html',context)

@login_required(login_url='user-login')
def upload_facturas(request, pk):
    pago = Pago.objects.get(id = pk)
    facturas = Facturas.objects.filter(pago = pago, hecho=True)
    factura, created = Facturas.objects.get_or_create(pago=pago, hecho=False)
    form = Facturas_Form()

    if request.method == 'POST':
        form = Facturas_Form(request.POST or None, request.FILES or None, instance = factura)
        factura = form.save(commit=False)
        factura.fecha_subido = date.today()
        factura.hora_subido = datetime.now().time()
        factura.hecho = True
        if form.is_valid():
            form.save()
            factura.save()
            messages.success(request,'Las facturas se subieron de manera exitosa')
            return redirect('matriz-compras')
        else:
            form = Facturas_Form()
            messages.error(request,'No se pudo subir tu documento')

    context={
        'facturas':facturas,
        'form':form,
        }

    return render(request, 'compras/upload.html', context)

@login_required(login_url='user-login')
def upload_xml(request, pk):
    compra = Compra.objects.get(id = pk)
    form = CompraFactForm()

    if request.method == 'POST':
        form = CompraFactForm(request.POST or None, request.FILES or None, instance = compra)
        if form.is_valid():
            form.save()
            return redirect('matriz-compras')
        else:
            form = CompraFactForm()
            messages.error(request,'No se pudo subir tu documento')

    context={
        'compra':compra,
        'form': form,
        }

    return render(request, 'compras/upload_xml.html', context)

@perfil_seleccionado_required
@login_required(login_url='user-login')
def autorizacion_oc1(request):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
   
    if usuario.tipo.oc_superintendencia == True:
        compras = Compra.objects.filter(complete=True, autorizado1= None, req__orden__distrito = usuario.distritos).order_by('-folio')
    else:
        compras = Compra.objects.filter(complete=True, autorizado1= None, req__orden__distrito = usuario.distritos)
    #compras = Compra.objects.filter(complete=True, autorizado1= None).order_by('-folio')

    form = Compra_ComentarioForm()

    context= {
        'compras':compras,
        }

    return render(request, 'compras/autorizacion_oc1.html',context)

def cancelar_oc1(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc = pk)

    if compra.costo_fletes == None:
        costo_fletes = 0
    
    #Si hay tipo de cambio es porque la compra fue en dólares entonces multiplico por tipo de cambio la cantidad
    #Escenario con dólares
    if compra.tipo_de_cambio:
        costo_oc = compra.costo_oc * compra.tipo_de_cambio
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes * compra.tipo_de_cambio
    #Escenario con pesos
    else:
        costo_oc = compra.costo_oc
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes
        else:
            costo_fletes = 0
    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_total - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)

    if request.method == 'POST':
        compra.oc_autorizada_por = usuario
        compra.autorizado1 = False
        compra.autorizado_date1 = date.today()
        compra.autorizado_hora1 = datetime.now().time()
        compra.save()
        messages.error(request,f'Has cancelado la compra con FOLIO: {compra.folio}')
        return redirect('autorizacion-oc1')

    context = {
        'compra':compra,
        'productos': productos,
        'costo_oc':costo_oc,
        'productos':productos,
        'tipo_cambio':compra.tipo_de_cambio,
        'resta':resta,
        'porcentaje':porcentaje,
        'costo_total':costo_total,
     }
    return render(request,'compras/cancelar_oc1.html', context)

def cancelar_oc2(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc = pk)
    costo_fletes = 0
    if compra.costo_fletes == None:
        costo_fletes = 0
    #Si hay tipo de cambio es porque la compra fue en dólares entonces multiplico por tipo de cambio la cantidad
    #Escenario con dólares
    if compra.tipo_de_cambio:
        costo_oc = compra.costo_oc * compra.tipo_de_cambio
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes * compra.tipo_de_cambio
    #Escenario con pesos
    else:
        costo_oc = compra.costo_oc
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes
    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_total - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)


    if request.method == 'POST':
        compra.oc_autorizada_por2 = usuario
        compra.autorizado2 = False
        compra.autorizado_date2 = date.today()
        compra.autorizado_hora2 = datetime.now().time()
        compra.save()
        messages.error(request,f'Has cancelado la compra con FOLIO: {compra.get_folio}')
        return redirect('autorizacion-oc2')

    context = {
        'compra':compra,
        'productos': productos,
        'costo_oc':costo_oc,
        'productos':productos,
        'tipo_cambio':compra.tipo_de_cambio,
        'resta':resta,
        'porcentaje':porcentaje,
        'costo_total':costo_total,
     }
    return render(request,'compras/cancelar_oc2.html', context)

def back_oc(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    perfil = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc = pk)
    #Traigo la requisición para poderla activar de nuevo, aunque esto ya no es necesario porque no se reactiva propiamente la requi
    #Crearé la cancelación de la OC?
    #Esto está afectando de alguna forma a los productos pendientes cuando se eliminan partidas de la OC?
    requi = Requis.objects.get(id=compra.req.id)

    if compra.costo_fletes == None or compra.costo_fletes == 0:
        costo_fletes = 0
    #Si hay tipo de cambio es porque la compra fue en dólares entonces multiplico por tipo de cambio la cantidad
    #Escenario con dólares
    if compra.tipo_de_cambio:
        costo_oc = compra.costo_oc * compra.tipo_de_cambio
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes * compra.tipo_de_cambio
    #Escenario con pesos
    else:
        costo_oc = compra.costo_oc
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes
    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_total - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)

    form = Compra_ComentarioForm()

    if request.method == 'POST':
        form = Compra_ComentarioForm(request.POST, instance=compra)
        if form.is_valid():
            compra = form.save(commit = False)
            if not compra.autorizado1:
                compra.oc_autorizada_por = perfil
                compra.autorizado1 = None
                compra.complete = False
                compra.autorizado_at = datetime.now()
                #compra.autorizado_hora1 = datetime.now().time()
                compra.regresar_oc = True
            else:
                compra.oc_autorizada_por2 = perfil
                compra.autorizado2 = None
                compra.autorizado1 = None
                compra.complete = False
                compra.autorizado_at_2 = datetime.now()
                #compra.autorizado_hora2 = datetime.now().time()
                compra.regresar_oc = True
            #Esta línea es la que activa a la requi
            #requi.colocada = False
            compra.save()
            #requi.save()
            messages.success(request,f'Has regresado la compra con FOLIO: {compra.get_folio} y ahora podrás encontrar esos productos en el apartado devolución')
            return redirect('compras-devueltas')

    context = {
        'form':form,
        'compra':compra,
        'productos': productos,
        'costo_oc':costo_oc,
        'productos':productos,
        'tipo_cambio':compra.tipo_de_cambio,
        'resta':resta,
        'porcentaje':porcentaje,
        'costo_total':costo_total,
     }

    return render(request,'compras/back_oc.html', context)




def autorizar_oc1(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc=pk)
    form = Compra_ComentarioForm()

    if compra.costo_fletes == None:
        costo_fletes = 0
    #Si hay tipo de cambio es porque la compra fue en dólares entonces multiplico por tipo de cambio la cantidad
    #Escenario con dólares
    if compra.tipo_de_cambio:
        costo_oc = compra.costo_oc * compra.tipo_de_cambio
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes * compra.tipo_de_cambio
        else:
            costo_fletes = 0
    #Escenario con pesos
    else:
        costo_oc = compra.costo_oc
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes
        else:
            costo_fletes = 0
    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_oc - costo_fletes - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)


    if request.method == 'POST':
        form = Compra_ComentarioForm(request.POST, instance=compra)
        if form.is_valid():
            compra = form.save(commit = False)
            compra.autorizado1 = True
            compra.oc_autorizada_por = usuario
            compra.autorizado_date1 = datetime.now()
            #compra.autorizado_hora1 = datetime.now().time()
            compra.save()
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
                    <body>
                        <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                        <p>Estimado {compra.req.orden.staff.staff.staff.first_name} {compra.req.orden.staff.staff.staff.last_name},</p>
                        <p>Estás recibiendo este correo porque tu OC {compra.folio} | RQ: {compra.req.folio} |Sol: {compra.req.orden.folio} ha sido autorizada por {compra.oc_autorizada_por.staff.staff.first_name} {compra.oc_autorizada_por.staff.staff.last_name},</p>
                        <p>El siguiente paso del sistema: Autorización de OC por Gerencia de Distrito</p>
                        <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                        <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                    </body>
                </html>
            """
            try:
                email = EmailMessage(
                    f'OC Autorizada {compra.folio}|RQ: {compra.req.folio} |Sol: {compra.req.orden.folio}',
                    body=html_message,
                    #f'Estimado {requi.orden.staff.staff.staff.first_name} {requi.orden.staff.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.staff.first_name} {requi.requi_autorizada_por.staff.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    to= ['ulises_huesc@hotmail.com',compra.req.orden.staff.staff.staff.email],
                    headers={'Content-Type': 'text/html'}
                    )
                email.content_subtype = "html " # Importante para que se interprete como HTML
                email.send()
                messages.success(request, f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio}')
            except (BadHeaderError, SMTPException) as e:
                error_message = f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio} pero el correo de notificación no ha sido enviado debido a un error: {e}'
                messages.success(request, error_message)    
            
            return redirect('autorizacion-oc1')

    context={
        'form':form,
        'compra':compra,
        'costo_oc':costo_oc,
        'productos':productos,
        'tipo_cambio':compra.tipo_de_cambio,
        'resta':resta,
        'porcentaje':porcentaje,
        'costo_total':costo_total,
        }

    return render(request, 'compras/autorizar_oc1.html',context)

@login_required(login_url='user-login')
def autorizacion_oc2(request):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    #if usuario.tipo.oc_gerencia == True:
    #    compras = Compra.objects.filter(complete = True, autorizado1 = True, autorizado2= None).order_by('-folio')
    #else:
    #    compras = Compra.objects.filter(flete=True,costo_fletes='1')
    compras = Compra.objects.filter(complete = True, autorizado1 = True, autorizado2= None, req__orden__distrito = usuario.distritos).order_by('-folio')

    
    context= {
        'compras':compras,
        }

    return render(request, 'compras/autorizacion_oc2.html',context)


def autorizar_oc2(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc=pk)

    if compra.costo_fletes == None:
        costo_fletes = 0
    #Si hay tipo de cambio es porque la compra fue en dólares entonces multiplico por tipo de cambio la cantidad

    if compra.tipo_de_cambio:
        costo_oc = compra.costo_oc * compra.tipo_de_cambio
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes * compra.tipo_de_cambio
        else:
            costo_fletes = 0
    #Escenario con pesos
    else:
        costo_oc = compra.costo_oc
        if compra.costo_fletes:
            costo_fletes = compra.costo_fletes
        else:
            costo_fletes = 0

    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_oc - costo_fletes - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)

    form = Compra_ComentarioGerForm()

   
    if request.method == 'POST':
        form = Compra_ComentarioGerForm(request.POST, instance=compra)
        if form.is_valid():
            compra = form.save(commit = False)
            compra.autorizado2 = True
            compra.oc_autorizada_por2 = usuario
            compra.autorizado_at_2 = datetime.now()
            #compra.autorizado_hora2 = datetime.now().time()
            compra.save()
            static_path = settings.STATIC_ROOT
            img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
            img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
            image_base64 = get_image_base64(img_path)
            logo_v_base64 = get_image_base64(img_path2)
            # Crear el mensaje HTML
            if compra.cond_de_pago.nombre == "CREDITO":
                archivo_oc = attach_oc_pdf(request, compra.id)
                html_message2 = f"""
                    <html>
                        <head>
                            <meta charset="UTF-8">
                        </head>
                        <body>
                            <p>Estimado(a) {compra.proveedor.contacto}| Proveedor {compra.proveedor.nombre}:,</p>
                            <p>Estás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.folio}.<p>
                            <p>&nbsp;</p>
                            <p> Atte. {compra.creada_por.staff.staff.first_name} {compra.creada_por.staff.staff.last_name}</p> 
                            <p>GRUPO VORDCAB S.A. de C.V.</p>
                            <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                            <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                            <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                        </body>
                    </html>
                """
                try:
                    email = EmailMessage(
                    f'Compra Autorizada {compra.folio}|SAVIA',
                    body=html_message2,
                    from_email =settings.DEFAULT_FROM_EMAIL,
                    to= ['ulises_huesc@hotmail.com', compra.creada_por.staff.staff.email, compra.proveedor.email],
                    headers={'Content-Type': 'text/html'}
                    )
                    email.content_subtype = "html " # Importante para que se interprete como HTML
                    email.attach(f'folio:{compra.folio}.pdf',archivo_oc,'application/pdf')
                    email.send()
                except (BadHeaderError, SMTPException) as e:
                    error_message = f'correo de notificación no ha sido enviado debido a un error: {e}'  

                html_message = f"""
                    <html>
                        <head>
                            <meta charset="UTF-8">
                        </head>
                        <body>
                            <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                            <p>Estimado {compra.req.orden.staff.staff.staff.first_name} {compra.req.orden.staff.staff.staff.last_name},</p>
                            <p>Estás recibiendo este correo porque tu OC {compra.folio} | RQ: {compra.req.folio} |Sol: {compra.req.orden.folio} ha sido autorizada por {compra.oc_autorizada_por2.staff.staff.first_name} {compra.oc_autorizada_por2.staff.staff.last_name},</p>
                            <p>El siguiente paso del sistema: Recepción por parte de Almacén |Compra a crédito</p>
                            <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                            <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                        </body>
                    </html>
                """
                try:
                    email = EmailMessage(
                        f'OC Autorizada Gerencia {compra.folio}|RQ: {compra.req.folio} |Sol: {compra.req.orden.folio}',
                        body=html_message,
                        #f'Estimado {requi.orden.staff.staff.staff.first_name} {requi.orden.staff.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.staff.first_name} {requi.requi_autorizada_por.staff.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                        from_email = settings.DEFAULT_FROM_EMAIL,
                        to= ['ulises_huesc@hotmail.com'],#[requi.orden.staff.staff.staff.email],
                        headers={'Content-Type': 'text/html'}
                        )
                    email.content_subtype = "html " # Importante para que se interprete como HTML
                    email.send()
                    
                    for producto in productos:
                        if producto.producto.producto.articulos.producto.producto.especialista == True:
                            archivo_oc = attach_oc_pdf(request, compra.id)
                            email = EmailMessage(
                                f'Compra Autorizada {compra.folio}',
                                f'Estimado Nombre de Calidad,\n Estás recibiendo este correo porque ha sido aprobada una OC que contiene el producto código:{producto.producto.producto.articulos.producto.producto.codigo} descripción:{producto.producto.producto.articulos.producto.producto.nombre} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA 2.0',
                                settings.DEFAULT_FROM_EMAIL,
                                ['ulises_huesc@hotmail.com'],
                                )
                            email.attach(f'folio:{compra.folio}.pdf',archivo_oc,'application/pdf')
                            email.send()
                    messages.success(request, f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio}')
                except (BadHeaderError, SMTPException) as e:
                    error_message = f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio} pero el correo de notificación no ha sido enviado debido a un error: {e}'
                    messages.warning(request, error_message)    
                
            else:
                html_message = f"""
                    <html>
                        <head>
                            <meta charset="UTF-8">
                        </head>
                        <body>
                            <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                            <p>Estimado {compra.req.orden.staff.staff.staff.first_name} {compra.req.orden.staff.staff.staff.last_name},</p>
                            <p>Estás recibiendo este correo porque tu OC {compra.folio} | RQ: {compra.req.folio} |Sol: {compra.req.orden.folio} ha sido autorizada por {compra.oc_autorizada_por2.staff.staff.first_name} {compra.oc_autorizada_por2.staff.staff.last_name},</p>
                            <p>El siguiente paso del sistema: Pago por parte de tesorería</p>
                            <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                            <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                        </body>
                    </html>
                """
                try:
                    email = EmailMessage(
                        f'OC Autorizada Gerencia {compra.folio}|RQ: {compra.req.folio} |Sol: {compra.req.orden.folio}',
                        body=html_message,
                        #f'Estimado {requi.orden.staff.staff.staff.first_name} {requi.orden.staff.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.staff.first_name} {requi.requi_autorizada_por.staff.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                        from_email = settings.DEFAULT_FROM_EMAIL,
                        to= ['ulises_huesc@hotmail.com'],#[requi.orden.staff.staff.staff.email],
                        headers={'Content-Type': 'text/html'}
                        )
                    email.content_subtype = "html " # Importante para que se interprete como HTML
                    email.send()
                    messages.success(request, f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio}')
                except (BadHeaderError, SMTPException) as e:
                    error_message = f'{usuario.staff.staff.first_name} has autorizado la compra {compra.folio} pero el correo de notificación no ha sido enviado debido a un error: {e}'
                    messages.success(request, error_message)    
            return redirect('autorizacion-oc2')

    context={
        'form':form,
        'compra':compra,
        'costo_oc':costo_oc,
        'productos':productos,
        'tipo_cambio':compra.tipo_de_cambio,
        'resta':resta,
        'porcentaje':porcentaje,
        'costo_total':costo_total,
        }

    return render(request, 'compras/autorizar_oc2.html',context)

def handle_uploaded_file(file, model_instance, field_name):
    setattr(model_instance, field_name, file)
    model_instance.save()

def comparativos(request):
    comparativos = Comparativo.objects.filter(completo = True)
    form = UploadFileForm()
    error_messages = {}

    if request.method == "POST":
        mi_id = request.POST.get('mi_id')
        form = UploadFileForm(request.POST or None, request.FILES or None)
        files = request.FILES.getlist('file')
        cont = 0
        if form.is_valid():
            comparativo = comparativos.get(id=mi_id)
            for f in files:
                if cont == 0:
                    comparativo.cotizacion = files[cont]
                elif cont == 1:
                    comparativo.cotizacion2 = files[cont]
                elif cont == 2:
                    comparativo.cotizacion3 = files[cont]
                elif cont == 3:
                    comparativo.cotizacion4 = files[cont]
                elif cont == 4:
                    comparativo.cotizacion5 = files[cont]
                cont+=1
                comparativo.save()
            messages.success(request,f'Entrando {files}')
            return redirect('comparativos')
        else:
            for field, errors in form.errors.items():
                error_messages[field] = errors.as_text()

    
    context= {
        'error_messages': error_messages,
        'comparativos':comparativos,
        'form':form,
    }
    return render(request,'compras/comparativos.html', context)



@perfil_seleccionado_required
@login_required(login_url='user-login')
def crear_comparativo(request):
    start_time = time.time()  # Tiempo de inicio
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    
    comparativo, created = Comparativo.objects.get_or_create(completo= False, creada_por=usuario)
    productos = Item_Comparativo.objects.filter(comparativo = comparativo, completo = True)
    error_messages = {}
    form_item = Item_ComparativoForm()
    form = ComparativoForm()

    if request.method =='POST':
        if "btn_creacion" in request.POST:
            form = ComparativoForm(request.POST, instance=comparativo)
            if form.is_valid():
                comparativo = form.save(commit=False)
                comparativo.completo = True
                comparativo.created_at = date.today()
                comparativo.creado_por =  usuario
                comparativo.save()
                messages.success(request, f'El comparativo {comparativo.id} ha sido creado')
                return redirect('comparativos')
            else:
                for field, errors in form_item.errors.items():
                    error_messages[field] = errors.as_text()
                messages.error(request,f'No está validando {error_messages}' )
        if "btn_producto" in request.POST:
            articulo, created = Item_Comparativo.objects.get_or_create(completo = False, comparativo = comparativo)
            form_item = Item_ComparativoForm(request.POST, instance= articulo)
            if form_item.is_valid():
                articulo = form_item.save(commit=False)
                articulo.completo = True
                articulo.save()
                messages.success(request, 'Se ha agregado el artículo exitosamente')
                return redirect('crear_comparativo')
            else:
                for field, errors in form_item.errors.items():
                    error_messages[field] = errors.as_text()
                messages.error(request,f'No está validando {error_messages}' )
        if "btn_files" in request.POST:
            #mi_id = request.POST.get('mi_id')
            form = UploadFileForm(request.POST or None, request.FILES or None)
            files = request.FILES.getlist('file')
            cont = 0
            if form.is_valid():
                #comparativo = comparativos.get(id=mi_id)
                #comparativo = form.save(commit = False)
                for f in files:
                    if cont == 0:
                        comparativo.cotizacion = files[cont]
                    elif cont == 1:
                        comparativo.cotizacion2 = files[cont]
                    elif cont == 2:
                        comparativo.cotizacion3 = files[cont]
                    elif cont == 3:
                        comparativo.cotizacion4 = files[cont]
                    elif cont == 4:
                        comparativo.cotizacion5 = files[cont]
                    cont+=1
                comparativo.save()
                messages.success(request,f'Entrando {files}')
                return redirect('crear_comparativo')
        else:
            post_data = request.POST
            post_items = [f"{key}: {value}" for key, value in post_data.items()]
            post_content = ", ".join(post_items)
            messages.error(request, f"Datos recibidos en POST: {post_content}")
        

    end_time = time.time()  # Tiempo de finalización
    total_time = end_time - start_time  # Tiempo total de ejecución    
    
    context= {
        'error_messages': error_messages,
        'productos':productos,
        'form':form,
        'form_item':form_item,
        'comparativo':comparativo,
        'total_time': total_time,
    }

    return render(request, 'compras/crear_comparativo.html', context)

#Ajax Select2
def carga_proveedor(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    term = request.GET.get('term')
    proveedores = Proveedor_direcciones.objects.filter(
         Q(estatus__nombre="NUEVO") | Q(estatus__nombre="APROBADO"),
         distrito = usuario.distritos, 
         nombre__razon_social__icontains = term
    ).values('id','nombre__razon_social','distrito__nombre','domicilio','estatus__nombre')
    data = list(proveedores)
        
    return JsonResponse(data, safe=False)

def carga_proveedor_comparativo(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    term = request.GET.get('term')
    proveedores = Proveedor.objects.filter(razon_social__icontains = term).values('id','razon_social')
    data = list(proveedores)
        
    return JsonResponse(data, safe=False)
    
#Ajax Select2
def carga_productos(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    term = request.GET.get('term')
    articulos = Inventario.objects.filter(distrito = usuario.distritos, producto__nombre__icontains = term).values('id','producto__nombre')
    
    #data = [{"id": item['id'], "text": item['producto__nombre']} for item in articulos]
    data = list(articulos)
        
    return JsonResponse(data, safe=False)



@login_required(login_url='user-login')
def editar_comparativo(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    comparativo =Comparativo.objects.get(id = pk)
    productos = Item_Comparativo.objects.filter(comparativo = comparativo, completo = True)
    proveedores = Proveedor_direcciones.objects.all()
    articulos = Inventario.objects.all()
    form_item = Item_ComparativoForm()
    form = ComparativoForm(instance = comparativo)

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = ComparativoForm(request.POST, request.FILES, instance = comparativo)
            #abrev= usuario.distrito.abreviado
            if form.is_valid():
                comparativo = form.save(commit=False)
                comparativo.completo = True
                comparativo.created_at = date.today()
                #comparativo.created_at_time = datetime.now().time()
                comparativo.creado_por =  usuario
                comparativo.save()
                #form.save()
                messages.success(request, f'El comparativo {comparativo.id} ha sido modificado')
                return redirect('comparativos')
        if "btn_producto" in request.POST:
            articulo, created = Item_Comparativo.objects.get_or_create(completo = False, comparativo = comparativo)
            #producto_id = request.POST.get('producto')
            #producto = Inventario.objects.filter(id = producto_id)
            #form_item.fields['producto'].queryset = producto
            form_item = Item_ComparativoForm(request.POST, instance=articulo)
            if form_item.is_valid():
                articulo = form_item.save(commit=False)
                articulo.completo = True
                articulo.save()
                messages.success(request, 'Se ha agregado el artículo exitosamente')
                return redirect('editar-comparativo')
        
    context= {
        'productos':productos,
        'form':form,
        'form_item':form_item,
        'articulos':articulos,
        'comparativo':comparativo,
        'proveedores':proveedores,
    }

    return render(request, 'compras/actualizar_comparativo.html', context)

def articulos_comparativo(request, pk):
    articulos = Item_Comparativo.objects.filter(comparativo__id = pk , completo = True)

    context= {
        'articulos':articulos,
    }
    return render(request, 'compras/articulos_comparativo.html', context)

def articulo_comparativo_delete(request, pk):
   
    articulo = Item_Comparativo.objects.get(id=pk)
    comparativo = articulo.comparativo.id
   
    messages.success(request,f'El articulo ha sido eliminado exitosamente')
    articulo.delete()

    return redirect('crear_comparativo')

@login_required(login_url='user-login')
def historico_articulos_compras(request):
    registros = ArticuloComprado.history.all()

    myfilter = HistoricalArticuloCompradoFilter(request.GET, queryset=registros)
    registros = myfilter.qs

    #Set up pagination
    p = Paginator(registros, 30)
    page = request.GET.get('page')
    registros_list = p.get_page(page)

    context = {
        'registros_list':registros_list,
        'myfilter':myfilter,
        }

    return render(request,'compras/historico_articulos_comprados.html',context)

def descargar_pdf(request, pk):
    compra = get_object_or_404(Compra, id=pk)
    buf = generar_pdf(compra)
    return FileResponse(buf, as_attachment=True, filename='oc_' + str(compra.folio) + '.pdf')

def attach_oc_pdf(request, pk):
    compra = get_object_or_404(Compra, id=pk)
    buf = generar_pdf(compra)

    # Si en algún lugar más de tu código necesitas hacer más cosas antes de retornar buf.getvalue(),
    # entonces aquí es el lugar para hacerlo. Por ahora, sólo retornaremos el valor.

    return buf.getvalue()


def generar_pdf(compra):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #doc = SimpleDocTemplate(buf, pagesize=letter)
    #Here ends conf.
    #compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=compra.id)

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



    c.drawString(430,caja_iso,'Preparado por:')
    c.drawString(405,caja_iso-10,'SUPT. DE ADQUISIONES')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(515,caja_iso-10,'SUBD ADTVO')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'SEOV-ADQ-N4-01.02')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'003')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'13/11/2017')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Orden de Compra
    c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    c.rect(20,520,565,2, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,755,'Orden de compra')
    c.setLineWidth(.3) #Grosor
    c.line(20,caja_proveedor-8,20,520) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(585,caja_proveedor-8,585,520) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    c.drawString(120,caja_proveedor,'Proveedor')
    c.drawString(400,caja_proveedor, 'Detalles')
    inicio_central = 300
    c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(30,caja_proveedor-20,'Nombre:')
    c.drawString(30,caja_proveedor-40,'RFC:')
    c.drawString(30,caja_proveedor-60,'Uso del CFDI:')
    c.drawString(30,caja_proveedor-80,'Solicitó:')
    c.drawString(30,caja_proveedor-100,'Fecha:')
    c.drawString(30,caja_proveedor-120,'Proveedor Calif:')
    c.drawString(30,caja_proveedor-140,'Tiempo de Entrega:')
    c.drawString(30,caja_proveedor-160,'A.F.:')

    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_proveedor-20,'FOLIO:')

    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_proveedor-20, str(compra.folio))

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(inicio_central + 10,caja_proveedor-35,'No. Requisición:')
    c.drawString(inicio_central + 10,caja_proveedor-55,'Método de pago:')
    c.drawString(inicio_central + 10,caja_proveedor-75,'Condiciones de pago:')
    c.drawString(inicio_central + 10,caja_proveedor-95,'Enviar Factura a:')
    c.drawString(inicio_central + 10,caja_proveedor-115,'Banco:')
    c.drawString(inicio_central + 10,caja_proveedor-135,'Cuenta:')
    c.drawString(inicio_central + 10,caja_proveedor-155,'Clabe:')

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    if compra.proveedor.nombre.razon_social == 'COLABORADOR':
        c.drawString(100,caja_proveedor-20, compra.deposito_comprador.staff.staff.first_name+' '+compra.deposito_comprador.staff.staff.last_name)
    else:
        c.drawString(100,caja_proveedor-20, compra.proveedor.nombre.razon_social)
    c.drawString(100,caja_proveedor-40, compra.proveedor.nombre.rfc)
    c.drawString(100,caja_proveedor-60, compra.uso_del_cfdi.descripcion)
    c.drawString(100,caja_proveedor-80, compra.req.orden.staff.staff.staff.first_name +' '+ compra.req.orden.staff.staff.staff.last_name)
    c.drawString(100,caja_proveedor-100, compra.created_at.strftime("%d/%m/%Y"))
    c.drawString(100,caja_proveedor-120, compra.proveedor.estatus.nombre)
    if compra.dias_de_entrega:
        c.drawString(110,caja_proveedor-140, str(compra.dias_de_entrega)+' '+'días hábiles')

    if compra.req.orden.activo:
        c.drawString(60,caja_proveedor-160, compra.req.orden.activo.eco_unidad + ' '+ compra.req.orden.activo.descripcion)
    else:
        c.drawString(60,caja_proveedor-160, 'NA')


    c.drawString(inicio_central + 90,caja_proveedor-35, str(compra.req.folio))
    c.drawString(inicio_central + 90,caja_proveedor-55, 'Transferencia Electrónica')
    c.drawString(inicio_central + 90,caja_proveedor-95, 'tesoreria@grupovordcab.com') #Esta parte hay que configurarla para que cambie de acuerdo al distrito
    if compra.proveedor.nombre.razon_social == 'COLABORADOR':
        c.drawString(inicio_central + 90,caja_proveedor-115, compra.deposito_comprador.banco.nombre)
        c.drawString(inicio_central + 90,caja_proveedor-135, compra.deposito_comprador.cuenta_bancaria)
        c.drawString(inicio_central + 90,caja_proveedor-155, compra.deposito_comprador.clabe)
    else:
        c.drawString(inicio_central + 90,caja_proveedor-115, compra.proveedor.banco.nombre)
        c.drawString(inicio_central + 90,caja_proveedor-135, compra.proveedor.cuenta)
        c.drawString(inicio_central + 90,caja_proveedor-155, compra.proveedor.clabe)




    if compra.cond_de_pago.nombre == "CREDITO":
        c.drawString(inicio_central + 100,caja_proveedor-75, compra.cond_de_pago.nombre + '  ' + str(compra.proveedor.dias_credito) + ' días')
    else:
        c.drawString(inicio_central + 100,caja_proveedor-75, compra.cond_de_pago.nombre )


    data =[]
    high = 495
    data.append(['''Código''','''Producto''', '''Cantidad''', '''Unidad''', '''P.Unitario''', '''Importe'''])
    for producto in productos:
        importe = producto.precio_unitario * producto.cantidad
        importe_rounded = round(importe, 4)
        data.append([
            producto.producto.producto.articulos.producto.producto.codigo,
            producto.producto.producto.articulos.producto.producto.nombre,
            producto.cantidad, 
            producto.producto.producto.articulos.producto.producto.unidad,
            producto.precio_unitario,
            importe_rounded
        ])
        high = high - 18

    c.setFillColor(black)
    c.setFont('Helvetica',8)

    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,200,340,20, fill=True, stroke=False) #2ra linea azul, donde esta el proyecto y el subproyecto, se coloca altura de 150
    c.setFillColor(black)
    c.setFont('Helvetica',7)

    c.setFillColor(white)
    c.setLineWidth(.1)
    c.setFont('Helvetica-Bold',10)
    c.drawString(25,205,'Proyecto:')
    c.drawString(100,205,compra.req.orden.proyecto.nombre)
    c.setFillColor(black)
    c.drawString(25,190,'Subproyecto:')
    c.drawString(25,175,'Elaboró:')
    c.drawString(25,160,'Moneda:')
    c.setFont('Helvetica',8)
    
    
    c.drawString(100,190,compra.req.orden.subproyecto.nombre)
    c.drawString(100,175,compra.creada_por.staff.staff.first_name + ' ' +compra.creada_por.staff.staff.last_name)
    c.drawString(100,160,compra.moneda.nombre)

    c.setLineWidth(.3)
    c.line(370,220,370,160) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(370,160,580,160)

    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)

    montos_align = 480
    c.drawRightString(montos_align,210,'Sub Total:')
    c.drawRightString(montos_align,200,'IVA 16%:')
    c.drawRightString(montos_align,190,'Importe Neto:')
    
    c.setFillColor(prussian_blue)
    c.setFillColor(black)
    c.drawString(20,130,'Opciones y condiciones:')
    c.setFont('Helvetica',8)
    letras = 320
    c.drawString(20,140,'Total con letra:')
    #c.line(135,90,215,90 ) #Linea de Autorizacion
    #c.line(350,90,430,90)
    c.drawCentredString(175,70,'Autorización')
    c.drawCentredString(390,70,'Autorización')

    c.drawCentredString(175,80,'Superintendente Administrativo')
    c.drawCentredString(390,80,'Gerencia Zona')
    c.setFont('Helvetica-Bold',8)
    if compra.autorizado1 ==  True:
        c.drawCentredString(175,90,compra.oc_autorizada_por.staff.staff.first_name + ' ' +compra.oc_autorizada_por.staff.staff.last_name)
    if compra.autorizado2 == True:
        c.drawCentredString(390,90,compra.oc_autorizada_por2.staff.staff.first_name + ' ' + compra.oc_autorizada_por2.staff.staff.last_name)

    c.setFont('Helvetica',10)
    subtotal = compra.costo_oc - compra.costo_iva
    
    importe_neto = compra.costo_oc
    if compra.impuestos:
        subtotal = subtotal - compra.impuestos
        c.setFillColor(black)
        c.setFont('Helvetica-Bold',9)
        c.drawRightString(montos_align,170,'Impuestos Adicionales:')
        c.setFont('Helvetica',10)
        costo_impuestos = format(float(compra.impuestos), '.2f')
        c.drawRightString(montos_align + 90, 180, '$' + str(costo_impuestos))
        c.drawRightString(montos_align, 180, 'Impuestos:')
        #importe_neto = importe_neto + compra.impuestos
    if compra.retencion:
        subtotal = subtotal + compra.retencion
        costo_retencion = format(float(compra.retencion), '.2f')
        c.drawRightString(montos_align + 90, 180, '$' + str(costo_retencion))
        c.drawRightString(montos_align, 180, 'Retención:')
        #importe_neto = importe_neto - compra.retencion
    costo_subtotal = format(float(subtotal), '.2f')
    c.drawRightString(montos_align + 90,210,'$ ' + str(costo_subtotal))
    costo_con_iva = format(float(compra.costo_iva), '.2f')
    c.drawRightString(montos_align + 90,200,'$ ' + str(costo_con_iva))
    costo_oc =  format(float(compra.costo_oc), '.2f')
    c.drawRightString(montos_align + 90,190,'$ ' + str(costo_oc))
    
   
    #if compra.costo_fletes is None:
    #c.setFillColor(prussian_blue)
       
    total =  format(float(compra.costo_plus_adicionales), '.2f')
    if compra.costo_fletes:
        importe_neto = importe_neto + compra.costo_fletes
        c.drawRightString(montos_align,160,'Total:')
        c.drawRightString(montos_align,180,'Costo fletes:')
        c.drawRightString(montos_align + 90,180,'$ ' + str(compra.costo_fletes))
        c.drawRightString(montos_align + 90,160,'$ ' + str(total))
    else:
        c.drawRightString(montos_align,170,'Total:')
        
        c.drawRightString(montos_align + 90,170,'$ ' + str(total))
    
    
    c.setFillColor(prussian_blue)
    
       
   
            
  
           
   
       
    c.setFont('Helvetica', 9)
    
   

    if compra.moneda.nombre == "PESOS":
        c.drawString(80,140, num2words(compra.costo_oc, lang='es', to='currency', currency='MXN'))
    if compra.moneda.nombre == "DOLARES":
        c.drawString(80,140, num2words(compra.costo_oc, lang='es', to='currency',currency='USD'))

    c.setFillColor(black)
    width, height = letter
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]

    if compra.opciones_condiciones is not None:
        options_conditions = compra.opciones_condiciones
    else:
        options_conditions = "NA"

    options_conditions_paragraph = Paragraph(options_conditions, styleN)


    # Crear un marco (frame) en la posición específica
    frame = Frame(135, 0, width-145, height-648, id='normal')

    # Agregar el párrafo al marco
    frame.addFromList([options_conditions_paragraph], c)
    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)

    
    table = Table(data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm,])
    table_style = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 8),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table_style2 = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), colors.black),
        ('FONTSIZE',(0,0),(-1,0), 6),
        #('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table.setStyle(table_style)

    rows_per_page = 15
    total_rows = len(data) - 1  # Excluye el encabezado
    remaining_rows = total_rows - rows_per_page

    if remaining_rows <= 0:
        # Si no hay suficientes filas para una segunda página, dibujar la tabla completa en la primera página
        table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        table.drawOn(c, 20, high)  # Posición en la primera página
    else:
        # Dibujar las primeras 15 filas en la primera página
        first_page_data = data[:rows_per_page + 1]  # Incluye el encabezado
        first_page_table = Table(first_page_data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm])
        first_page_table.setStyle(table_style)
        first_page_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        first_page_table.drawOn(c, 20, high)  # Posición en la primera página

        # Agregar una nueva página y dibujar las filas restantes en la segunda página
        c.showPage()
        remaining_data = data[rows_per_page + 1:]
        remaining_table = Table(remaining_data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm])
        remaining_table.setStyle(table_style2)
        remaining_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        remaining_table_height = len(remaining_data) * 18
        remaining_table_y = c._pagesize[1] - 70 - remaining_table_height - 10  # Espacio para el encabezado
        remaining_table.drawOn(c, 20, remaining_table_y)  # Posición en la segunda página

        # Agregar el encabezado en la segunda página
        c.setFont('Helvetica', 8)
        c.drawString(420, caja_iso, 'Preparado por:')
        c.drawString(420, caja_iso - 10, 'SUP. ADMON')
        c.drawString(520, caja_iso, 'Aprobación')
        c.drawString(520, caja_iso - 10, 'SUB ADM')
        c.drawString(150, caja_iso - 20, 'Número de documento')
        c.drawString(160, caja_iso - 30, 'F-ADQ-N4-01.02')
        c.drawString(245, caja_iso - 20, 'Clasificación del documento')
        c.drawString(275, caja_iso - 30, 'Controlado')
        c.drawString(355, caja_iso - 20, 'Nivel del documento')
        c.drawString(380, caja_iso - 30, 'N5')
        c.drawString(440, caja_iso - 20, 'Revisión No.')
        c.drawString(452, caja_iso - 30, '000')
        c.drawString(510, caja_iso - 20, 'Fecha de Emisión')
        c.drawString(525, caja_iso - 30, '1-Sep.-18')

        caja_proveedor = caja_iso - 65
        c.setFont('Helvetica', 12)
        c.setFillColor(prussian_blue)
        c.rect(150, 750, 250, 20, fill=True, stroke=False)  # Barra azul superior Orden de Compra
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(280, 755, 'Orden de compra')
        c.drawInlineImage('static/images/logo_vordcab.jpg', 45, 730, 3 * cm, 1.5 * cm)  # Imagen vortec
    
    c.showPage()
    # Agregar el encabezado en la segunda página
    c.setFont('Helvetica', 8)
    c.drawString(430, caja_iso, 'Preparado por:')
    c.drawString(420, caja_iso - 10, 'ASIST. TEC. SUBAD')
    c.drawString(525, caja_iso, 'Aprobación')
    c.drawString(520, caja_iso - 10, 'SUBD-ADTVO')
    c.drawString(50, caja_iso - 35, 'Número de documento')
    c.drawString(50, caja_iso - 45, 'SEOV-ADQ-N4-01.04')
    c.drawString(145, caja_iso - 35, 'Clasificación del documento')
    c.drawString(175, caja_iso - 45, 'No Controlado')
    c.drawString(255, caja_iso - 35, 'Nivel del documento')
    c.drawString(280, caja_iso - 45, 'N5')
    c.drawString(340, caja_iso - 35, 'Revisión No.')
    c.drawString(352, caja_iso - 45, '001')
    c.drawString(410, caja_iso - 35, 'Fecha de Emisión')
    c.drawString(425, caja_iso - 45, '03/05/23')
    c.drawString(500, caja_iso - 35, 'Fecha de Revisión')
    c.drawString(525, caja_iso - 45, '06/09/23')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica', 12)
    c.setFillColor(prussian_blue)
    c.rect(155, 735, 250, 35, fill=True, stroke=False)  # Barra azul superior encabezado
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(280, 755, 'Requisitos en Materia de Gestión')
    c.drawCentredString(280, 740, 'de Seguridad, Salud y Medio Ambiente')
    c.drawInlineImage('static/images/logo_vordcab.jpg', 60, 735, 2 * cm, 1 * cm)  # Imagen vortec


    
    #c.setFont("Helvetica-Bold", 12)
    #c.setFillColor(prussian_blue)  # Asumiendo que prussian_blue está definido
    #c.drawCentredString(300, 680, )  # Ajusta la posición según sea necesario
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontSize = 10
    #styleN.color = prussian_blue
    styleN.leading = 13  # Espaciado entre líneas
    styleN = ParagraphStyle('Justicado', parent=styles['Normal'], alignment=TA_JUSTIFY)

    styleT = styles["Normal"]
    styleT.fontSize = 13
    styleT.fontName = 'Helvetica-Bold'
    styleT.textColor = prussian_blue
    styleT.leading = 17
    styleT = ParagraphStyle('Center', parent=styles['Normal'], alignment= TA_CENTER)

    texto = """El objeto del presente escrito es poner en conocimiento, de los proveedores que realizan trabajos para nuestra empresa, 
                los requerimientos mínimos que le sean de aplicación, que debe de cumplir en lo referente a la seguridad y salud en el 
                trabajo, calidad y protección del medio ambiente. La aceptación de una orden de compra implica la responsabilidad por 
                parte del proveedor del conocimiento y aceptación de lo descrito.<br/>Nuestra empresa tiene implantado un SEOV 
                (Sistema de Excelencia Operativa Vordcab), bajo las normas ISO 9001:2015, ISO 14001:2015 e ISO 45001:2018, 
                por lo que se requiere que nuestros proveedores colaboren en el cumplimiento de los siguientes requisitos: <br/>
                """
    
    texto2 = """En todo momento el proveedor está obligado a cumplir con la legislación aplicable al servicio que está prestando.<br/>
El proveedor se compromete a garantizar el cumplimiento de lo solicitado en el pedido u orden de compra del material o del trabajo 
externo.<br/>
El proveedor debería poder garantizar la correcta gestión y control de: los residuos, emisiones atmosféricas, ruidos, 
efluentes residuales, productos peligrosos, afectación del suelo y mantenimiento de instalaciones, respecto al servicio prestado.<br/>
El proveedor deberá aplicar las medidas preventivas necesarias, para evitar situaciones de peligro o emergencia como derrame, fuga, 
incendio, etc., durante la realización del trabajo encomendado. Y si es preciso formar e informar a su personal sobre manipulación, 
almacenaje, uso y riesgos de productos o preparados peligrosos.<br/>
El proveedor deberá facilitar la documentación ambiental y de seguridad que se le solicite o requiera.<br/>
Si el proveedor tiene algún servicio que presta a nuestra empresa subcontratado, por ejemplo, transporte, deberá transmitir este 
documento a su subcontratista.<br/> """
    texto3 = """El proveedor deberá trabajar adoptando buenas prácticas ambientales y cumplir con los procedimientos internos que se 
    le hayan comunicado respecto a HSE y la Prevención de Riesgos Laborales.<br/>
Las empresas que realicen trabajos para nuestra empresa deberán cumplirse los requisitos de seguridad establecidos, uso de EPP, 
protecciones colectivas, formación, seguridad equipos,
medidas preventivas<br/>
Si durante el trabajo se deben retirar residuos peligrosos (aceites, aguas con productos peligrosos, pinturas, disolventes, sus envases)
o /y no peligrosos (escombros, embalajes), se recogerán en recipientes adecuados según la cantidad a retirar. Los recipientes llenos
serán retirados por la empresa que preste el servicio o entregados a nuestra empresa, según convenga, para su correcto almacenamiento 
y gestión posterior.<br/>
Si no sabe qué hacer con algún residuo o efluente residual o cualquier otra cosa, que se ha originado mientras prestaba el servicio,
 avise a la persona que le haya atendido o al Responsable de seguridad. No tomará decisiones.<br/>
Si detecta cualquier situación de riesgo/emergencia (ambiental, personal, de seguridad), lo comunicará de inmediato a cualquier persona
de la empresa o a la que le haya atendido o al Responsable de seguridad. Nunca actué. Deberá seguir las normas de emergencia que se le
 han facilitado a la entrada.<br/>
Si mientras trabaja se produce una situación de emergencia (derrame o fuga de producto peligrosos), y le han facilitado la formación y 
medios necesarios para actuar, proceda según la instrucción que se le ha facilitado, en caso contrario avise de inmediato a cualquier 
persona de la empresa o a la que le ha atendido o al Responsable de seguridad.<br/>"""
    titulo1 = "REQUISITOS OBLIGATORIOS PARA PROVEEDORES DE GRUPO VORDCAB"
    titulo2 = """REQUISITOS GENERALES PARA TODOS LOS PROVEEDORES"""
    titulo3 = """REQUISITOS SI USTED PRESTA EL SERVICIO O PARTE DE SERVICIO DENTRO <br/> 
                DE LAS INSTALACIONES DE GRUPO VORDCAB"""
    
    titulo1 = Paragraph(titulo1, styleT)
    parrafo = Paragraph(texto, styleN)
    titulo2 = Paragraph(titulo2, styleT)
    parrafo2 = Paragraph(texto2, styleN)
    titulo3 = Paragraph(titulo3, styleT)
    parrafo3 = Paragraph(texto3, styleN)

    ancho, alto = letter  # Asegúrate de tener estas dimensiones definidas
    #frame = Frame(120, 720, ancho - 100, alto - 100, id='frameTextoConstante')  # Ajusta las dimensiones según sea necesario
    elementos = [titulo1, Spacer(1,25), parrafo, Spacer(1,25),titulo2,Spacer(1,25), parrafo2, Spacer(1,25),titulo3,Spacer(1,25), parrafo3]
    frame = Frame(30, 0, width-50, height-100, id='frameTextoConstante')
    frame.addFromList(elementos, c)

    c.save()
    buf.seek(0)
    return buf


def generar_pdf_proveedor(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #doc = SimpleDocTemplate(buf, pagesize=letter)
    #Here ends conf.
    #compra = Compra.objects.get(id=pk)
    proveedor = Proveedor_direcciones.objects.get(id=pk)

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



    c.drawString(430,caja_iso,'Preparado por:')
    c.drawString(405,caja_iso-10,'Auditoría de Proveedores')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(515,caja_iso-10,'SUBD QHSE')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(150,caja_iso-30,'SEOV-CTE-N5-05.01')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'09/01/2024')


    c.drawString(500,caja_iso - 45,'Fecha:')
    c.drawString(5400,caja_iso - 45, str(proveedor.modificado_fecha))
    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_iso-60,'FOLIO:')

    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_iso-60, str(proveedor.id))

    #Primera Tabla
    caja_proveedor = caja_iso - 85
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(140,750,260,20, fill=True, stroke=False) #Barra azul superior Título
    c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior | Datos Bancarios
    c.rect(20,caja_proveedor - 100,565,5, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(270,755,'Carta de Contactos y Datos Bancarios')
    c.setLineWidth(.3) #Grosor
    #c.line(20,caja_proveedor-8,20,520) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    #c.line(585,caja_proveedor-8,585,520) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    c.drawString(200,caja_proveedor,'DATOS BANCARIOS MONEDA NACIONAL')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)
    #Primera columna
    c.drawString(30,caja_proveedor-20,'Nombre:')
    c.drawString(30,caja_proveedor-40,'Banco:')
    c.drawString(30,caja_proveedor-60,'Clabe:')
    c.drawString(30,caja_proveedor-80,'Convenio:')
    #Segunda Columna
    c.drawString(300,caja_proveedor-40,'Cuenta:')
    c.drawString(300,caja_proveedor-60,'Referencia:')
   


    c.setFillColor(black)
    c.setFont('Helvetica',9)
   
    #Primera columna
    c.drawString(100,caja_proveedor-20, proveedor.nombre.razon_social)
    c.drawString(100,caja_proveedor-40, proveedor.banco.nombre)
    c.drawString(100,caja_proveedor-60, proveedor.clabe)
    c.drawString(100,caja_proveedor-80, proveedor.contratocie)
    #Segunda columna
    c.drawString(370,caja_proveedor-40, proveedor.cuenta)
    c.drawString(370,caja_proveedor-60, 'NR')

    
    #Segunda tabla
    segunda_tabla = caja_proveedor - 150
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,  segunda_tabla - 8,565,20, fill=True, stroke=False) #Barra azul superior | Datos Bancarios Dólares
    c.rect(20, segunda_tabla - 80,565,5, fill=True, stroke=False) #Linea posterior horizontal
   

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    c.drawString(220, segunda_tabla,'DATOS BANCARIOS DÓLARES')
    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)
    #Primera columna
    c.drawString(30,segunda_tabla-20,'Nombre:')
    c.drawString(30,segunda_tabla-40,'Banco:')
    c.drawString(30,segunda_tabla-60,'Clabe Spid:')
    #Segunda Columna
    c.drawString(300,segunda_tabla-40,'Cuenta:')
    c.drawString(300,segunda_tabla-60,'Codigo Swift:')
   
    c.setFillColor(black)
    c.setFont('Helvetica',9)
   
    #Primera columna
    c.drawString(100,segunda_tabla-20, proveedor.nombre.razon_social)
    c.drawString(100,segunda_tabla-40, proveedor.banco.nombre)
    c.drawString(100,segunda_tabla-60, proveedor.spid)
    #Segunda columna
    c.drawString(370,segunda_tabla-40, proveedor.cuenta)
    if proveedor.swift:
        c.drawString(370,segunda_tabla-60, proveedor.swift)
    else:
        c.drawString(370,segunda_tabla-60, 'NA')

    #Tercera tabla
    tercera_tabla = segunda_tabla - 140
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,   tercera_tabla - 8,565,20, fill=True, stroke=False) #Barra azul superior | Datos Bancarios Dólares
    c.rect(20,  tercera_tabla - 35,565,5, fill=True, stroke=False) #Linea posterior horizontal
   

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    c.drawString(230,  tercera_tabla,'CONDICIONES DE COMPRA')
    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)
    #Única Fila
    c.drawString(30,tercera_tabla-20,'Crédito:')
    c.drawString(150,tercera_tabla-20,'Contado:')
    c.drawString(300,tercera_tabla-20,'Días de Crédito:')
   
    c.setFillColor(black)
    c.setFont('Helvetica',9)
   
    #Primera columna
    if proveedor.financiamiento:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(70,tercera_tabla-20, "X")
    else:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(200,tercera_tabla-20, "X")
    c.drawString(380,tercera_tabla-20, str(proveedor.dias_credito))
   

    #Cuarta tabla
    cuarta_tabla = tercera_tabla - 80
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20, cuarta_tabla - 8,565,20, fill=True, stroke=False) #Barra azul superior | Datos Bancarios Dólares
    c.rect(20, cuarta_tabla - 120,565,5, fill=True, stroke=False) #Linea posterior horizontal
   

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    c.drawString(220, cuarta_tabla,'DATOS DE PROVEEDOR Y CONTACTO')
    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)
    #Primera columna
    c.drawString(30,cuarta_tabla-20,'Razón Social:')
    c.drawString(30,cuarta_tabla-40,'Dirección:')
    c.drawString(30,cuarta_tabla-60,'Estado:')
    c.drawString(30,cuarta_tabla-80,'RFC:')
    c.drawString(30,cuarta_tabla-100,'Contacto:')
    #Segunda Columna
    c.drawString(300,cuarta_tabla-60,'Teléfono:')
    c.drawString(300,cuarta_tabla-80,'Email:')
    
   
    c.setFillColor(black)
    c.setFont('Helvetica',9)
   
    #Primera columna
    c.drawString(100,cuarta_tabla-20, proveedor.nombre.razon_social)
    c.drawString(100,cuarta_tabla-40, proveedor.domicilio)
    if proveedor.estado:
        c.drawString(100,cuarta_tabla-60, str(proveedor.estado.nombre))
    else:
        c.drawString(100,cuarta_tabla-60, 'No registro')
    c.drawString(100,cuarta_tabla-80, proveedor.nombre.rfc)
    c.drawString(100,cuarta_tabla-100, proveedor.contacto)
    #Segunda columna
    c.drawString(370,cuarta_tabla-60, proveedor.telefono)
    c.drawString(370,cuarta_tabla-80, proveedor.email)
   
   
    """c.setLineWidth(.3)
    c.line(370,220,370,160) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(370,160,580,160)

    c.setFillColor(black)
    c.setFont('Helvetica-Bold',9)

    montos_align = 480
    c.drawRightString(montos_align,210,'Sub Total:')
    c.drawRightString(montos_align,200,'IVA 16%:')
    c.drawRightString(montos_align,190,'Importe Neto:')
    c.drawRightString(montos_align,180,'Costo fletes:')
    c.setFillColor(prussian_blue)
    c.setFillColor(black)
    c.drawString(20,130,'Opciones y condiciones:')
    c.setFont('Helvetica',8)
    letras = 320
    c.drawString(20,140,'Total con letra:')
    #c.line(135,90,215,90 ) #Linea de Autorizacion
    #c.line(350,90,430,90)
    c.drawCentredString(175,70,'Autorización')
    c.drawCentredString(390,70,'Autorización')

    c.drawCentredString(175,80,'Superintendente Administrativo')
    c.drawCentredString(390,80,'Gerencia Zona')
    c.setFont('Helvetica-Bold',8)
    if compra.autorizado1 ==  True:
        c.drawCentredString(175,90,compra.oc_autorizada_por.staff.staff.first_name + ' ' +compra.oc_autorizada_por.staff.staff.last_name)
    if compra.autorizado2 == True:
        c.drawCentredString(390,90,compra.oc_autorizada_por2.staff.staff.first_name + ' ' + compra.oc_autorizada_por2.staff.staff.last_name)

    c.setFont('Helvetica',10)
    subtotal = compra.costo_oc - compra.costo_iva
    c.drawRightString(montos_align + 90,210,'$ ' + str(subtotal))
    c.drawRightString(montos_align + 90,200,'$ ' + str(compra.costo_iva))
    c.drawRightString(montos_align + 90,190,'$ ' + str(compra.costo_oc))
    if compra.costo_fletes is None:
        compra.costo_fletes = 0

    c.drawRightString(montos_align + 90,180,'$ ' + str(compra.costo_fletes))
    c.setFillColor(prussian_blue)

    if compra.impuestos:
        c.setFillColor(black)
        c.setFont('Helvetica-Bold',9)
        c.drawRightString(montos_align,170,'Impuestos Adicionales:')
        c.setFont('Helvetica',10)

    if compra.impuestos:
        c.drawRightString(montos_align + 90,170,'$ ' + str(compra.impuestos))
        c.setFillColor(prussian_blue)
        c.drawRightString(montos_align,160,'Total:')
        c.drawRightString(montos_align + 90,160,'$ ' + str(compra.costo_plus_adicionales))
    else:
        c.drawRightString(montos_align,170,'Total:')
        c.drawRightString(montos_align + 90,170,'$ ' + str(compra.costo_plus_adicionales))
    c.setFont('Helvetica', 9)
    
    if compra.moneda.nombre == "PESOS":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='es', to='currency', currency='MXN'))
    if compra.moneda.nombre == "DOLARES":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='es', to='currency',currency='USD'))

    c.setFillColor(black)
    width, height = letter
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]

    if compra.opciones_condiciones is not None:
        options_conditions = compra.opciones_condiciones
    else:
        options_conditions = "NA"

    options_conditions_paragraph = Paragraph(options_conditions, styleN)


    # Crear un marco (frame) en la posición específica
    frame = Frame(135, 0, width-145, height-648, id='normal')

    # Agregar el párrafo al marco
    frame.addFromList([options_conditions_paragraph], c)
    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)

    
    table = Table(data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm,])
    table_style = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 8),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table_style2 = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), colors.black),
        ('FONTSIZE',(0,0),(-1,0), 6),
        #('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table.setStyle(table_style)

    rows_per_page = 15
    total_rows = len(data) - 1  # Excluye el encabezado
    remaining_rows = total_rows - rows_per_page

    if remaining_rows <= 0:
        # Si no hay suficientes filas para una segunda página, dibujar la tabla completa en la primera página
        table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        table.drawOn(c, 20, high)  # Posición en la primera página
    else:
        # Dibujar las primeras 15 filas en la primera página
        first_page_data = data[:rows_per_page + 1]  # Incluye el encabezado
        first_page_table = Table(first_page_data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm])
        first_page_table.setStyle(table_style)
        first_page_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        first_page_table.drawOn(c, 20, high)  # Posición en la primera página

        # Agregar una nueva página y dibujar las filas restantes en la segunda página
        c.showPage()
        remaining_data = data[rows_per_page + 1:]
        remaining_table = Table(remaining_data, colWidths=[1.2 * cm, 13 * cm, 1.5 * cm, 1.2 * cm, 1.5 * cm, 1.5 * cm])
        remaining_table.setStyle(table_style2)
        remaining_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        remaining_table_height = len(remaining_data) * 18
        remaining_table_y = c._pagesize[1] - 70 - remaining_table_height - 10  # Espacio para el encabezado
        remaining_table.drawOn(c, 20, remaining_table_y)  # Posición en la segunda página

        # Agregar el encabezado en la segunda página
        c.setFont('Helvetica', 8)
        c.drawString(420, caja_iso, 'Preparado por:')
        c.drawString(420, caja_iso - 10, 'SUP. ADMON')
        c.drawString(520, caja_iso, 'Aprobación')
        c.drawString(520, caja_iso - 10, 'SUB ADM')
        c.drawString(150, caja_iso - 20, 'Número de documento')
        c.drawString(160, caja_iso - 30, 'F-ADQ-N4-01.02')
        c.drawString(245, caja_iso - 20, 'Clasificación del documento')
        c.drawString(275, caja_iso - 30, 'Controlado')
        c.drawString(355, caja_iso - 20, 'Nivel del documento')
        c.drawString(380, caja_iso - 30, 'N5')
        c.drawString(440, caja_iso - 20, 'Revisión No.')
        c.drawString(452, caja_iso - 30, '000')
        c.drawString(510, caja_iso - 20, 'Fecha de Emisión')
        c.drawString(525, caja_iso - 30, '1-Sep.-18')

        caja_proveedor = caja_iso - 65
        c.setFont('Helvetica', 12)
        c.setFillColor(prussian_blue)
        c.rect(150, 750, 250, 20, fill=True, stroke=False)  # Barra azul superior Orden de Compra
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(280, 755, 'Orden de compra')
        c.drawInlineImage('static/images/logo_vordcab.jpg', 45, 730, 3 * cm, 1.5 * cm)  # Imagen vortec
    
    c.showPage()
    # Agregar el encabezado en la segunda página
    c.setFont('Helvetica', 8)
    c.drawString(430, caja_iso, 'Preparado por:')
    c.drawString(420, caja_iso - 10, 'ASIST. TEC. SUBAD')
    c.drawString(525, caja_iso, 'Aprobación')
    c.drawString(520, caja_iso - 10, 'SUBD-ADTVO')
    c.drawString(50, caja_iso - 35, 'Número de documento')
    c.drawString(50, caja_iso - 45, 'SEOV-ADQ-N4-01.04')
    c.drawString(145, caja_iso - 35, 'Clasificación del documento')
    c.drawString(175, caja_iso - 45, 'No Controlado')
    c.drawString(255, caja_iso - 35, 'Nivel del documento')
    c.drawString(280, caja_iso - 45, 'N5')
    c.drawString(340, caja_iso - 35, 'Revisión No.')
    c.drawString(352, caja_iso - 45, '001')
    c.drawString(410, caja_iso - 35, 'Fecha de Emisión')
    c.drawString(425, caja_iso - 45, '03/05/23')
    c.drawString(500, caja_iso - 35, 'Fecha de Revisión')
    c.drawString(525, caja_iso - 45, '06/09/23')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica', 12)
    c.setFillColor(prussian_blue)
    c.rect(155, 735, 250, 35, fill=True, stroke=False)  # Barra azul superior encabezado
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(280, 755, 'Requisitos en Materia de Gestión')
    c.drawCentredString(280, 740, 'de Seguridad, Salud y Medio Ambiente')
    c.drawInlineImage('static/images/logo_vordcab.jpg', 60, 735, 2 * cm, 1 * cm)  # Imagen vortec


    
    #c.setFont("Helvetica-Bold", 12)
    #c.setFillColor(prussian_blue)  # Asumiendo que prussian_blue está definido
    #c.drawCentredString(300, 680, )  # Ajusta la posición según sea necesario
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontSize = 10
    #styleN.color = prussian_blue
    styleN.leading = 13  # Espaciado entre líneas
    styleN = ParagraphStyle('Justicado', parent=styles['Normal'], alignment=TA_JUSTIFY)

    styleT = styles["Normal"]
    styleT.fontSize = 13
    styleT.fontName = 'Helvetica-Bold'
    styleT.textColor = prussian_blue
    styleT.leading = 17
    styleT = ParagraphStyle('Center', parent=styles['Normal'], alignment= TA_CENTER)"""

    texto = """El objeto del presente escrito es poner en conocimiento, de los proveedores que realizan trabajos para nuestra empresa, 
                los requerimientos mínimos que le sean de aplicación, que debe de cumplir en lo referente a la seguridad y salud en el 
                trabajo, calidad y protección del medio ambiente. La aceptación de una orden de compra implica la responsabilidad por 
                parte del proveedor del conocimiento y aceptación de lo descrito.<br/>Nuestra empresa tiene implantado un SEOV 
                (Sistema de Excelencia Operativa Vordcab), bajo las normas ISO 9001:2015, ISO 14001:2015 e ISO 45001:2018, 
                por lo que se requiere que nuestros proveedores colaboren en el cumplimiento de los siguientes requisitos: <br/>
                """
    
    texto2 = """En todo momento el proveedor está obligado a cumplir con la legislación aplicable al servicio que está prestando.<br/>
El proveedor se compromete a garantizar el cumplimiento de lo solicitado en el pedido u orden de compra del material o del trabajo 
externo.<br/>
El proveedor debería poder garantizar la correcta gestión y control de: los residuos, emisiones atmosféricas, ruidos, 
efluentes residuales, productos peligrosos, afectación del suelo y mantenimiento de instalaciones, respecto al servicio prestado.<br/>
El proveedor deberá aplicar las medidas preventivas necesarias, para evitar situaciones de peligro o emergencia como derrame, fuga, 
incendio, etc., durante la realización del trabajo encomendado. Y si es preciso formar e informar a su personal sobre manipulación, 
almacenaje, uso y riesgos de productos o preparados peligrosos.<br/>
El proveedor deberá facilitar la documentación ambiental y de seguridad que se le solicite o requiera.<br/>
Si el proveedor tiene algún servicio que presta a nuestra empresa subcontratado, por ejemplo, transporte, deberá transmitir este 
documento a su subcontratista.<br/> """
    texto3 = """El proveedor deberá trabajar adoptando buenas prácticas ambientales y cumplir con los procedimientos internos que se 
    le hayan comunicado respecto a HSE y la Prevención de Riesgos Laborales.<br/>
Las empresas que realicen trabajos para nuestra empresa deberán cumplirse los requisitos de seguridad establecidos, uso de EPP, 
protecciones colectivas, formación, seguridad equipos,
medidas preventivas<br/>
Si durante el trabajo se deben retirar residuos peligrosos (aceites, aguas con productos peligrosos, pinturas, disolventes, sus envases)
o /y no peligrosos (escombros, embalajes), se recogerán en recipientes adecuados según la cantidad a retirar. Los recipientes llenos
serán retirados por la empresa que preste el servicio o entregados a nuestra empresa, según convenga, para su correcto almacenamiento 
y gestión posterior.<br/>
Si no sabe qué hacer con algún residuo o efluente residual o cualquier otra cosa, que se ha originado mientras prestaba el servicio,
 avise a la persona que le haya atendido o al Responsable de seguridad. No tomará decisiones.<br/>
Si detecta cualquier situación de riesgo/emergencia (ambiental, personal, de seguridad), lo comunicará de inmediato a cualquier persona
de la empresa o a la que le haya atendido o al Responsable de seguridad. Nunca actué. Deberá seguir las normas de emergencia que se le
 han facilitado a la entrada.<br/>
Si mientras trabaja se produce una situación de emergencia (derrame o fuga de producto peligrosos), y le han facilitado la formación y 
medios necesarios para actuar, proceda según la instrucción que se le ha facilitado, en caso contrario avise de inmediato a cualquier 
persona de la empresa o a la que le ha atendido o al Responsable de seguridad.<br/>"""
    titulo1 = "REQUISITOS OBLIGATORIOS PARA PROVEEDORES DE GRUPO VORDCAB"
    titulo2 = """REQUISITOS GENERALES PARA TODOS LOS PROVEEDORES"""
    titulo3 = """REQUISITOS SI USTED PRESTA EL SERVICIO O PARTE DE SERVICIO DENTRO <br/> 
                DE LAS INSTALACIONES DE GRUPO VORDCAB"""
    
    """titulo1 = Paragraph(titulo1, styleT)
    parrafo = Paragraph(texto, styleN)
    titulo2 = Paragraph(titulo2, styleT)
    parrafo2 = Paragraph(texto2, styleN)
    titulo3 = Paragraph(titulo3, styleT)
    parrafo3 = Paragraph(texto3, styleN)

    ancho, alto = letter  # Asegúrate de tener estas dimensiones definidas
    #frame = Frame(120, 720, ancho - 100, alto - 100, id='frameTextoConstante')  # Ajusta las dimensiones según sea necesario
    elementos = [titulo1, Spacer(1,25), parrafo, Spacer(1,25),titulo2,Spacer(1,25), parrafo2, Spacer(1,25),titulo3,Spacer(1,25), parrafo3]
    frame = Frame(30, 0, width-50, height-100, id='frameTextoConstante')
    frame.addFromList(elementos, c)"""

    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='Carta_Proveedor' + str(proveedor.id) +'.pdf')


def convert_excel_matriz_compras(compras, num_requis_atendidas, num_approved_requis, start_date, end_date):
      #print('si entra a la función')
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Matriz_Compras")

     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})

    columns = ['Compra', 'Requisición', 'Solicitud', 'Proyecto', 'Subproyecto', 'Área', 'Solicitante', 'Creado', 'Req. Autorizada', 'Proveedor',
               'Crédito/Contado', 'Costo', 'Monto Pagado', 'Status Pago', 'Status Autorización', 'Días de entrega', 'Moneda',
               'Tipo de cambio', 'Entregada', "Total en pesos"]

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por Savia Vordcab. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    
    # Escribir encabezados debajo de los mensajes
    worksheet.write(2, columna_max - 1, "Fecha Inicial", head_style)
    worksheet.write(3, columna_max - 1, "Fecha Final", head_style)
    worksheet.write(4, columna_max - 1, "Total de OC's", head_style)
    worksheet.write(5, columna_max - 1, "Requisiciones Aprobadas", head_style)
    worksheet.write(6, columna_max - 1, "Requisiciones Atendidas", head_style)
    worksheet.write(7, columna_max - 1, "KPI Colocadas/Aprobadas", head_style)
    worksheet.write(8, columna_max - 1, "OC Entregadas", head_style)
    worksheet.write(9, columna_max - 1, "OC Autorizadas", head_style)
    worksheet.write(10, columna_max - 1, "KPI OC Entregadas/Total de OC", head_style)
    
    indicador = num_requis_atendidas/num_approved_requis
    letra_columna = xl_col_to_name(columna_max)
    formula = f"={letra_columna}9/{letra_columna}10"
    # Escribir datos y fórmulas
    worksheet.write(2, columna_max, start_date, date_style)  # Ejemplo de escritura de fecha
    worksheet.write(3, columna_max, end_date, date_style)
    worksheet.write_formula(4, columna_max, '=COUNTA(A:A)-1', body_style)  # Ejemplo de fórmula
    worksheet.write(5, columna_max, num_approved_requis, body_style)
    worksheet.write(6, columna_max, num_requis_atendidas, body_style)
    worksheet.write(7, columna_max, indicador, percent_style)  # Ajuste del índice de fila y columna para xlsxwriter
    worksheet.write_formula(8, columna_max, '=COUNTIF(S:S, "Entregada")', body_style)
    # Escribir otra fórmula COUNTIF, también con el estilo corporal
    worksheet.write_formula(9, columna_max, '=COUNTIF(O:O, "Autorizado")', body_style)
    worksheet.write_formula(10, columna_max, formula, percent_style)

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    worksheet.set_column('L:L', 12,  money_style)
    worksheet.set_column('M:M', 12, money_style) 
    # Asumiendo que ya tienes tus datos de compras
    row_num = 0
    for compra_list in compras:
        row_num += 1
        # Aquí asumimos que ya hiciste el procesamiento necesario de cada compra
        pagos = Pago.objects.filter(oc=compra_list)
        tipo_de_cambio_promedio_pagos = pagos.aggregate(Avg('tipo_de_cambio'))['tipo_de_cambio__avg']

        # Usar el tipo de cambio de los pagos, si existe. De lo contrario, usar el tipo de cambio de la compra
        tipo = tipo_de_cambio_promedio_pagos or compra_list.tipo_de_cambio
        tipo_de_cambio = '' if tipo == 0 else tipo
        created_at = compra_list.created_at.replace(tzinfo=None)
        approved_at = compra_list.req.approved_at

        row = [
            compra_list.folio,
            compra_list.req.folio,
            compra_list.req.orden.folio,
            compra_list.req.orden.proyecto.nombre if compra_list.req.orden.proyecto else '',
            compra_list.req.orden.subproyecto.nombre if compra_list.req.orden.subproyecto else '',
            compra_list.req.orden.operacion.nombre if compra_list.req.orden.operacion else '',
            f"{compra_list.req.orden.staff.staff.staff.first_name} {compra_list.req.orden.staff.staff.staff.last_name}",
            created_at,
            approved_at,
            compra_list.proveedor.nombre.razon_social,
            compra_list.cond_de_pago.nombre,
            compra_list.costo_oc,
            compra_list.monto_pagado,
            'Pagada' if compra_list.pagada else 'No Pagada',
            'Autorizado' if compra_list.autorizado2 else 'No Autorizado' if compra_list.autorizado2 == False or compra_list.autorizado1 == False else 'Pendiente Autorización',
            compra_list.dias_de_entrega,
            compra_list.moneda.nombre,
            tipo_de_cambio,  # Asegúrate de que tipo_de_cambio sea un valor que pueda ser escrito directamente
            'Entregada' if compra_list.entrada_completa else 'No Entregada',
        ]
        
        for col_num, cell_value in enumerate(row):
        # Define el formato por defecto
            cell_format = body_style

            # Aplica el formato de fecha para las columnas con fechas
            if col_num in [7, 8]:  # Asume que estas son tus columnas de fechas
                cell_format = date_style
        
            # Aplica el formato de dinero para las columnas con valores monetarios
            elif col_num in [11, 12]:  # Asume que estas son tus columnas de dinero
                cell_format = money_style

            # Finalmente, escribe la celda con el valor y el formato correspondiente
            worksheet.write(row_num, col_num, cell_value, cell_format)

      
        worksheet.write_formula(row_num, 19, f'=IF(ISBLANK(R{row_num+1}), L{row_num+1}, L{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Matriz_compras_{dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response