from django.shortcuts import render, redirect
from solicitudes.models import Proyecto, Subproyecto
from dashboard.models import Inventario, Order, ArticulosparaSurtir, ArticulosOrdenados, Inventario_Batch, Product, Marca
from dashboard.forms import  Inventario_BatchForm
from user.models import Profile, User
from .models import ArticulosRequisitados, Requis, Devolucion, Devolucion_Articulos, Tipo_Devolucion
from entradas.models import Entrada, EntradaArticulo
from requisiciones.models import Salidas, ValeSalidas
from django.contrib.auth.decorators import login_required
from user.decorators import perfil_seleccionado_required
from .filters import ArticulosparaSurtirFilter, SalidasFilter, EntradasFilter, DevolucionFilter
from .forms import SalidasForm, ArticulosRequisitadosForm, ValeSalidasForm, ValeSalidasProyForm, RequisForm, Rechazo_Requi_Form, DevolucionArticulosForm, DevolucionForm
from solicitudes.filters import SolicitudesFilter
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt
from datetime import date, datetime
from django.db.models.functions import Concat
from django.db.models import Value, Sum, Case, When, F, Value, Q
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import EmailMessage
import json
import csv
from django.core.paginator import Paginator
import ast # Para leer el csr many to many
import decimal

#PDF generator
#PDF generator
import io
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter, portrait
from reportlab.rl_config import defaultPageSize
from django.http import FileResponse
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
import urllib.request, urllib.parse, urllib.error


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
    
    if usuario.tipo.almacenista == True:
        productos= ArticulosparaSurtir.objects.filter(salida=False, surtir=False, articulos__orden__autorizar = True, articulos__orden__tipo__tipo = "normal")

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


def update_devolucion(request):
    data= json.loads(request.body)
    action = data["action"]
    cantidad = decimal.Decimal(data["val_cantidad"])
    devolucion = data["devolucion"]
    producto_id = data["id"]
    comentario = data["comentario"]
    devolucion = Devolucion.objects.get(id = devolucion)
    
    
    if devolucion.tipo.nombre == "SALIDA":
        producto = Salidas.objects.get(vale_salida=devolucion.salida.vale_salida, producto__id = producto_id)
        inv_del_producto = Inventario.objects.get(producto = producto.producto.articulos.producto.producto)
    else:
        producto = ArticulosparaSurtir.objects.get(id = producto_id)
        inv_del_producto = Inventario.objects.get(producto = producto.articulos.producto.producto)
        


    if action == "add":
        cantidad_total = producto.cantidad - cantidad
        if cantidad_total < 0:
            messages.error(request,f'La cantidad que se quiere ingresar sobrepasa la cantidad disponible. {cantidad_total} mayor que {producto.cantidad}')
        else:
            if devolucion.tipo.nombre == "SALIDA":
                devolucion_articulos, created = Devolucion_Articulos.objects.get_or_create(producto= producto.producto, vale_devolucion = devolucion, complete=False)
            else:
                devolucion_articulos, created = Devolucion_Articulos.objects.get_or_create(producto=producto, vale_devolucion = devolucion, complete=False)
            
            producto.seleccionado = True
            #Se le resta a la cantidad de artículos para surtir
            producto.cantidad = producto.cantidad - cantidad
            #La cantidad de la devolución es igual a la cantidad que se marcó en la devolución (daaa)
            devolucion_articulos.cantidad = cantidad
            devolucion_articulos.comentario = comentario
            devolucion_articulos.precio = producto.precio
            devolucion_articulos.complete = True
            if producto.cantidad == 0: #Si la cantidad de artículos para surtir es igual a 0, si la cantidad a devolver es 0 entonces ya no se puede surtir
                producto.surtir = False
            messages.success(request,'Has agregado producto para devolución de manera exitosa')
            producto.save()
            devolucion_articulos.save()
    if action == "remove":
        if devolucion.tipo.nombre == "SALIDA":
            item = Devolucion_Articulos.objects.get(producto=producto.producto, vale_devolucion = devolucion, complete = True)
        else:
            item = Devolucion_Articulos.objects.get(producto=producto, vale_devolucion = devolucion, complete = True)
        producto.cantidad = producto.cantidad + item.cantidad
        producto.seleccionado = False
        messages.success(request,'Has eliminado un producto de tu listado')
        producto.save()
        item.delete()

    return JsonResponse('Item updated, action executed: '+data["action"], safe=False)

@login_required(login_url='user-login')
def autorizar_devolucion(request, pk):
    devolucion= Devolucion.objects.get(id=pk)
    productos = Devolucion_Articulos.objects.filter(vale_devolucion = devolucion)
    
    if request.method == 'POST' and 'btnAutorizar' in request.POST:
        for producto in productos:
            if devolucion.tipo.nombre == "SALIDA":
                producto_surtir = Salidas.objects.get(id=devolucion.salida.id)
                inv_del_producto = Inventario.objects.get(producto = producto.producto.articulos.producto.producto) 
                inv_del_producto._change_reason = f'Esta es una devolucion desde un salida {devolucion.id}'
            else:
                producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto.producto.articulos)
                inv_del_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto)
                inv_del_producto._change_reason = f'Esta es una devolucion desde un surtimiento de inventario {devolucion.id}'
                try:
                    entrada = EntradaArticulo.objects.get(articulo_comprado__producto__producto=producto_surtir, entrada__oc__req__orden=producto_surtir.articulos.orden, agotado = False)
                    
                    # Verificar si la cantidad en la entrada es suficiente
                    if entrada.cantidad_por_surtir >= producto.cantidad:
                        print(entrada)
                        # Reducir la cantidad de la entrada según la cantidad de la devolución
                        entrada.cantidad_por_surtir -= producto.cantidad 
                        entrada.save()
                    else:
                        # Manejar el caso en que no hay suficiente cantidad en la entrada (opcional)
                        entrada.cantidad_por_surtir = 0
                        entrada.agotado = True
                        entrada.save()
                except EntradaArticulo.DoesNotExist:
                    # Manejar el caso en que no hay una entrada asociada (opcional)
                    messages.error(request, 'No se encontró una entrada asociada para el producto.')
                    
            inv_del_producto.cantidad = inv_del_producto.cantidad + producto.cantidad
            inv_del_producto.save()
            messages.success(request,'Has autorizado exitosamente una devolución')
        devolucion.autorizada = True
        devolucion.save()
        return redirect('matriz-autorizar-devolucion')

    context= {
        'productos':productos,
        'devolucion':devolucion,
        }

    return render(request, 'requisiciones/autorizar_devolucion.html',context)

@login_required(login_url='user-login')
def cancelar_devolucion(request, pk):
    devolucion= Devolucion.objects.get(id=pk)
    productos = Devolucion_Articulos.objects.filter(vale_devolucion = devolucion)

    if request.method == 'POST' and 'btnCancelar' in request.POST:
        for producto in productos:
            if devolucion.tipo.nombre == "SALIDA":
                producto_surtir = Salidas.objects.get(salida=devolucion.salida)
            else:
                producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto.producto.articulos)
            producto_surtir.cantidad = producto_surtir.cantidad + producto.cantidad
            producto_surtir.surtir = True
            producto_surtir.save()
            #inv_del_producto.save()
        devolucion.autorizada = False
        devolucion.save()
        return redirect('matriz-autorizar-devolucion')

    context= {
        'productos':productos,
        'devolucion':devolucion,
        }

    return render(request, 'requisiciones/cancelar_devolucion.html',context)


@login_required(login_url='user-login')
def matriz_autorizar_devolucion(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    devoluciones= Devolucion.objects.filter(complete=True, autorizada=None)
    #print(devoluciones)

    
    myfilter = DevolucionFilter(request.GET, queryset = devoluciones)
    devoluciones = myfilter.qs

    #Set up pagination
    p = Paginator(devoluciones, 20)
    page = request.GET.get('page')
    devoluciones_list = p.get_page(page)

    #Here is where call a function to generate XLSX, using Openpyxl library

    #if request.method == 'POST' and 'btnExcel' in request.POST:
    #    return convert_solicitud_autorizada_to_xls(productos)


    context= {
        'devoluciones_list':devoluciones_list,
        'devoluciones':devoluciones,
        'myfilter':myfilter,
        'usuario':usuario,
        }
    return render(request, 'requisiciones/matriz_devoluciones_autorizar.html',context)

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
        
        if formVale.is_valid():
            #formVale.save()
            vale = formVale.save(commit=False)
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
            vale.complete = True
            vale.save()
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

@login_required(login_url='user-login')
def devolucion_material(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    orden = Order.objects.get(id = pk)
    productos_sel = ArticulosparaSurtir.objects.filter(articulos__orden = orden, surtir=True)
    tipo = Tipo_Devolucion.objects.get(nombre ="APARTADO" )
    devolucion, created = Devolucion.objects.get_or_create(almacenista = usuario,complete = False,solicitud=orden, tipo=tipo)
    productos = Devolucion_Articulos.objects.filter(vale_devolucion = devolucion)
    cantidad_items = productos.count()
    form = DevolucionArticulosForm()
    form2 = DevolucionForm()

    form.fields['producto'].queryset = productos_sel

    if request.method == 'POST':
        if "agregar_devolucion" in request.POST:
            form2 = DevolucionForm(request.POST, instance=devolucion)
            if form2.is_valid():
                devolucion = form2.save(commit=False)
                devolucion.complete= True
                devolucion.hora = datetime.now().time()
                devolucion.fecha = date.today()
                devolucion.tipo.nombre = "SIN SALIDA" 
                devolucion.save()
                for producto in productos_sel:
                    producto.seleccionado = False
                    producto.save()
                messages.success(request,f'{usuario.staff.first_name}, Has hecho la devolución de manera exitosa')
                email = EmailMessage(
                    f'Cancelación de solicitud: {orden.folio}',
                    f'Estimado {orden.staff.staff.first_name} {orden.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {orden.folio} ha sido devuelta al almacén por {usuario.staff.first_name} {usuario.staff.last_name}, con el siguiente comentario {devolucion.comentario} para más información comunicarse al almacén.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    'savia@vordtec.com',
                    ['ulises_huesc@hotmail.com'],#orden.staff.staff.email],
                    )
                email.send()
                return redirect('solicitud-autorizada')

    context= {
        'orden':orden,
        'productos':productos,
        'form':form,
        'form2':form2,
        'devolucion': devolucion,
        'cantidad_items':cantidad_items,
        'productos_sel': productos_sel,
        }

    return render(request, 'requisiciones/devolucion_material.html',context)

@login_required(login_url='user-login')
def devolucion_material_salida(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    salidas = Salidas.objects.all()
    salida = salidas.get(id=pk)
    vale_salida = ValeSalidas.objects.get(id=salida.vale_salida.id)
    orden = Order.objects.get(id = vale_salida.solicitud.id)
    #Esta es la parte que varía de devolución de material, aquí los productos deben ser salida = True
    #productos_sel = ArticulosparaSurtir.objects.filter(articulos__orden = orden, salida=True)
    productos_sel = salidas.filter(id=pk)
    tipo = Tipo_Devolucion.objects.get(nombre ="SALIDA" )
    devolucion, created = Devolucion.objects.get_or_create(almacenista = usuario,complete = False,solicitud=orden,tipo =tipo, salida =salida)
    productos = Devolucion_Articulos.objects.filter(vale_devolucion = devolucion)
    cantidad_items = productos.count()
    form = DevolucionArticulosForm()
    form2 = DevolucionForm()

    form.fields['producto'].queryset = productos_sel

    if request.method == 'POST':
        if "agregar_devolucion" in request.POST:
            form2 = DevolucionForm(request.POST, instance=devolucion)
            if form2.is_valid():
                devolucion = form2.save(commit=False)
                devolucion.complete= True
                devolucion.hora = datetime.now().time()
                devolucion.fecha = date.today()
                devolucion.save()
                for producto in productos_sel:
                    producto.seleccionado = False
                    producto.save()
                messages.success(request,f'{usuario.staff.first_name}, Has hecho la devolución de manera exitosa')
                email = EmailMessage(
                    f'Cancelación de solicitud: {orden.folio}',
                    f'Estimado {orden.staff.staff.first_name} {orden.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {orden.folio} ha sido devuelta al almacén por {usuario.staff.first_name} {usuario.staff.last_name}, con el siguiente comentario {devolucion.comentario} para más información comunicarse al almacén.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    'savia@vordtec.com',
                    ['ulises_huesc@hotmail.com'],#orden.staff.staff.email],
                    )
                email.send()
                return redirect('solicitud-autorizada')

    context= {
        'orden':orden,
        'productos':productos,
        'form':form,
        'form2':form2,
        'devolucion': devolucion,
        'cantidad_items':cantidad_items,
        'productos_sel': productos_sel,
        }

    return render(request, 'requisiciones/devolucion_material.html',context)


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


def update_salida(request):
    data= json.loads(request.body)
    action = data["action"]
    cantidad = decimal.Decimal (data["val_cantidad"])
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
        #con cantidad total establezco si la "cantidad" no sobrepasa lo que tengo que surtir(producto.cantidad)     
        cantidad_total = producto.cantidad - cantidad
        producto.seleccionado = True
        entradas_dir = EntradaArticulo.objects.filter(articulo_comprado__producto__producto=producto, agotado=False, entrada__oc__req__orden=producto.articulos.orden, articulo_comprado__producto__producto__articulos__orden__tipo__tipo = 'normal')

        try:
            EntradaArticulo.objects.filter(articulo_comprado__producto__producto__articulos__producto = inv_del_producto, articulo_comprado__producto__producto__articulos__orden__tipo__tipo = 'resurtimiento', agotado = False)
           
        except EntradaArticulo.DoesNotExist:
            entrada_res = None
        else:
            entrada_res = EntradaArticulo.objects.filter(articulo_comprado__producto__producto__articulos__producto = inv_del_producto, articulo_comprado__producto__producto__articulos__orden__tipo__tipo = 'resurtimiento', agotado = False).order_by('id')

        if entradas_dir.exists():
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
                        #producto.salida =
                        #True si vuelvo la entrada de resurtimiento verdadera anulo la posibilidad de realizar más salidas
                        producto.save()
                        entrada.save()
                        salida.save()
                    inv_del_producto.cantidad_entradas = inv_del_producto.cantidad_entradas - salida.cantidad
                    #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad si hago una salida que proviene de entradas voy a obtener un inv_del_producto negativo
                    inv_del_producto.save()
        elif entrada_res:   #si hay resurtimiento
            for entrada in entrada_res:
                if producto.cantidad > 0:
                    salida, created = Salidas.objects.get_or_create(producto=producto, vale_salida = vale_salida, complete=False)
                    salida.cantidad = cantidad
                    #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad #    Este falló ya con el nuevo método salida.precio = entrada_res.articulo_comprado.precio_unitario
                    entrada.cantidad_por_surtir = entrada.cantidad_por_surtir - salida.cantidad
                    producto.cantidad = producto.cantidad - salida.cantidad
                    #producto.cantidad_requisitar = producto.cantidad_requisitar + salida.cantidad
                    salida.entrada = entrada.id
                    salida.complete = True
                    if producto.cantidad_requisitar == 0:
                        producto.requisitar = False
                    if entrada.cantidad_por_surtir == 0:
                        entrada.agotado = True
                    entrada.save()
                    inv_del_producto.cantidad_entradas = inv_del_producto.cantidad_entradas - salida.cantidad
                    inv_del_producto._change_reason = f'Esta es la salida de un artículo desde un resurtimiento de inventario {salida.id}'
                    salida.precio = entrada.articulo_comprado.precio_unitario
                    salida.save()
        else:    #si no hay resurtimiento
            salida, created = Salidas.objects.get_or_create(producto=producto, vale_salida = vale_salida, complete=False)
            salida.cantidad = cantidad
            salida.entrada = 0
            salida.complete = True
            producto.cantidad = producto.cantidad - salida.cantidad 
            if producto.cantidad_requisitar <= 0:
                producto.requisitar = False
            salida.precio = inv_del_producto.price
            inv_del_producto._change_reason = f'Esta es la salida de inventario de un artículo'
            #inv_del_producto.cantidad = inv_del_producto.cantidad - salida.cantidad
        inv_del_producto.cantidad_apartada = inv_del_producto.cantidad_apartada - salida.cantidad
        producto.save()
        inv_del_producto.save()
        salida.save()

       
        
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
        inv_del_producto._change_reason = f'Esta es una cancelación de un artìculo en una salida {item.id}'
        producto.save()
        inv_del_producto.save()
        item.delete()

    return JsonResponse('Item updated, action executed: '+data["action"], safe=False)


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
def matriz_salida_activos(request):
    productos = Salidas.objects.filter(validacion_activos = False, producto__articulos__producto__producto__activo = True)
    #producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto.producto.articulos)
    #activo = Activo.objects.filter(activo = productos.producto.producto)


    context= {
        'productos':productos,
    }

    return render(request, 'requisiciones/matriz_salida_activos.html',context)

@login_required(login_url='user-login')
def solicitud_autorizada_orden(request):
    perfil = Profile.objects.get(staff__id=request.user.id)
    ordenes = Order.objects.filter(requisitar = True, complete=True, autorizar=True, staff__distritos=perfil.distritos, requisitado = False)


    if perfil.tipo.almacenista == True:
        ordenes = Order.objects.filter(requisitar = True, requisitado=False)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #productos= ArticulosparaSurtir.objects.filter(Q(salida=False) | Q(requisitar=True), articulos__orden__autorizar = True )
    myfilter=SolicitudesFilter(request.GET, queryset=ordenes)
    ordenes = myfilter.qs


    if request.method == "POST" and 'btnExcel' in request.POST:

        return convert_solicitud_autorizada_orden_to_xls(ordenes)

    context= {
        'ordenes':ordenes,
        'myfilter':myfilter,
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
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    #perfil = Profile.objects.get(staff__id=request.user.id)
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
    cantidad = decimal.Decimal(data["cantidad"])
    
    requi = Requis.objects.get(id=pk)
    orden = Order.objects.get(id=requi.orden.id)

    producto = ArticulosparaSurtir.objects.get(id = producto_id)
    ordenado = ArticulosOrdenados.objects.filter(orden = orden, producto = producto.articulos.id)
   
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

def obtener_consecutivo(distrito, requis):
    # Obtener la última requisición del distrito basado en la fecha de creación
    ultima_requisicion = requis.filter(orden__staff__distrito=distrito, complete=True).order_by('-created_at').first()

    if not ultima_requisicion:
        # Si no hay ninguna requisición previa, devolver 1 (será el primer folio)
        return 1

    # Extraer el número de folio (después de la abreviatura del distrito)
    ultimo_numero_folio = int(ultima_requisicion.folio.replace(distrito.abreviado, ''))

    # Devolver el siguiente número
    return ultimo_numero_folio + 1

@login_required(login_url='user-login')
@perfil_seleccionado_required
def requisicion_detalle(request, pk):
    #Vista de creación de requisición
    productos = ArticulosparaSurtir.objects.filter(articulos__orden__id = pk, requisitar= True)
    orden = Order.objects.get(id = pk)
    pk = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk)
    requisiciones = Requis.objects.all()
    requi, created = requisiciones.get_or_create(complete=False, orden=orden)
    requis = requisiciones.filter(orden__distrito = orden.distrito, complete = True)
    # Extraemos solo los números de los folios del distrito
    last_requi = requis.order_by('-folio').first()
    if last_requi:
        folio = last_requi.folio + 1
    else:
        folio = 1
    abrev = usuario.distritos.abreviado
    folio_preview = str(abrev)+ str(folio)
    #for producto in productos:
    productos_requisitados = ArticulosRequisitados.objects.filter(req = requi)

    form = RequisForm()


    if request.method == 'POST':
        form = RequisForm(request.POST, instance = requi)
        if form.is_valid():
            requi = form.save(commit=False)
            requi.complete = True
            orden.requisitado = True
            conteo_pendientes_requisitar = productos.filter(requisitar = True).count()
            if conteo_pendientes_requisitar > 0: #cuento cuantos productos están pendientes por requisitar 
                orden.requisitado = False
            else:
                orden.requisitado = True
            for producto in productos:
                producto.seleccionado = False
                producto.save()
                #if producto.requisitar == False:
                #    orden.requisitado = False
                #    orden.save()
            if productos_requisitados:
                #folio_consecutivo = obtener_consecutivo(usuario.distrito, requisiciones)
                requi.folio = folio
                requi.save()
                form.save()
                orden.save()
                messages.success(request,f'Has realizado la requisición {requi.folio} con éxito')
                return redirect('solicitud-autorizada-orden')
            else:
                messages.error(request,'No se puede crear la requisición debido a que no hay productos agregados')
        else:
            errores = form.errors.as_data()
            messages.error(request,f'El formulario no es válido, {errores}')


    context = {
        'productos': productos,
        'productos_requisitados':productos_requisitados,
        'orden': orden,
        'folio':folio_preview,
        'requi':requi,
        'form':form,
        }

    return render(request,'requisiciones/detalle_requisitar_editar.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def requisicion_autorizar(request, pk):
    #usuario = request.user.id
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    #perfil = Profile.objects.get(staff__id=usuario)
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
                f'Estimado {requi.orden.staff.staff.staff.first_name} {requi.orden.staff.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requi.orden.folio}| Req: {requi.folio} ha sido autorizada,\n por {requi.requi_autorizada_por.staff.first_name} {requi.requi_autorizada_por.staff.last_name}.\n El siguiente paso del sistema: Generación de OC \n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
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
                f'Estimado {requis.orden.staff.staff.first_name} {requis.orden.staff.staff.last_name},\n Estás recibiendo este correo porque tu solicitud: {requis.orden.folio}| Req: {requis.folio} ha sido rechazada,\n por {requis.autorizada_por.staff.first_name} {requis.autorizada_por.staff.last_name} por el siguiente motivo: \n " {requis.comentario_compras} ".\n\n Este mensaje ha sido automáticamente generado por SAVIA X',
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
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Solicitud
    c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    c.rect(20,575,565,2, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,755,'Solicitud')
    c.setLineWidth(.3) #Grosor
    c.line(20,caja_proveedor-8,20,575) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(585,caja_proveedor-8,585,575) #Linea 2 contorno
    c.drawInlineImage('static/images/logo vordtec_documento.png',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    #c.drawString(120,caja_proveedor,'Infor')
    c.drawString(300,caja_proveedor, 'Detalles')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(30,caja_proveedor-20,'Solicitó:')
    c.drawString(30,caja_proveedor-40,'Distrito:')
    c.drawString(30,caja_proveedor-60,'Proyecto')
    c.drawString(30,caja_proveedor-80,'Subproyecto:')
    c.drawString(30,caja_proveedor-100,'Fecha:')
    
    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_proveedor-20,'FOLIO:')
    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_proveedor-20, orden.folio)

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(100,caja_proveedor-20, orden.staff.staff.first_name+' '+ orden.staff.staff.last_name)
    c.drawString(100,caja_proveedor-40, orden.staff.distrito.nombre)
    c.drawString(100,caja_proveedor-60, orden.proyecto.nombre)
    c.drawString(100,caja_proveedor-80, orden.subproyecto.nombre)
    c.drawString(100,caja_proveedor-100, orden.approved_at.strftime("%d/%m/%Y"))

    #Create blank list
    data =[]

    data.append(['''Código''', '''Nombre''', '''Cantidad''','''Comentario'''])


    high = 540
    for producto in productos:
        data.append([producto.producto.producto.codigo, producto.producto.producto.nombre,producto.cantidad, producto.comentario])
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

    c.setFillColor(black)
    width, height = letter
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]

    if orden.comentario is not None:
        comentario = orden.comentario
    else:
        comentario = "No hay comentarios"

    options_conditions_paragraph = Paragraph(comentario, styleN)
    # Crear un marco (frame) en la posición específica
    frame = Frame(50, 0, width, high-50, id='normal')

    # Agregar el párrafo al marco
    frame.addFromList([options_conditions_paragraph], c)
    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)

    table = Table(data, colWidths=[1.2 * cm, 12 * cm, 1.5 * cm, 5.2 * cm,])
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
    table.setStyle(table_style)

    #pdf size
    table.wrapOn(c, width, height)
    table.drawOn(c, 20, high)

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='reporte_' + str(orden.folio) +'.pdf')

def reporte_entradas(request):
    entradas = EntradaArticulo.objects.filter(entrada__completo = True, articulo_comprado__producto__producto__articulos__producto__producto__servicio = False)
    myfilter = EntradasFilter(request.GET, queryset=entradas)
    entradas = myfilter.qs

    #Set up pagination
    p = Paginator(entradas, 50)
    page = request.GET.get('page')
    entradas_list = p.get_page(page)

    if request.method == "POST" and 'btnExcel' in request.POST:

        return convert_entradas_to_xls(entradas)


    context = {
        'entradas_list':entradas_list,
        'entradas':entradas,
        'myfilter':myfilter,
        }

    return render(request,'requisiciones/reporte_entradas.html', context)

def reporte_salidas(request):
    salidas = Salidas.objects.all().order_by('-vale_salida')
    myfilter = SalidasFilter(request.GET, queryset=salidas)
    salidas = myfilter.qs
    salidas_filtradas = salidas.filter(producto__articulos__producto__producto__servicio = False)

    if request.method == "POST" and 'btnExcel' in request.POST:
        return convert_salidas_to_xls(salidas_filtradas)
    
     #Set up pagination
    p = Paginator(salidas, 50)
    page = request.GET.get('page')
    salidas_list = p.get_page(page)


    context = {
        'salidas':salidas,
        'salidas_list':salidas_list,
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
    number_style = NamedStyle(name='number_style', number_format='#,##0.00')
    number_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(number_style)

    columns = ['Folio','Solicitante','Proyecto','Subproyecto','Código','Artículo','Creado','Cantidad']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = productos.values_list(
        'articulos__orden__folio',
        Concat('articulos__orden__staff__staff__first_name',Value(' '),'articulos__orden__staff__staff__last_name'),
        'articulos__orden__proyecto__nombre',
        'articulos__orden__subproyecto__nombre',
        'articulos__producto__producto__codigo',
        'articulos__producto__producto__nombre',
        'articulos__orden__approved_at',
        'cantidad')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            if col_num == 6:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 7 or col_num == 4:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = number_style
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
    ws = wb.create_sheet(title='Entradas')
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

    columns = ['Folio Solicitud','Fecha','Solicitante','Proyecto','Subproyecto','Código','Articulo','Cantidad','Precio']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia V2. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style

    rows = entradas.values_list('entrada__oc__req__orden__id','created_at',Concat('entrada__oc__req__orden__staff__staff__first_name',Value(' '),'entrada__oc__req__orden__staff__staff__last_name'),
                        'entrada__oc__req__orden__proyecto__nombre','entrada__oc__req__orden__subproyecto__nombre','articulo_comprado__producto__producto__articulos__producto__producto__codigo',
                        'articulo_comprado__producto__producto__articulos__producto__producto__nombre','cantidad','articulo_comprado__precio_unitario')

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
    ws = wb.create_sheet(title='Salidas')
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
    number_style = NamedStyle(name='number_style', number_format='#,##0.00')
    number_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(number_style)

    columns = ['Folio Solicitud','Fecha','Solicitante','Proyecto','Subproyecto','Área','Código','Articulo','Material recibido por','Cantidad','Precio','Total']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA VORDTEC. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Grupo Vordcab S.A. de C.V.}')).style = messages_style
    

    rows = salidas.values_list(
        'producto__articulos__orden__folio',
        'created_at',
        Concat('producto__articulos__orden__staff__staff__first_name',Value(' '),'producto__articulos__orden__staff__staff__last_name'),
        'producto__articulos__orden__proyecto__nombre',
        'producto__articulos__orden__subproyecto__nombre',
        'producto__articulos__orden__area__nombre',
        'producto__articulos__producto__producto__codigo',
        'producto__articulos__producto__producto__nombre',
        Concat('vale_salida__material_recibido_por__staff__first_name',Value(' '),'vale_salida__material_recibido_por__staff__last_name'),
        'cantidad',
        Case(
            When(precio__gt = 0, then='precio'),
            When(producto__precio__gt = 0, then='producto__precio'),
            default='producto__articulos__producto__price',
        )
    )

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 1:
                value = (row[col_num]).date()
                (ws.cell(row = row_num, column = col_num+1, value=value)).style = date_style
            if col_num == 9:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = number_style
            if col_num == 10:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
        ws.cell(row=row_num, column=len(row) + 1, value=f'=J{row_num} * K{row_num}').style = money_style
    
    (ws.cell(column = columna_max , row = 3, value=f'=SUM(L2:L{row_num})')).style = money_resumen_style

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
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 6

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
        producto_nombre = Paragraph(producto.producto.articulos.producto.producto.nombre, styles["BodyText"])
        data.append([producto.producto.articulos.producto.producto.codigo, producto_nombre, producto.cantidad, producto.producto.articulos.producto.producto.unidad, producto.precio, producto.precio * producto.cantidad])
        high = high - 18
   
    c.setFillColor(black)
    c.setFont('Helvetica',8)
    proyecto_y = 485 if high > 500 else high - 30

    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(20,proyecto_y - 5 ,250,20, fill=True, stroke=False) #3ra linea azul
    c.setFillColor(black)
    c.setFont('Helvetica',7)


    c.setFillColor(white)
    c.setLineWidth(.1)
    c.setFont('Helvetica-Bold',10)
    c.drawCentredString(70,proyecto_y,'Proyecto')
    c.drawCentredString(165,proyecto_y,'Subproyecto')

    c.setFont('Helvetica',8)
    c.setFillColor(black)
    c.drawCentredString(70,proyecto_y - 15, str(vale.solicitud.proyecto.nombre))
    c.drawCentredString(165,proyecto_y - 15, str(vale.solicitud.subproyecto.nombre))


    c.setFillColor(black)
    c.setFont('Helvetica',8)
    #c.line(135,high-200,215, high-200) #Linea de Autorizacion
    c.drawCentredString(150,proyecto_y - 30,'Entregó')
    c.drawCentredString(150,proyecto_y - 40, vale.almacenista.staff.first_name +' '+vale.almacenista.staff.last_name)

    c.line(370,proyecto_y - 20,430, proyecto_y - 20)
    c.drawCentredString(400,proyecto_y - 30,'Recibió')
    c.drawCentredString(400,proyecto_y - 40, vale.material_recibido_por.staff.first_name +' '+vale.material_recibido_por.staff.last_name)


    #c.line(240, high-200, 310, high-200)
    c.drawCentredString(280,proyecto_y - 30,'Autorizó')
    c.drawCentredString(280,proyecto_y - 40, vale.solicitud.staff.staff.first_name + ' ' + vale.solicitud.staff.staff.last_name)

    c.setFont('Helvetica',10)
    c.setFillColor(prussian_blue)
    c.setFont('Helvetica', 9)
    c.setFillColor(black)

    c.setFillColor(prussian_blue)
    c.rect(20,proyecto_y - 65,565,20, fill=True, stroke=False)
    c.setFillColor(white)

    width, height = letter
    table = Table(data, colWidths=[1.5 * cm, 10.5 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm])
    table.setStyle(TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 10),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 20, high)
    c.save()
    c.showPage()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='vale_salida_'+str(vale.id) +'.pdf')