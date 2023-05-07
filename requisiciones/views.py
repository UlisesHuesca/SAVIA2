from django.shortcuts import render, redirect
from solicitudes.models import Proyecto, Subproyecto
from dashboard.models import Inventario, Order, ArticulosparaSurtir, ArticulosOrdenados, Inventario_Batch, Product, Marca
from dashboard.forms import  Inventario_BatchForm
from user.models import Profile, User
from .models import ArticulosRequisitados, Requis
from entradas.models import Entrada, EntradaArticulo
from requisiciones.models import Salidas, ValeSalidas
from django.contrib.auth.decorators import login_required
from .filters import ArticulosparaSurtirFilter, SalidasFilter, EntradasFilter
from .forms import SalidasForm, ArticulosRequisitadosForm, ValeSalidasForm, ValeSalidasProyForm, RequisForm, Rechazo_Requi_Form
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt
from datetime import date, datetime
from django.db.models.functions import Concat
from django.db.models import Value, Sum
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import EmailMessage
import json
import csv
from django.core.paginator import Paginator
import ast # Para leer el csr many to many

#PDF generator
import io
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from django.http import FileResponse
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.db.models import Q

# Create your views here.
@login_required(login_url='user-login')
def liberar_stock(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    orden = Order.objects.get(id = pk)
    productos= ArticulosparaSurtir.objects.filter(articulos__orden = orden, surtir=True)
    vale_salida, created = ValeSalidas.objects.get_or_create(almacenista = usuario,complete = False,solicitud=orden)
    salidas = Salidas.objects.filter(vale_salida = vale_salida)
    cantidad_items = salidas.count()
    proyectos = Proyecto.objects.filter(activo=True)
    subproyectos = Subproyecto.objects.all()


    formVale = ValeSalidasProyForm()
    form = SalidasForm()
    users = Profile.objects.all()

    if request.method == 'POST':
        formVale = ValeSalidasProyForm(request.POST, instance=vale_salida)
        vale = formVale.save(commit=False)
        vale.complete = True
        for producto in productos:
            if producto.cantidad == 0:
                producto.salida = True
                producto.surtir = False
                producto.save()
        if formVale.is_valid():
            formVale.save()
            messages.success(request,'La salida se ha generado de manera exitosa')
            return redirect('solicitud-autorizada')

    context= {
        'proyectos':proyectos,
        'subproyectos':subproyectos,
        'productos':productos,
        'orden':orden,
        'form':form,
        'formVale':formVale,
        'users': users,
        'vale_salida':vale_salida,
        'cantidad_items':cantidad_items,
        'salidas':salidas,
        }
    return render(request,'requisiciones/liberar_stock.html',context)



@login_required(login_url='user-login')
def solicitud_autorizada(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    #productos= Requis.objects.filter(complete=True, autorizar=None)
    #Aquí aparecen todas las ordenes, es decir sería el filtro para administrador, el objeto Q no tiene propiedad conmutativa
    #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(requisitar=True), articulos__orden__autorizar = True )

    #if usuario.tipo.superintendente == True:
        #productos= Requis.objects.filter(complete=True, autorizar=None, orden__superintendente=usuario)
    if usuario.tipo.almacen == True:
        #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(surtir=True), articulos__orden__autorizar = True)
        #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(surtir=True), articulos__orden__autorizar = True, articulos__orden__tipo__tipo = "normal")
        productos= ArticulosparaSurtir.objects.filter(surtir=True, articulos__orden__autorizar = True, articulos__orden__tipo__tipo = "normal")
    #else:
        #productos = Requis.objects.filter(complete=None)
    myfilter = ArticulosparaSurtirFilter(request.GET, queryset=productos)
    productos = myfilter.qs
    #Here is where call a function to generate XLSX, using Openpyxl library

    #Set up pagination
    p = Paginator(productos, 20)
    page = request.GET.get('page')
    productos_list = p.get_page(page)


    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_solicitud_autorizada_to_xls(productos)


    context= {
        'productos':productos,
        'productos_list':productos_list,
        'myfilter':myfilter,
        'usuario':usuario,
        }
    return render(request, 'requisiciones/solicitudes_autorizadas.html',context)

@login_required(login_url='user-login')
def solicitudes_autorizadas_pendientes(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    #productos= Requis.objects.filter(complete=True, autorizar=None)
    #Aquí aparecen todas las ordenes, es decir sería el filtro para administrador, el objeto Q no tiene propiedad conmutativa
    #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(requisitar=True), articulos__orden__autorizar = True )

    #if usuario.tipo.superintendente == True:
        #productos= Requis.objects.filter(complete=True, autorizar=None, orden__superintendente=usuario)
    if usuario.tipo.almacenista == True:
        #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(surtir=True), articulos__orden__autorizar = True)
        #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(surtir=True), articulos__orden__autorizar = True, articulos__orden__tipo__tipo = "normal")
        productos= ArticulosparaSurtir.objects.filter(salida=False, surtir=False, articulos__orden__autorizar = True, articulos__orden__tipo__tipo = "normal")

    #else:
        #productos = Requis.objects.filter(complete=None)
    myfilter = ArticulosparaSurtirFilter(request.GET, queryset=productos)
    productos = myfilter.qs

    #Set up pagination
    p = Paginator(productos, 20)
    page = request.GET.get('page')
    productos_list = p.get_page(page)

    #Here is where call a function to generate XLSX, using Openpyxl library

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_solicitud_autorizada_to_xls(productos)


    context= {
        'productos_list':productos_list,
        'productos':productos,
        'myfilter':myfilter,
        'usuario':usuario,
        }
    return render(request, 'requisiciones/solicitudes_autorizadas_no_surtidas.html',context)


def update_salida(request):
    data= json.loads(request.body)
    action = data["action"]
    cantidad = int(data["val_cantidad"])
    salida = data["salida"]
    producto_id = data["id"]
    id_salida =data["id_salida"]
    producto = ArticulosparaSurtir.objects.get(id = producto_id)
    vale_salida = ValeSalidas.objects.get(id = salida)
    inv_del_producto = Inventario.objects.get(producto = producto.articulos.producto.producto)
    entradas = EntradaArticulo.objects.filter(articulo_comprado__producto__producto = producto, agotado=False, entrada__oc__req__orden= producto.articulos.orden).aggregate(cantidad_surtir=Sum('cantidad_por_surtir'))
    suma_entradas = entradas['cantidad_surtir']
    #Si no existen entradas la suma_entradas es igual a None, lo convierto en 0 para que pueda pasar la condicional #Definitoria
    if suma_entradas == None:
        suma_entradas = 0

    if action == "add":
        cantidad_total = producto.cantidad - cantidad
        if cantidad_total < 0 and inv_del_producto.cantidad > 0:
            cantidad_total = inv_del_producto.cantidad - cantidad
        if cantidad_total < 0:
            messages.error(request,f'La cantidad que se quiere egresar sobrepasa la cantidad disponible. {cantidad_total} mayor que {producto.cantidad}')
        else:
            salida, created = Salidas.objects.get_or_create(producto=producto, vale_salida = vale_salida, complete=False)
            producto.seleccionado = True
            if inv_del_producto.cantidad_apartada > inv_del_producto.cantidad_entradas and suma_entradas <= 0: #Definitoria or inv_del_producto.cantidad_apartada >0:
                #Voy a crear un vale de salida con producto salida desde al apartado, lo voy a mandar a llamar aqui, si existe, entonces no hay ni resurtimiento ni salidas derivadas de entradas, solo salidas derivadas de inventario
                try:
                    EntradaArticulo.objects.get(articulo_comprado__producto__producto__articulos__producto = inv_del_producto, articulo_comprado__producto__producto__articulos__orden__tipo__tipo = 'resurtimiento')
                except EntradaArticulo.DoesNotExist:
                    entrada_res = None
                else:
                    entrada_res = EntradaArticulo.objects.get(articulo_comprado__producto__producto__articulos__producto = inv_del_producto, articulo_comprado__producto__producto__articulos__orden__tipo__tipo = 'resurtimiento')

                salida.cantidad = cantidad #Lo que se surte es la cantidad pedida
                producto.cantidad = producto.cantidad - salida.cantidad   #se le resta a los articulos por surtir la cantidad que sale
                if entrada_res:   #si hay resurtimiento
                    #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad #    Este falló ya con el nuevo método salida.precio = entrada_res.articulo_comprado.precio_unitario
                    entrada_res.cantidad_por_surtir = entrada_res.cantidad_por_surtir - salida.cantidad
                    #producto.cantidad_apartada = producto.cantidad_apartada - salida.cantidad
                    salida.entrada = entrada_res.id
                    if producto.cantidad_requisitar == 0:
                        producto.requisitar = False
                    if entrada_res.cantidad_por_surtir == 0:
                        entrada_res.agotado = True
                    entrada_res.save()
                    inv_del_producto._change_reason = f'Esta es una salida desde un resurtimiento de inventario {salida.id}'
                    salida.precio = entrada_res.articulo_comprado.precio_unitario
                else:    #si no hay resurtimiento
                    salida.entrada = 0
                    salida.precio = inv_del_producto.price
                    #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad
                inv_del_producto.cantidad_apartada = inv_del_producto.cantidad_apartada - salida.cantidad
                producto.save()
                inv_del_producto.save()
                salida.save()

            else:
                entradas = EntradaArticulo.objects.filter(articulo_comprado__producto__producto = producto, agotado=False, entrada__oc__req__orden= producto.articulos.orden)
                for entrada in entradas:
                    if producto.cantidad > 0:
                        salida, created = Salidas.objects.get_or_create(producto=producto, vale_salida = vale_salida, complete=False)
                        salida.precio = entrada.articulo_comprado.precio_unitario
                        if entrada.cantidad_por_surtir >= cantidad:
                            salida.cantidad = cantidad
                            producto.cantidad = producto.cantidad - salida.cantidad
                            salida.entrada = entrada.id
                            entrada.cantidad_por_surtir = entrada.cantidad_por_surtir - salida.cantidad
                            salida.complete = True
                            if entrada.cantidad_por_surtir == 0:
                                entrada.agotado = True
                            producto.save()
                            entrada.save()
                            salida.save()
                        elif entrada.cantidad_por_surtir < cantidad:
                            salida.cantidad = entrada.cantidad_por_surtir #No puedo surtir mas que la cantidad que tengo disponible en la entrada
                            cantidad = cantidad - salida.cantidad #La nueva cantidad a surtir es la cantidad menos lo que ya salió
                            producto.cantidad = producto.cantidad - salida.cantidad
                            salida.entrada = entrada.id
                            salida.complete = True
                            entrada.agotado = True
                            entrada.cantidad_por_surtir = 0
                            #producto.salida = True si vuelvo la entrada de resurtimiento verdadera anulo la posibilidad de realizar más salidas
                            producto.save()
                            entrada.save()
                            salida.save()
                        inv_del_producto.cantidad_entradas = inv_del_producto.cantidad_entradas - salida.cantidad
                        if inv_del_producto.cantidad_apartada > 0:
                            inv_del_producto.cantidad_apartada = inv_del_producto.cantidad_apartada - salida.cantidad
                        #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad si hago una salida que proviene de entradas voy a obtener un inv_del_producto negativo
                        inv_del_producto.save()
    if action == "remove":
        item = Salidas.objects.get(vale_salida = vale_salida, id = id_salida)
        if item.entrada != 0:
            entrada = EntradaArticulo.objects.get(id=item.entrada)
            inv_del_producto.cantidad_entradas = inv_del_producto.cantidad_entradas + item.cantidad
            entrada.cantidad_por_surtir = entrada.cantidad_por_surtir + item.cantidad
            entrada.agotado = False
            entrada.save()
            #if entrada.entrada.oc.req.orden.tipo.tipo == "normal":
            #    inv_del_producto.cantidad_apartada = inv_del_producto.cantidad_apartada + item.cantidad
        if vale_salida.solicitud.tipo.tipo == "normal":
            inv_del_producto.cantidad_apartada = inv_del_producto.cantidad_apartada + item.cantidad
        #inv_del_producto.cantidad = inv_del_producto.cantidad + item.cantidad
        producto.seleccionado = False
        producto.salida= False
        producto.cantidad = producto.cantidad + item.cantidad
        inv_del_producto._change_reason = f'Esta es una cancelación de una salida {item.id}'
        producto.save()
        inv_del_producto.save()
        item.delete()

    return JsonResponse('Item updated, action executed: '+data["action"], safe=False)


@login_required(login_url='user-login')
def salida_material(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    orden = Order.objects.get(id = pk)
    productos= ArticulosparaSurtir.objects.filter(articulos__orden = orden, surtir=True)
    vale_salida, created = ValeSalidas.objects.get_or_create(almacenista = usuario,complete = False,solicitud=orden)
    salidas = Salidas.objects.filter(vale_salida = vale_salida)
    cantidad_items = salidas.count()


    formVale = ValeSalidasForm()
    form = SalidasForm()
    users = Profile.objects.all()

    if request.method == 'POST':
        formVale = ValeSalidasForm(request.POST, instance=vale_salida)
        cantidad_salidas = 0
        cantidad_productos = productos.count()
        for producto in productos:
            producto.seleccionado = False
            if producto.cantidad == 0:
                producto.salida=True
                producto.surtir=False
                cantidad_salidas = cantidad_salidas + 1
            producto.save()
        if cantidad_productos == cantidad_salidas:
            orden.requisitado == True #Esta variable creo que podría ser una variable estúpida
            orden.save()
        if formVale.is_valid():
            formVale.save()
            vale = formVale.save(commit=False)
            vale.complete = True
            messages.success(request,'La salida se ha generado de manera exitosa')
            return redirect('reporte-salidas')
        if not formVale.is_valid():
            messages.error(request,'No capturaste el usuario')

    context= {
        'productos':productos,
        'form':form,
        'formVale':formVale,
        'users': users,
        #'disponible':disponible,
        'vale_salida':vale_salida,
        'cantidad_items':cantidad_items,
        'salidas':salidas,
        }

    return render(request, 'requisiciones/salida_material.html',context)


def solicitud_autorizada_firma(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    #Aquí aparecen todas las ordenes, es decir sería el filtro para administrador
    productos= Salidas.objects.filter(producto__articulos__orden__autorizar = True, salida_firmada=False)
    myfilter = SalidasFilter(request.GET, queryset=productos)
    productos = myfilter.qs

    #Here is where XLSX is generated, using Openpyxl library | Aquí es donde se genera el XLSX
    if request.method == "POST" and 'btnExcel' in request.POST:

        return convert_solicitud_autorizada_orden_to_xls(productos)

    context= {
        'productos':productos,
        'myfilter':myfilter,
        'usuario':usuario,
        }
    return render(request, 'requisiciones/solicitudes_autorizadas_firma.html',context)



@login_required(login_url='user-login')
def salida_material_usuario(request, pk):
    producto= Salidas.objects.get(id = pk)
    producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto.producto.articulos)

    if request.method == 'POST':
        producto.salida_firmada = True
        producto_surtir.salida = True
        producto_surtir.firma = True
        producto_surtir.save()
        producto.save()

        messages.success(request,f'Has realizado la salida del producto {producto.producto.articulos.producto.producto} con éxito')
        return redirect('solicitud-autorizada-firma')

    context= {
        'productos':producto,
    }

    return render(request, 'requisiciones/salida_material_usuario.html',context)

@login_required(login_url='user-login')
def solicitud_autorizada_orden(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    #usuario = request.user.id

    perfil = Profile.objects.get(staff__id=request.user.id)
    ordenes = Order.objects.filter(requisitar = True, complete=True, autorizar=True, staff__distrito=perfil.distrito, requisitado = False)


    if perfil.tipo.almacenista == True:
        ordenes = Order.objects.filter(requisitar = True, requisitado=False)
        #ordenes = Order.objects.filter(requisitar = True, complete=True, autorizar =True)
    #perfil = Profile.objects.get(id=usuario)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(requisitar=True), articulos__orden__autorizar = True )


    if request.method == "POST" and 'btnExcel' in request.POST:

        return convert_solicitud_autorizada_orden_to_xls(ordenes)

    context= {
        'ordenes':ordenes,
        }

    return render(request, 'requisiciones/solicitudes_autorizadas_orden.html',context)


def detalle_orden(request, pk):
    orden = Order.objects.get(id=pk)
    productos = ArticulosOrdenados.objects.filter(orden=pk)

    context = {
        'productos': productos,
        'orden': orden,
     }
    return render(request,'requisiciones/orden_detail.html', context)


@login_required(login_url='user-login')
def requisicion_autorizacion(request):
    perfil = Profile.objects.get(staff__id=request.user.id)
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito

    #ordenes = Order.objects.filter(complete=True, autorizar=True, staff__distrito=perfil.distrito)
    if perfil.tipo.superintendente == True:
        requis = Requis.objects.filter(autorizar=None, orden__superintendente=perfil, complete =True)
    else:
        requis = Requis.objects.filter(complete=None)
    #requis = Requis.objects.filter(autorizar=None)


    context= {
        'requis':requis,
        }

    return render(request, 'requisiciones/requisiciones_autorizacion.html',context)

def requisicion_creada_detalle(request, pk):
    productos = ArticulosRequisitados.objects.filter(req = pk)
    requis = Requis.objects.get(id = pk)

    context = {
        'productos': productos,
        'requis': requis,
     }

    return render(request,'requisiciones/requisicion_creada_detalle.html', context)

def update_requisicion(request):
    data= json.loads(request.body)
    action = data["action"]
    producto_id = data["id"]
    pk = data["requi"]
    cantidad = int(data["cantidad"])

    requi = Requis.objects.get(id=pk)
    #orden = Order.objects.get(id=requi.orden.id)
    producto = ArticulosparaSurtir.objects.get(id = producto_id)
    if action == "add":
        item, created = ArticulosRequisitados.objects.get_or_create(req=requi, producto = producto, cantidad = cantidad)
        producto.requisitar = False
        producto.seleccionado = True
        producto.save()
        item.save()
    if action == "remove":
        item = ArticulosRequisitados.objects.get(req = requi, producto = producto)
        articulo_requisitado = ArticulosparaSurtir.objects.get(id =producto_id)
        articulo_requisitado.requisitar = True
        articulo_requisitado.seleccionado = False
        articulo_requisitado.save()
        item.delete()

    return JsonResponse('Item updated, action executed: '+data["action"], safe=False)


def requisicion_detalle(request, pk):
    #Vista de creación de requisición
    productos = ArticulosparaSurtir.objects.filter(articulos__orden__id = pk, requisitar= True)
    orden = Order.objects.get(id = pk)
    usuario = Profile.objects.get(staff__id=request.user.id)
    requi, created = Requis.objects.get_or_create(complete=False, orden=orden)
    requis = Requis.objects.filter(orden__staff__distrito = usuario.distrito, complete = True)
    consecutivo = requis.count() + 1

    #for producto in productos:
    productos_requisitados = ArticulosRequisitados.objects.filter(req = requi)

    form = RequisForm()


    if request.method == 'POST':
        form = RequisForm(request.POST, instance=requi)
        requi.complete = True
        orden.requisitado = True
        for producto in productos:
            #Vuelve false para que desaparezca de la vista pero creo que debo evaluar si es la mejor manera lo mismo para orden.requisitar = False, esto me está causando problemas en la vista
            producto.seleccionado = False
            producto.save()
            if producto.requisitar == False:
                orden.requisitado = False
                orden.save()
        if productos_requisitados:
            requi.folio = str(usuario.distrito.abreviado)+str(requi.id).zfill(4)
            requi.save()
            form.save()
            orden.save()
            messages.success(request,f'Has realizado la requisición {requi.folio} con éxito')
            return redirect('solicitud-autorizada-orden')
        else:
             messages.error(request,'No se puede crear la requisición debido a que no productos agregados')


    context = {
        'productos': productos,
        'productos_requisitados':productos_requisitados,
        'orden': orden,
        'requi':requi,
        'form':form,
        }

    return render(request,'requisiciones/detalle_requisitar_editar.html', context)

def requisicion_autorizar(request, pk):
    usuario = request.user.id
    perfil = Profile.objects.get(staff__id=usuario)
    #perfil = Profile.objects.get(id=usuario)
    requi = Requis.objects.get(id = pk)
    productos = ArticulosRequisitados.objects.filter(req = pk)
    costo_aprox = 0
    for producto in productos:
        costo_aprox = costo_aprox + producto.cantidad * producto.producto.articulos.producto.price

    porcentaje = "{0:.2f}%".format((costo_aprox/requi.orden.subproyecto.presupuesto)*100)
    resta = requi.orden.subproyecto.presupuesto - requi.orden.subproyecto.gastado - costo_aprox

    if request.method == 'POST':
        requi.requi_autorizada_por = perfil
        requi.approved_at_time = datetime.now().time()
        requi.approved_at = date.today()
        requi.autorizar = True
        requi.save()
        email = EmailMessage(
                f'Requisición Autorizada {requi.folio}',
                f'Estimado {requi.orden.staff.staff.first_name} {requi.orden.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.first_name} {requi.requi_autorizada_por.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                'savia@vordtec.com',
                ['ulises_huesc@hotmail.com'],[requi.orden.staff.staff.email],
                )
        email.send()
        messages.success(request,f'Has autorizado la requisición {requi.folio} con éxito')
        return redirect('requisicion-autorizacion')

    context = {
        'productos': productos,
        'requis': requi,
        'costo_aprox': costo_aprox,
        'porcentaje': porcentaje,
        'resta': resta,
     }

    return render(request,'requisiciones/requisiciones_autorizar.html', context)

def requisicion_cancelar(request, pk):
    usuario = request.user.id
    perfil = Profile.objects.get(staff=usuario)
    requis = Requis.objects.get(id = pk)
    productos = ArticulosRequisitados.objects.filter(req = pk)

    if request.method == 'POST':
        form= Rechazo_Requi_Form(request.POST,instance=requis)
        if form.is_valid():
            requis.autorizada_por = perfil
            requis.autorizar = False
            requis.save()
            email = EmailMessage(
                f'Requisición Rechazada {requis.folio}',
                f'Estimado {requis.orden.staff.staff.first_name} {requis.orden.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requis.orden.folio}| Req: {requis.folio} ha sido rechazada,\n por {requis.autorizada_por.staff.first_name} {requis.autorizada_por.staff.last_name} por el siguiente motivo: \n " {requis.comentario_comprador} ".\n\n Este mensaje ha sido automáticamente generado por SAVIA X',
                'savia@vordtec.com',
                ['ulises_huesc@hotmail.com'],[requis.orden.staff.staff.email],
                )
            email.send()
            messages.error(request,f'Has cancelado la requisición {requis.folio}')
            return redirect('requisicion-autorizacion')
    else:
        form = Rechazo_Requi_Form(instance=requis)


    context = {
        'productos': productos,
        'requis': requis,
        'form':form,
     }
    return render(request,'requisiciones/requisiciones_cancelar.html', context)

def render_pdf_view(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    orden = Order.objects.get(id=pk)
    productos = ArticulosOrdenados.objects.filter(orden=pk)
    #salidas = Salidas.objects.filter(producto__articulos__orden__id=pk)


    #Azul Vordcab
    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    #prussian_blue = Color(0.2421875,0.5703125,0.796875)
    rojo = Color(0.59375, 0.05859375, 0.05859375)
    c.setFillColor(prussian_blue)
    # REC (DIST DEL MARGEN VERTICAL, DIST DEL MARGEN HORIZONTAL, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,695,565,25, fill=True, stroke=False)


    #Encabezado
    c.setFillColor(black)
    c.setLineWidth(.3)
    c.setFont('Helvetica-Bold',14)
    c.drawString(180,760,'Solicitud')
    c.setFont('Helvetica',12)
    c.drawString(300,760,'Preparado por:')


    c.setFillColor(rojo)
    #c.drawString(90,730,orden.get_folio)
    c.setFillColor(black)
    c.setFont('Helvetica',22)
    #c.drawString(30,750,'Vordtec de México')

    c.setFont('Helvetica-Bold',12)
    c.drawString(480,740,orden.created_at.strftime("%d/%m/%Y"))



    c.drawInlineImage('static/images/logo vordtec_documento.png',30,740, 3.0 * cm, 1.5 * cm)
    c.setFillColor(white)
    c.setFont('Helvetica',14)
    c.drawCentredString(320,700,'Comprobante de Solicitud')
    c.setFillColor(black)
    c.setFont('Helvetica',12)
    c.drawString(290,680,'Estatus:')
    c.drawString(290,660, 'Proyecto:')
    c.drawString(290,640, 'Área:')
    c.drawString(290,620, 'Almacén:')


    c.drawString(370,660, orden.proyecto.nombre)
    c.drawString(370,640, orden.area.nombre)
    c.drawString(370,620, orden.staff.distrito.nombre)
    #c.drawString(370,600, orden.sector.nombre)



    c.setLineWidth(.3)
    c.line(20,570,585,570)





    #Create blank list
    data =[]

    data.append(['''Código''', '''Nombre''', '''Cantidad'''])


    high = 540
    for producto in productos:
        data.append([producto.producto.producto.codigo, producto.producto.producto.nombre,producto.cantidad])
        high = high - 18


    c.setFillColor(prussian_blue)
    c.rect(20,high-50,565,25, fill=True, stroke=False)
    c.setFillColor(white)
    c.drawCentredString(320,high-45,'Observaciones')
    c.setFillColor(black)
    c.drawCentredString(230,high-190, orden.staff.staff.first_name +' '+ orden.staff.staff.last_name)
    c.line(180,high-195,280,high-195)
    c.drawCentredString(230,high-205, 'Solicitado')
    #if orden.sol_autorizada_por == None:
    #    c.setFillColor(rojo)
    #    c.drawCentredString(410, high-190, '{Esta orden no ha sido autorizada}')
    #    c.drawString(370,680, 'No aprobada')
    #else:
    #    c.setFillColor(black)
    #    c.drawCentredString(410,high-190, orden.sol_autorizada_por.staff.first_name+' '+ orden.staff.staff.last_name)
    #    c.drawString(370,680, 'Aprobada')
    c.setFillColor(black)
    c.line(360,high-195,460,high-195)
    c.drawCentredString(410,high-205,'Aprobado por')



    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)
    #Primer renglón
    c.drawCentredString(70,48,'Clasificación:')
    c.drawCentredString(140,48,'Nivel:')
    c.drawCentredString(240,48,'Preparado por:')
    c.drawCentredString(350,48,'Aprobado:')
    c.drawCentredString(450,48,'Fecha emisión:')
    c.drawCentredString(550,48,'Rev:')
    #Segundo renglón
    c.drawCentredString(70,34,'Controlado')
    c.drawCentredString(140,34,'N5')
    c.drawCentredString(240,34,'SEOV-ALM-N4-01-01')
    c.drawCentredString(350,34,'SUB ADM')
    c.drawCentredString(450,34,'24/Oct/2018')
    c.drawCentredString(550,34,'001')


    width, height = letter
    table = Table(data, colWidths=[4 * cm, 9.0 * cm, 4.0 * cm])
    table.setStyle(TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.black),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 13),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 12),
        ]))

    #pdf size
    table.wrapOn(c, width, height)
    table.drawOn(c, 55, high)

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='reporte_' + str(orden.get_folio) +'.pdf')

def reporte_entradas(request):
    entradas = EntradaArticulo.objects.filter(entrada__completo = True, articulo_comprado__producto__producto__articulos__producto__producto__servicio = False)
    myfilter = EntradasFilter(request.GET, queryset=entradas)
    entradas = myfilter.qs

    if request.method == "POST" and 'btnExcel' in request.POST:

        return convert_entradas_to_xls(entradas)


    context = {
        'entradas':entradas,
        'myfilter':myfilter,
        }

    return render(request,'requisiciones/reporte_entradas.html', context)

def reporte_salidas(request):
    salidas = Salidas.objects.all()
    myfilter = SalidasFilter(request.GET, queryset=salidas)
    salidas = myfilter.qs

    if request.method == "POST" and 'btnExcel' in request.POST:
        return convert_salidas_to_xls(salidas)



    context = {
        'salidas':salidas,
        'myfilter':myfilter,
        }

    return render(request,'requisiciones/reporte_salidas.html', context)

@login_required(login_url='user-login')
def historico_articulos_para_surtir(request):
    registros = ArticulosparaSurtir.history.all()

    context = {
        'registros':registros,
        }

    return render(request,'requisiciones/historicos_articulos_para_surtir.html',context)

@login_required(login_url='user-login')
def historico_salidas(request):
    registros = Salidas.history.all()

    context = {
        'registros':registros,
        }

    return render(request,'requisiciones/historico_salidas.html',context)


def convert_solicitud_autorizada_to_xls(productos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Solicitudes_' + str(dt.date.today())+'.xlsx'
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

    columns = ['Folio','Solicitante','Proyecto','Subproyecto','Código','Artículo','Creado']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = productos.values_list('articulos__orden_id',Concat('articulos__orden__staff__staff__first_name',Value(' '),'articulos__orden__staff__staff__last_name'),
                            'articulos__orden__proyecto__nombre','articulos__orden__subproyecto__nombre',
                            'articulos__producto__producto__codigo','articulos__producto__producto__nombre','articulos__orden__approved_at')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            if col_num/6 >0 and col_num % 6 == 0:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            else:
                (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)
    #Aquí termina la implementación del XLSX

def convert_solicitud_autorizada_orden_to_xls(ordenes):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Solicitudes_pend_requisicion' + str(dt.date.today())+'.xlsx'
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

    columns = ['Folio','Solicitante','Proyecto','Subproyecto','Creado']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = ordenes.values_list('id',Concat('staff__staff__first_name',Value(' '),'staff__staff__last_name'),
                            'proyecto__nombre','subproyecto__nombre','created_at')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 4:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style

    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)
#Aquí termina la implementación del XLSX

def convert_entradas_to_xls(entradas):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Entradas_' + str(dt.date.today())+'.xlsx'
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

    columns = ['Folio Solicitud','Fecha','Solicitante','Proyecto','Subproyecto','Código','Articulo','Cantidad']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = entradas.values_list('entrada__oc__req__orden__id','created_at',Concat('entrada__oc__req__orden__staff__staff__first_name',Value(' '),'entrada__oc__req__orden__staff__staff__last_name'),
                        'entrada__oc__req__orden__proyecto__nombre','entrada__oc__req__orden__subproyecto__nombre','articulo_comprado__producto__producto__articulos__producto__producto__codigo',
                        'articulo_comprado__producto__producto__articulos__producto__producto__nombre','cantidad')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 4:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style

    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)
#Aquí termina la implementación del XLSX

def convert_salidas_to_xls(salidas):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Salidas_' + str(dt.date.today())+'.xlsx'
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

    columns = ['Folio Solicitud','Fecha','Solicitante','Proyecto','Subproyecto','Código','Articulo','Material recibido por','Cantidad']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = salidas.values_list('producto__articulos__orden__id','created_at',Concat('producto__articulos__orden__staff__staff__first_name',Value(' '),'producto__articulos__orden__staff__staff__last_name'),
                        'producto__articulos__orden__proyecto__nombre','producto__articulos__orden__subproyecto__nombre','producto__articulos__producto__producto__codigo','producto__articulos__producto__producto__nombre',
                        Concat('vale_salida__material_recibido_por__staff__first_name',Value(' '),'vale_salida__material_recibido_por__staff__last_name'),'cantidad')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 8:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = body_style

    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)
#Aquí termina la implementación del XLSX


def render_salida_pdf(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=portrait(letter))
    #Here ends conf.
    articulo = Salidas.objects.get(id=pk)
    vale = ValeSalidas.objects.get(id = articulo.vale_salida.id)
    productos = Salidas.objects.filter(vale_salida = vale)


    #Azul Vordcab
    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    rojo = Color(0.59375, 0.05859375, 0.05859375)
    #Encabezado
    c.setFillColor(black)
    c.setLineWidth(.2)
    c.setFont('Helvetica',8)
    caja_iso = 770
    #Elaborar caja
    #c.line(caja_iso,500,caja_iso,720)


    c.drawString(420,caja_iso,'Preparado por:')
    c.drawString(420,caja_iso-10,'SUP. ADMON')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(520,caja_iso-10,'SUB ADM')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'F-ALM-N4-01.02')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'1-Sep.-18')


    c.drawString(510,caja_iso-50,'Folio: ')
    c.drawString(530,caja_iso-50, str(vale.id))
    c.drawString(510,caja_iso-60,'Fecha:')
    c.drawString(540,caja_iso-60,vale.created_at.strftime("%d/%m/%Y"))


    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,caja_iso-15,250,20, fill=True, stroke=False) #Barra azul superior Orden de Compra

    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,caja_iso-10,'Vale de Salida Almacén')
    c.setLineWidth(.3) #Grosor

    c.drawInlineImage('static/images/logo vordtec_documento.png',45,caja_iso-40, 3 * cm, 1.5 * cm) #Imagen vortec


    data =[]
    high = 670
    data.append(['''Código''','''Producto''', '''Cantidad''', '''Unidad''','''P.Unitario''', '''Importe'''])
    for producto in productos:
        data.append([producto.producto.articulos.producto.producto.codigo, producto.producto.articulos.producto.producto.nombre,producto.cantidad, producto.producto.articulos.producto.producto.unidad, producto.precio, producto.precio * producto.cantidad])
        high = high - 18

    c.setFillColor(black)
    c.setFont('Helvetica',8)


    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,480,250,20, fill=True, stroke=False) #3ra linea azul
    c.setFillColor(black)
    c.setFont('Helvetica',7)


    c.setFillColor(white)
    c.setLineWidth(.1)
    c.setFont('Helvetica-Bold',10)
    c.drawCentredString(70,485,'Proyecto')
    c.drawCentredString(165,485,'Subproyecto')

    c.setFont('Helvetica',8)
    c.setFillColor(black)
    c.drawCentredString(70,470, str(vale.solicitud.proyecto.nombre))
    c.drawCentredString(165,470, str(vale.solicitud.subproyecto.nombre))


    c.setFillColor(black)
    c.setFont('Helvetica',8)
    #c.line(135,high-200,215, high-200) #Linea de Autorizacion
    c.drawCentredString(150,455,'Entregó')
    c.drawCentredString(150,445, vale.almacenista.staff.first_name +' '+vale.almacenista.staff.last_name)

    c.line(370,465,430, 465)
    c.drawCentredString(400,455,'Recibió')
    c.drawCentredString(400,445, vale.material_recibido_por.staff.first_name +' '+vale.material_recibido_por.staff.last_name)


    #c.line(240, high-200, 310, high-200)
    c.drawCentredString(280,455,'Autorizó')
    c.drawCentredString(280,445, vale.solicitud.staff.staff.first_name + ' ' + vale.solicitud.staff.staff.last_name)

    c.setFont('Helvetica',10)
    c.setFillColor(prussian_blue)
    c.setFont('Helvetica', 9)
    c.setFillColor(black)

    c.setFillColor(prussian_blue)
    c.rect(20,420,565,20, fill=True, stroke=False)
    c.setFillColor(white)

    width, height = letter
    table = Table(data, colWidths=[2.8 * cm, 6 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm])
    table.setStyle(TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 12),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 8),
        ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 20, high)
    c.save()
    c.showPage()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='vale_salida_'+str(vale.id) +'.pdf')