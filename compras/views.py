from django.shortcuts import render, redirect, get_object_or_404
from .tasks import convert_excel_matriz_compras_task
from django.views.decorators.cache import cache_page
from dashboard.models import Inventario, Order, ArticulosOrdenados, ArticulosparaSurtir
from requisiciones.models import Requis, ArticulosRequisitados
from user.models import Profile
from tesoreria.models import Pago
from user.decorators import perfil_seleccionado_required
from .filters import CompraFilter, ArticulosRequisitadosFilter,  ArticuloCompradoFilter, HistoricalArticuloCompradoFilter
from .models import ArticuloComprado, Compra, Proveedor_direcciones, Cond_pago, Uso_cfdi, Moneda, Comparativo, Item_Comparativo
from tesoreria.models import Facturas
from .forms import CompraForm, ArticuloCompradoForm, ArticulosRequisitadosForm, ComparativoForm, Item_ComparativoForm, Compra_ComentarioForm, UploadFileForm
from requisiciones.forms import Articulo_Cancelado_Form
from tesoreria.forms import Facturas_Form
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
import json
from django.contrib import messages
from datetime import date, datetime, timedelta
from num2words import num2words
from django.core.paginator import Paginator
import decimal
from django.db.models import F, Avg, Value, ExpressionWrapper, fields, Sum, Q
from django.db.models.functions import Concat
from django.utils import timezone
import time
import os


#PDF generator
import io
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter
from reportlab.rl_config import defaultPageSize
from django.http import FileResponse
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
import urllib.request, urllib.parse, urllib.error
from django.core.mail import EmailMessage
# Import Excel Stuff
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
import ssl
# Create your views here.

@login_required(login_url='user-login')
def requisiciones_autorizadas(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)
    if perfil.tipo.compras == True:
        requis = Requis.objects.filter(orden__distrito = perfil.distritos, autorizar=True, colocada=False, complete = True, )
    else:
        requis = Requis.objects.filter(autorizar=True, colocada=False, complete =True)
    #requis = Requis.objects.filter(autorizar=True, colocada=False)

    tag = dof()

     #Set up pagination
    p = Paginator(requis, 50)
    page = request.GET.get('page')
    requis_list = p.get_page(page)

    context= {
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

    context= {
        'requis':requis,
        'articulos':articulos,
        'myfilter':myfilter,
        }

    return render(request, 'compras/productos_pendientes.html',context)

def eliminar_articulos(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
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
                f'Estimado(a) {producto.req.orden.staff.staff.first_name}:\n\nEstás recibiendo este correo porque el producto: {producto.producto.articulos.producto.producto.nombre} de la solicitud: {producto.req.orden.folio} ha sido eliminado, por la siguiente razón: {producto.comentario_cancelacion} \n\n Atte.{perfil.staff.first_name}{perfil.staff.last_name}  \nVORDTEC DE MÉXICO S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                'savia@vordtec.com',
                ['ulises_huesc@hotmail.com',producto.req.orden.staff.staff.email,],
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
 # Determinar el día de la semana
    today = datetime.now()
    day_of_week = today.weekday()

    # Archivo para almacenar el valor del viernes
    valor_viernes_file = 'valor_viernes.txt'

    # Si es sábado (5) o domingo (6), intentar leer el valor del archivo
    if day_of_week in [5, 6]:
        if os.path.exists(valor_viernes_file):
            with open(valor_viernes_file, 'r') as file:
                return file.read() + " (Este valor es del viernes)"
        else:
            return "Valor no disponible"
        
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
    #productos = ArticulosRequisitados.objects.filter(req = pk)
    #req = Requis.objects.get(id = pk)
    usuario = Profile.objects.get(staff__id=request.user.id)
    compras = Compra.objects.filter(regresar_oc = True)
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
    usuario = Profile.objects.get(staff__id=request.user.id)
    oc = Compra.objects.get(id =pk)
    colaborador_sel = Profile.objects.all()
    productos_comp = ArticuloComprado.objects.filter(oc = oc)
    productos = ArticulosRequisitados.objects.filter(req = oc.req, sel_comp = False)
    req = Requis.objects.get(id = oc.req.id)
    proveedores = Proveedor_direcciones.objects.filter(
        Q(estatus__nombre='NUEVO') | Q(estatus__nombre='APROBADO'))
    form_product = ArticuloCompradoForm()
    form = CompraForm(instance=oc)

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
            abrev= usuario.distrito.abreviado
            #oc.folio = str(abrev) + str(consecutivo).zfill(4)
            oc.regresar_oc = False
            form.save()
            oc.save()
            req.save()
            messages.success(request,f'{usuario.staff.first_name}, Has modificado la OC {oc.get_folio} correctamente')
            return redirect('compras-devueltas')



    context= {
        'proveedores':proveedores,
        'productos':productos,
        'form':form,
        'oc':oc,
        'productos_comp':productos_comp,
        'form_product':form_product,
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
    abrev = req.orden.distrito.abreviado
    folio_preview = str(abrev)+ str(folio)
    error_messages = {}

    productos_para_select2 = [
        {'id': producto.id,
         'text': str(producto), 
         'cantidad': str(producto.cantidad), 
         'cantidad_pendiente': str(producto.cantidad_comprada),
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
            messages.success(request,f'{usuario.staff.staff.first_name}, Has generado la OC {oc.folio} correctamente')
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

  
    # Calcular el total de órdenes de compra
    total_de_oc = compras.count()
     # Calcular el número de OC que cumplen el criterio (created_at - approved_at <= 3)
    time_difference = ExpressionWrapper(F('created_at') - F('req__approved_at'), output_field=fields.DurationField())
    compras_con_criterio = compras.annotate(time_difference=time_difference).filter(time_difference__lte=timedelta(days=3))
    oc_cumplen = compras_con_criterio.count()

     # Calcular el indicador de cumplimiento (oc_cumplen / total_de_oc)
    if total_de_oc > 0:
        cumplimiento = (oc_cumplen / total_de_oc)*100
    else:
        cumplimiento = 0

     #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    context= {
        'compras_list':compras_list,
        'compras':compras,
        'myfilter':myfilter,
        'cumplimiento': cumplimiento,
        }

    if request.method == 'POST' and 'btnReporte' in request.POST:
        task = convert_excel_matriz_compras_task.delay(compras_data)
        task_id = task.id
        request.session['task_id'] = task_id
        context['task_id'] = task_id 
        cantidad = compras.count()
        context['cantidad'] = cantidad
        #messages.success(request, f'Tu reporte se está generando {task_id}')
        

    

    return render(request, 'compras/matriz_compras.html',context)


#def generar_reporte(request):
    

from celery.result import AsyncResult

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
    compras = Compra.objects.filter(complete=True)
    articulos = ArticuloComprado.objects.filter(oc__complete = True).order_by('-oc__created_at')
    myfilter = ArticuloCompradoFilter(request.GET, queryset=articulos)
    articulos = myfilter.qs

    #fecha_un_anno = datetime.today() - timedelta(days=450)
    #filter(created_at__gte = fecha_un_anno).
    productos_optimized = articulos.select_related(
        'oc__req__orden__staff__staff__staff',
        'oc__req__orden',
        'oc__req__orden__proyecto',
        'oc__req__orden__subproyecto',
        'oc__req__orden__operacion',
        'oc__proveedor__nombre',
        'producto__producto__articulos__producto__producto'
    ).only(
        'oc__folio',
        'oc__req__folio',
        'oc__req__orden__folio',
        'oc__req__orden__staff__staff__staff__first_name',
        'oc__req__orden__staff__staff__staff__last_name',
        'oc__req__orden__proyecto__nombre',
        'oc__req__orden__subproyecto__nombre',
        'created_at',
        'oc__proveedor__nombre__razon_social',
        'oc__req__orden__operacion__nombre',
        'cantidad',
        'producto__producto__articulos__producto__producto__codigo',
        'producto__producto__articulos__producto__producto__nombre',
        'precio_unitario',
        #'subtotal_parcial',
        #'iva_parcial',
        #'total'
    )
    
    #Set up pagination
    p = Paginator(articulos, 50)
    page = request.GET.get('page')
    articulos_list = p.get_page(page)

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_solicitud_matriz_productos(productos_optimized)

    context= {
        'articulos_list':articulos_list,
        'articulos':articulos,
        'compras':compras,
        'myfilter':myfilter,
        }

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

@login_required(login_url='user-login')
def autorizacion_oc1(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    if usuario.tipo.oc_superintendencia == True:
        compras = Compra.objects.filter(complete=True, autorizado1= None).order_by('-folio')
    else:
        compras = Compra.objects.filter(flete=True,costo_fletes='1')
    #compras = Compra.objects.filter(complete=True, autorizado1= None).order_by('-folio')



    context= {
        'compras':compras,
        }

    return render(request, 'compras/autorizacion_oc1.html',context)

def cancelar_oc1(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
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
    costo_total = costo_fletes + costo_oc
    resta = compra.req.orden.subproyecto.presupuesto - costo_total - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)

    if request.method == 'POST':
        compra.oc_autorizada_por = usuario
        compra.autorizado1 = False
        compra.autorizado_date1 = date.today()
        compra.autorizado_hora1 = datetime.now().time()
        compra.save()
        messages.error(request,f'Has cancelado la compra con FOLIO: {compra.get_folio}')
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
    usuario = Profile.objects.get(staff__id=request.user.id)
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
    perfil = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc = pk)
    #Traigo la requisición para poderla activar de nuevo
    requi = Requis.objects.get(id=compra.req.id)

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

    form = Compra_ComentarioForm()

    if request.method == 'POST':
        form = Compra_ComentarioForm(request.POST, instance=compra)
        if form.is_valid():
            compra = form.save(commit = False)
            if not compra.autorizado1:
                compra.oc_autorizada_por = perfil
                compra.autorizado1 = None
                compra.complete = False
                compra.autorizado_date1 = date.today()
                compra.autorizado_hora1 = datetime.now().time()
                compra.regresar_oc = True
            else:
                compra.oc_autorizada_por2 = perfil
                compra.autorizado2 = None
                compra.autorizado1 = None
                compra.complete = False
                compra.autorizado_date2 = date.today()
                compra.autorizado_hora2 = datetime.now().time()
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
    usuario = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc=pk)

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
    resta = compra.req.orden.subproyecto.presupuesto - costo_oc - costo_fletes - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)


    if request.method == 'POST':
        compra.autorizado1 = True
        compra.oc_autorizada_por = usuario
        compra.autorizado_date1 = date.today()
        compra.autorizado_hora1 = datetime.now().time()
        compra.save()
        messages.success(request, f'{usuario.staff.first_name} has autorizado la solicitud {compra.get_folio}')
        return redirect('autorizacion-oc1')

    context={
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
    usuario = Profile.objects.get(staff__id=request.user.id)
    #if usuario.tipo.oc_gerencia == True:
    #    compras = Compra.objects.filter(complete = True, autorizado1 = True, autorizado2= None).order_by('-folio')
    #else:
    #    compras = Compra.objects.filter(flete=True,costo_fletes='1')
    compras = Compra.objects.filter(complete = True, autorizado1 = True, autorizado2= None).order_by('-folio')

    context= {
        'compras':compras,
        }

    return render(request, 'compras/autorizacion_oc2.html',context)


def autorizar_oc2(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id = pk)
    productos = ArticuloComprado.objects.filter(oc=pk)

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
    resta = compra.req.orden.subproyecto.presupuesto - costo_oc - costo_fletes - compra.req.orden.subproyecto.gastado
    porcentaje = "{0:.2f}%".format((costo_oc/compra.req.orden.subproyecto.presupuesto)*100)

    if request.method == 'POST':
        compra.autorizado2 = True
        compra.oc_autorizada_por2 = usuario
        compra.autorizado_date2 = date.today()
        compra.autorizado_hora2 = datetime.now().time()
        compra.save()
        if compra.cond_de_pago.nombre == "CREDITO":
            archivo_oc = attach_oc_pdf(request, compra.id)
            email = EmailMessage(
                f'Compra Autorizada {compra.get_folio}',
                f'Estimado(a) {compra.proveedor.contacto} | Proveedor {compra.proveedor.nombre}:\n\nEstás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.get_folio}.\n\n Atte. {compra.creada_por.staff.first_name} {compra.creada_por.staff.last_name} \nVORDTEC DE MÉXICO S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                'savia@vordtec.com',
                ['ulises_huesc@hotmail.com','lizeth.ojeda@vordtec.com','osiris.bautista@vordtec.com',compra.proveedor.email,'ulises_huesc@hotmail.com'],  #compra.proveedor.email,
                )
            email.attach(f'folio:{compra.get_folio}.pdf',archivo_oc,'application/pdf')
            email.send()
            for producto in productos:
                if producto.producto.producto.articulos.producto.producto.especialista == True:
                    archivo_oc = attach_oc_pdf(request, compra.id)
                    email = EmailMessage(
                        f'Compra Autorizada {compra.get_folio}',
                        f'Estimado proveedor,\n Estás recibiendo este correo porque ha sido aprobada una OC que contiene el producto código:{producto.producto.producto.articulos.producto.producto.codigo} descripción:{producto.producto.producto.articulos.producto.producto.nombre} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA X',
                        'savia@vordtec.com',
                        ['ulises_huesc@hotmail.com'],
                        )
                    email.attach(f'folio:{compra.get_folio}.pdf',archivo_oc,'application/pdf')
                    email.send()
        messages.success(request, f'{usuario.staff.first_name} has autorizado la solicitud {compra.get_folio}')

        return redirect('autorizacion-oc2')

    context={
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
            # Manejar múltiples archivos
            
            
            #for i, file in enumerate(files):
            #    field_name = f'cotizacion{i+1}'
            #    if hasattr(comparativo, field_name):
            #        handle_uploaded_file(file, comparativo, field_name)
            #       
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

def carga_proveedor(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    term = request.GET.get('term')
    proveedores = Proveedor_direcciones.objects.filter(distrito = usuario.distritos, nombre__razon_social__icontains = term).values('id','nombre__razon_social','distrito__nombre','domicilio','estatus__nombre')
    data = list(proveedores)
        
    return JsonResponse(data, safe=False)
    
    
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
    return FileResponse(buf, as_attachment=True, filename='oc_' + str(compra.id) + '.pdf')

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



    c.drawString(420,caja_iso,'Preparado por:')
    c.drawString(420,caja_iso-10,'SUP. ADMON')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(520,caja_iso-10,'SUB ADM')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'F-ADQ-N4-01.02')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'1-Sep.-18')

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
    c.drawInlineImage('static/images/logo vordtec_documento.png',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

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

    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_proveedor-20,'FOLIO:')

    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_proveedor-20, compra.get_folio)

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
        c.drawString(100,caja_proveedor-20, compra.deposito_comprador.staff.first_name+' '+compra.deposito_comprador.staff.last_name)
    else:
        c.drawString(100,caja_proveedor-20, compra.proveedor.nombre.razon_social)
    c.drawString(100,caja_proveedor-40, compra.proveedor.nombre.rfc)
    c.drawString(100,caja_proveedor-60, compra.uso_del_cfdi.descripcion)
    c.drawString(100,caja_proveedor-80, compra.req.orden.staff.staff.first_name +' '+ compra.req.orden.staff.staff.last_name)
    c.drawString(100,caja_proveedor-100, compra.created_at.strftime("%d/%m/%Y"))
    c.drawString(100,caja_proveedor-120, compra.proveedor.estatus.nombre)
    if compra.dias_de_entrega:
        c.drawString(110,caja_proveedor-140, str(compra.dias_de_entrega)+' '+'días hábiles')



    c.drawString(inicio_central + 90,caja_proveedor-35, str(compra.req.id))
    c.drawString(inicio_central + 90,caja_proveedor-95, 'tesoreria.planta@vordtec.com')
    if compra.proveedor.nombre.razon_social == 'COLABORADOR':
        c.drawString(inicio_central + 90,caja_proveedor-115, compra.deposito_comprador.banco.nombre)
        c.drawString(inicio_central + 90,caja_proveedor-135, compra.deposito_comprador.cuenta_bancaria)
        c.drawString(inicio_central + 90,caja_proveedor-155, compra.deposito_comprador.clabe)
    else:
        c.drawString(inicio_central + 90,caja_proveedor-115, compra.proveedor.banco.nombre)
        c.drawString(inicio_central + 90,caja_proveedor-135, compra.proveedor.cuenta)
        c.drawString(inicio_central + 90,caja_proveedor-155, compra.proveedor.clabe)




    if compra.cond_de_pago.nombre == "CREDITO":
        c.drawString(inicio_central + 90,caja_proveedor-55, compra.cond_de_pago.nombre + '  ' + str(compra.dias_de_credito) + 'días')
    else:
        c.drawString(inicio_central + 90,caja_proveedor-55, compra.cond_de_pago.nombre )


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
    c.drawCentredString(50,205,'Proyecto')
    c.drawCentredString(110,205,'Subproyecto')
    c.drawCentredString(230,205,'Elaboró')
    c.drawCentredString(325,205,'Moneda')
    c.setFont('Helvetica',8)
    c.setFillColor(black)
    c.drawCentredString(50,190,compra.req.orden.proyecto.nombre)
    c.drawCentredString(110,190,compra.req.orden.subproyecto.nombre)
    c.drawCentredString(230,190,compra.creada_por.staff.first_name + ' ' +compra.creada_por.staff.last_name)
    c.drawCentredString(325,190,compra.moneda.nombre)

    c.setLineWidth(.3)
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
    c.line(135,90,215,90 ) #Linea de Autorizacion
    c.line(350,90,430,90)
    c.drawCentredString(175,70,'Autorización')
    c.drawCentredString(390,70,'Autorización')

    c.drawCentredString(175,80,'Superintendente Administrativo')
    c.drawCentredString(390,80,'Gerencia Zona')
    if compra.autorizado1:
        c.drawCentredString(175,90,compra.oc_autorizada_por.staff.first_name + ' ' +compra.oc_autorizada_por.staff.last_name)
    if compra.autorizado2:
        c.drawCentredString(390,90,compra.oc_autorizada_por2.staff.first_name + ' ' + compra.oc_autorizada_por2.staff.last_name)

    c.setFont('Helvetica',10)
    subtotal = compra.costo_oc - compra.costo_iva
    c.drawRightString(montos_align + 90,210,'$ ' + str(subtotal))
    c.drawRightString(montos_align + 90,200,'$ ' + str(compra.costo_iva))
    c.drawRightString(montos_align + 90,190,'$ ' + str(compra.costo_oc))
    if compra.costo_fletes is None:
        compra.costo_fletes = 0

    c.drawRightString(montos_align + 90,180,'$ ' + str(compra.costo_fletes))
    c.setFillColor(prussian_blue)

    if compra.impuesto:
        c.setFillColor(black)
        c.setFont('Helvetica-Bold',9)
        c.drawRightString(montos_align,170,'Impuestos Adicionales:')
        c.setFont('Helvetica',10)
        c.drawRightString(montos_align + 90,170,'$ ' + str(compra.impuestos_adicionales))
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
        c.drawInlineImage('static/images/logo vordtec_documento.png', 45, 730, 3 * cm, 1.5 * cm)  # Imagen vortec

    c.save()
    buf.seek(0)
    return buf


    

def convert_excel_solicitud_matriz_productos(productos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Solicitudes_por_producto_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Compras_Producto')
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

    columns = ['OC','RQ','Sol','Solicitante','Proyecto','Subproyecto','Fecha','Proveedor','Área','Cantidad','Código', 'Producto','P.U.','Moneda','Tipo de Cambio','Subtotal','IVA','Total']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 4 or col_num == 7:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25
        if col_num == 11:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30



    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia Vordtec. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20
    
    
    rows = []
    for producto in productos:
        # Extract the needed attributes
        compra_id = producto.oc.id
        moneda_nombre = producto.oc.moneda.nombre
        nombre_completo = producto.oc.req.orden.staff.staff.staff.first_name + " " + producto.oc.req.orden.staff.staff.staff.last_name
        proyecto_nombre = producto.oc.req.orden.proyecto.nombre if producto.oc.req.orden.proyecto else "Desconocido"
        subproyecto_nombre = producto.oc.req.orden.subproyecto.nombre if producto.oc.req.orden.subproyecto else "Desconocido"
        operacion_nombre = producto.oc.req.orden.operacion.nombre if producto.oc.req.orden.operacion else "Desconocido"
        fecha_creacion = producto.created_at.astimezone(timezone.utc).replace(tzinfo=None)

        # Calculate total, subtotal, and IVA using attributes from producto
        subtotal_parcial = producto.subtotal_parcial
        iva_parcial = producto.iva_parcial
        total = producto.total
        
        # Handling the currency conversion logic
        pagos = Pago.objects.filter(oc_id=compra_id)
        tipo_de_cambio_promedio_pagos = pagos.aggregate(Avg('tipo_de_cambio'))['tipo_de_cambio__avg']
        tipo_de_cambio = tipo_de_cambio_promedio_pagos or producto.oc.tipo_de_cambio

        if moneda_nombre == "DOLARES" and tipo_de_cambio:
            total = total * tipo_de_cambio

        # Constructing the row
        row = [
            producto.oc.folio,
            producto.oc.req.folio,
            producto.oc.req.orden.folio,
            nombre_completo,
            proyecto_nombre,
            subproyecto_nombre,
            fecha_creacion,
            producto.oc.proveedor.nombre.razon_social,
            operacion_nombre,
            producto.cantidad,
            producto.producto.producto.articulos.producto.producto.codigo,
            producto.producto.producto.articulos.producto.producto.nombre,
            producto.precio_unitario,
            moneda_nombre,
            tipo_de_cambio,
            subtotal_parcial,
            iva_parcial,
            total
        ]
        rows.append(row)

    #Ahora, iteramos sobre las filas recopiladas para construir el archivo Excel:
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = body_style
            if col_num in [12, 14, 15, 16, 17]:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style

    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

