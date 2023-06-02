from django.shortcuts import render, redirect
from dashboard.models import Inventario, Order, ArticulosOrdenados, ArticulosparaSurtir
from requisiciones.models import Requis, ArticulosRequisitados
from user.models import Profile
from tesoreria.models import Pago
from .filters import CompraFilter, ArticulosRequisitadosFilter,  ArticuloCompradoFilter
from .models import ArticuloComprado, Compra, Proveedor_direcciones, Cond_credito, Uso_cfdi, Moneda
from tesoreria.models import Facturas
from .forms import CompraForm, ArticuloCompradoForm, ArticulosRequisitadosForm
from requisiciones.forms import Articulo_Cancelado_Form
from tesoreria.forms import Facturas_Form
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
from django.contrib import messages
from datetime import date, datetime
from num2words import num2words
from django.core.paginator import Paginator
import decimal
from django.db.models import F
#PDF generator
import io
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter
from django.http import FileResponse
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
import urllib.request, urllib.parse, urllib.error
from django.core.mail import EmailMessage
# Import Excel Stuff
from django.db.models.functions import Concat
from django.db.models import Value
from django.contrib import messages
from django.db.models import Sum
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
    perfil = Profile.objects.get(staff__id=request.user.id)
    if perfil.tipo.compras == True:
        requis = Requis.objects.filter(autorizar=True, colocada=False)
    else:
        requis = Requis.objects.filter(complete=None)
    #requis = Requis.objects.filter(autorizar=True, colocada=False)

    tag = dof()

    context= {
        'requis':requis,
        'tags':tag,
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
            conteo_productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"), cancelado=False).count()
            if conteo_productos == 0:
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
    productos = ArticulosRequisitados.objects.filter(req = pk, cantidad_comprada__lt = F("cantidad"))
    requis = Requis.objects.get(id = pk)

    context = {
        'productos': productos,
        'requis': requis,
        }

    return render(request,'compras/articulos_restantes.html', context)

def dof():
#Trying to fetch DOF
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
    proveedores = Proveedor_direcciones.objects.filter(estatus__nombre='APROBADO')
    form_product = ArticuloCompradoForm()
    form = CompraForm(instance=oc)

    tag = dof()
    subtotal = 0
    iva = 0
    total = 0
    dif_cant = 0
    form.fields['deposito_comprador'].queryset = colaborador_sel
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
        requisitados = ArticulosRequisitados.objects.filter(req = pk)
        cuenta_art_comprados = requisitados.filter(art_surtido = True).count()
        cuenta_art_totales = requisitados.count()
        if cuenta_art_totales == cuenta_art_comprados:
            req.colocada = True
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
        }

    return render(request, 'compras/compra_edicion.html',context)



def update_oc(request):
    data= json.loads(request.body)
    action = data["action"]
    cantidad = data["val_cantidad"]
    producto_id = data["id"]
    productos = ArticulosRequisitados.objects.get(id=producto_id)
    pk = data["oc"]
    precio = data["val_precio"]
    oc = Compra.objects.get(id=pk)
    if action == "add":
        cantidad_total = productos.cantidad_comprada + decimal.Decimal(cantidad)
        if cantidad_total > productos.cantidad:
            messages.error(request,f'La cantidad que se quiere comprar sobrepasa la cantidad requisitada {cantidad_total} mayor que {productos.cantidad}')
        else:
            comp_item, created = ArticuloComprado.objects.get_or_create(oc=oc, producto=productos)
            productos.cantidad_comprada = productos.cantidad_comprada + decimal.Decimal(cantidad)
            messages.success(request,f'Estos son los productos comprados ahora {productos.cantidad_comprada}')
            if productos.cantidad_comprada == productos.cantidad:
                productos.art_surtido = True
            if comp_item.cantidad == None:
                comp_item.cantidad = 0
            comp_item.cantidad = comp_item.cantidad + decimal.Decimal(cantidad)
            comp_item.precio_unitario = precio
            productos.sel_comp = True
            comp_item.save()
            productos.save()
    if action == "remove":
        comp_item = ArticuloComprado.objects.get(oc = oc, producto = productos)
        productos.art_surtido = False
        productos.sel_comp = False
        productos.cantidad_comprada = productos.cantidad_comprada - comp_item.cantidad
        productos.save()
        comp_item.delete()

    return JsonResponse('Item updated, action executed: '+data["action"], safe=False)

def oc_modal(request, pk):
    productos = ArticulosRequisitados.objects.filter(req = pk, sel_comp = False)
    req = Requis.objects.get(id = pk)
    proveedores = Proveedor_direcciones.objects.filter(estatus__nombre='APROBADO')
    usuario = Profile.objects.get(staff__id=request.user.id)
    colaborador_sel = Profile.objects.all()
    compras = Compra.objects.all()
    oc, created = Compra.objects.get_or_create(complete = False, req = req, creada_por = usuario)
    #consecutivo = compras.count() + 1
    productos_comp = ArticuloComprado.objects.filter(oc=oc)
    form_product = ArticuloCompradoForm()
    form = CompraForm(instance=oc)
    tag = dof()
    subtotal = 0
    iva = 0
    total = 0
    dif_cant = 0
    form.fields['deposito_comprador'].queryset = colaborador_sel
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
        requisitados = ArticulosRequisitados.objects.filter(req = pk)
        cuenta_art_comprados = requisitados.filter(art_surtido = True).count()
        cuenta_art_totales = requisitados.count()
        if cuenta_art_totales == cuenta_art_comprados:
            req.colocada = True
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
            form.save()
            oc.save()
            req.save()
            messages.success(request,f'{usuario.staff.first_name}, Has generado la OC {oc.folio} correctamente')
            return redirect('requisicion-autorizada')


    context= {
        'proveedores':proveedores,
        'req':req,
        'form':form,
        'oc':oc,
        'productos':productos,
        'form_product':form_product,
        'tag':tag,
        'productos_comp':productos_comp,
        'subtotal':subtotal,
        'iva':iva,
        'total':total,
        'colaborador_sel':colaborador_sel,
        }
    return render(request, 'compras/oc.html',context)


@login_required(login_url='user-login')
def matriz_oc(request):
    compras = Compra.objects.filter(complete=True)
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

     #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    if request.method == 'POST' and 'btnReporte' in request.POST:
        return convert_excel_matriz_compras(compras)

    context= {
        'compras_list':compras_list,
        'compras':compras,
        'myfilter':myfilter,
        }

    return render(request, 'compras/matriz_compras.html',context)

@login_required(login_url='user-login')
def matriz_oc_productos(request):
    compras = Compra.objects.filter(complete=True)
    articulos = ArticuloComprado.objects.filter(oc__complete = True)
    myfilter = ArticuloCompradoFilter(request.GET, queryset=articulos)
    articulos = myfilter.qs

    #Set up pagination
    p = Paginator(articulos, 50)
    page = request.GET.get('page')
    articulos_list = p.get_page(page)

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_solicitud_matriz_productos(articulos)

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
    usuario = request.user.id
    perfil = Profile.objects.get(id=usuario)
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
        compra.autorizada1_por = perfil
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
    usuario = request.user.id
    perfil = Profile.objects.get(id=usuario)
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
        compra.autorizada2_por = perfil
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
    usuario = request.user.id
    perfil = Profile.objects.get(id=usuario)
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

    if request.method == 'POST':
        if not compra.autorizado1:
            compra.autorizada1_por = perfil
            compra.autorizada1 = None
            compra.complete = False
            compra.autorizada_date1 = date.today()
            compra.autorizada_hora2 = datetime.now().time()
        else:
            compra.autorizada2_por = perfil
            compra.autorizado2 = None
            compra.autorizado1 = None
            compra.complete = False
            compra.autorizado_date2 = date.today()
            compra.autorizado_hora2 = datetime.now().time()
        #Esta línea es la que activa a la requi
        requi.colocada = False
        compra.save()
        requi.save()
        messages.error(request,f'Has regresado la compra con FOLIO: {compra.get_folio} y ahora podrás encontrar esos productos en la requisición {requi.folio}')
        return redirect('requisicion-autorizada')

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
        compra.autorizado_time2 = datetime.now().time()
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

def render_oc_pdf(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #doc = SimpleDocTemplate(buf, pagesize=letter)
    #Here ends conf.
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=pk)

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
        data.append([producto.producto.producto.articulos.producto.producto.codigo, producto.producto.producto.articulos.producto.producto.nombre,producto.cantidad, producto.producto.producto.articulos.producto.producto.unidad, producto.precio_unitario, producto.precio_unitario * producto.cantidad])
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
    c.drawRightString(montos_align,170,'Total:')
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
    c.drawRightString(montos_align + 90,210,str(subtotal))
    c.drawRightString(montos_align + 90,200,str(compra.costo_iva))
    c.drawRightString(montos_align + 90,190,str(compra.costo_oc))
    if compra.costo_fletes is None:
        compra.costo_fletes = 0

    c.drawRightString(montos_align + 90,180,str(compra.costo_fletes))
    c.setFillColor(prussian_blue)

    if compra.impuesto:
        c.setFillColor(black)
        c.setFont('Helvetica-Bold',9)
        c.drawRightString(montos_align,170,'Impuestos Adicionales:')
        c.setFont('Helvetica',10)
        c.drawRightString(montos_align + 90,170,str(compra.impuestos_adicionales))

    c.drawRightString(montos_align + 90,160,str(compra.costo_plus_adicionales))
    c.setFont('Helvetica', 9)
    if compra.moneda.nombre == "PESOS":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='es_CO', to='currency'))
    if compra.moneda.nombre == "DOLARES":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='en', to='currency'))

    c.setFillColor(black)
    if compra.opciones_condiciones is not None:
        c.drawString(130,130,compra.opciones_condiciones)
    else:
        c.drawString(150,high-200,"NA")

    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)

    width, height = letter
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
    return FileResponse(buf, as_attachment=True, filename='oc_'+str(compra.id) +'.pdf')

def attach_oc_pdf(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=pk)



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


    #c.drawString(460,735,'Folio: ')
    #c.drawString(270,735,'Fecha:')


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
        data.append([producto.producto.producto.articulos.producto.producto.codigo, producto.producto.producto.articulos.producto.producto.nombre,producto.cantidad, producto.producto.producto.articulos.producto.producto.unidad, producto.precio_unitario, producto.precio_unitario * producto.cantidad])
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
    c.drawRightString(montos_align,170,'Total:')
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
    c.drawRightString(montos_align + 90,210,str(subtotal))
    c.drawRightString(montos_align + 90,200,str(compra.costo_iva))
    c.drawRightString(montos_align + 90,190,str(compra.costo_oc))
    if compra.costo_fletes is None:
        compra.costo_fletes = 0
    c.drawRightString(montos_align + 90,180,str(compra.costo_fletes))
    c.setFillColor(prussian_blue)


    if compra.impuesto:
        c.setFillColor(black)
        c.setFont('Helvetica-Bold',9)
        c.drawRightString(montos_align,170,'Impuestos Adicionales:')
        c.setFont('Helvetica',10)
        c.drawRightString(montos_align + 90,170,str(compra.impuestos_adicionales))

    c.drawRightString(montos_align + 90,160,str(compra.costo_plus_adicionales))
    c.setFont('Helvetica', 9)
    if compra.moneda.nombre == "PESOS":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='es_CO', to='currency'))
    if compra.moneda.nombre == "DOLARES":
        c.drawString(80,140, num2words(compra.costo_plus_adicionales, lang='en', to='currency'))


    c.setFillColor(black)
    if compra.opciones_condiciones is not None:
        c.drawString(130,130,compra.opciones_condiciones)
    else:
        c.drawString(150,130,"NA")

    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)

    width, height = letter
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
    c.showPage()
    buf.seek(0)
    return buf.getvalue()

def convert_excel_matriz_compras(compras):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Matriz_compras_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Solicitudes')
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

    columns = ['Compra','Requisición','Solicitud','Solicitante','Proyecto','Subproyecto','Área','Creado','Req. Autorizada','Proveedor','Costo','Status Pago','Status Autorización','Días de entrega']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia Vordtec. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20

    rows = compras.values_list('id','req__folio','req__orden__folio','req__orden__proyecto__nombre','req__orden__subproyecto__nombre',
                               'req__orden__area__nombre', Concat('req__orden__staff__staff__first_name',Value(' '),'req__orden__staff__staff__last_name'),
                               'created_at','req__approved_at','proveedor__nombre__razon_social','costo_oc','pagada','autorizado2','dias_de_entrega')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 8 or col_num == 7:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 10 or col_num == 11 or col_num == 12:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

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

    columns = ['OC','RQ','Sol','Solicitante','Proyecto','Subproyecto','Área','Cantidad','Código', 'Producto','P.U.','Cantidad','Subtotal','IVA','Total']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 4 or col_num == 7:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25



    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia Vordtec. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20

    rows = productos.values_list('oc','oc__req','oc__req__orden', Concat('oc__req__orden__staff__staff__first_name',Value(' '),'oc__req__orden__staff__staff__last_name'),
                                'oc__req__orden__proyecto__nombre','oc__req__orden__subproyecto__nombre', 'oc__req__orden__area__nombre','cantidad','producto__producto__articulos__producto__producto__codigo',
                                'producto__producto__articulos__producto__producto__nombre','precio_unitario','cantidad')

    subtotales = [producto.subtotal_parcial for producto in productos]
    ivas = [producto.iva_parcial for producto in productos]
    totales = [producto.total for producto in productos]

    for row, subtotal, iva, total in zip(rows,subtotales, ivas, totales):
        row_num += 1
        row_with_additional_columns = list(row) + [subtotal, iva, total]  # Agrega el subtotal a la fila existente
        for col_num in range(len(row_with_additional_columns)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row_with_additional_columns[col_num]))).style = body_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row_with_additional_columns[col_num])).style = body_style
            if col_num == 10 or col_num == 12 or col_num == 13 or col_num == 14:
                (ws.cell(row = row_num, column = col_num+1, value=row_with_additional_columns[col_num])).style = money_style
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)