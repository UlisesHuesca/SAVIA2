from django.shortcuts import render, redirect
from dashboard.models import Inventario, Order, ArticulosOrdenados, ArticulosparaSurtir, Inventario_Batch, Marca, Product, Tipo_Orden
from requisiciones.models import Requis, ArticulosRequisitados, ValeSalidas
from compras.models import Compra
from tesoreria.models import Pago
from solicitudes.models import Subproyecto, Operacion, Proyecto
from entradas.models import EntradaArticulo, Entrada
from .forms import InventarioForm, OrderForm, Inv_UpdateForm, Inv_UpdateForm_almacenista, ArticulosOrdenadosForm
from dashboard.forms import Inventario_BatchForm
from user.models import Profile, Distrito, Almacen
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
from django.db.models import Sum
from .filters import InventoryFilter, SolicitudesFilter, SolicitudesProdFilter, InventarioFilter
from django.contrib import messages
# Import Pagination Stuff
from django.core.paginator import Paginator
from datetime import date, datetime
# Import Excel Stuff
from django.db.models.functions import Concat
from django.db.models import Value
from django.contrib import messages
from django.db.models import Sum
from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt
from django.db.models import F
import csv
import ast
from django.core.mail import EmailMessage
# Create your views here.


#Respuesta de Json

#def product_edit(request):
#    return render(request,'solicitud/product_edit.html')

def updateItem(request):
    data= json.loads(request.body)
    productId = data['productId']
    action = data['action']

    usuario = Profile.objects.get(staff__id=request.user.id)
    producto = Inventario.objects.get(id=productId)
    tipo = Tipo_Orden.objects.get(tipo ='normal')
    order, created = Order.objects.get_or_create(staff=usuario, complete=False, tipo = tipo, distrito = usuario.distrito)

    orderItem, created = ArticulosOrdenados.objects.get_or_create(orden = order, producto= producto)

    if action == 'add':
        orderItem.cantidad = (orderItem.cantidad + 1)
        message = f"Item was added: {orderItem}"
        orderItem.save()
    elif action == 'remove':
        orderItem.delete()
        message = f"Item was removed: {orderItem}"

    return JsonResponse(message, safe=False)

def updateItemRes(request):
    data= json.loads(request.body)
    productId = data['productId']
    action = data['action']

    usuario = Profile.objects.get(id=request.user.id)
    producto = Inventario.objects.get(id=productId)
    tipo = Tipo_Orden.objects.get(tipo ='resurtimiento')
    order, created = Order.objects.get_or_create(staff = usuario, complete = False, tipo=tipo, distrito = usuario.distrito)
    orderItem, created = ArticulosOrdenados.objects.get_or_create(orden = order, producto= producto)

    if action == 'add':
        orderItem.cantidad = (orderItem.cantidad + 1)
        message = f"Item was added: {orderItem}"
        orderItem.save()
    elif action == 'remove':
        orderItem.delete()
        message = f"Item was removed: {orderItem}"

    return JsonResponse(message, safe=False)

#Vista de seleccion de productos, requiere login
@login_required(login_url='user-login')
def product_selection_resurtimiento(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    tipo = Tipo_Orden.objects.get(tipo ='resurtimiento')
    order, created = Order.objects.get_or_create(staff=usuario, complete=False, tipo=tipo)
    productos = Inventario.objects.filter(cantidad__lt =F('minimo'))
    cartItems = order.get_cart_quantity
    myfilter=InventoryFilter(request.GET, queryset=productos)
    productos = myfilter.qs


    context= {
        'myfilter': myfilter,
        'productos':productos,
        'productosordenadosres':cartItems,
        }
    return render(request, 'solicitud/product_selection_resurtimiento.html', context)


#Vista de seleccion de productos, requiere login
@login_required(login_url='user-login')
def product_selection(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    tipo = Tipo_Orden.objects.get(tipo ='normal')
    #order, created = Order.objects.get_or_create(staff = usuario, complete = False, tipo = tipo)
    order, created = Order.objects.get_or_create(staff = usuario, complete = False, tipo=tipo, distrito = usuario.distrito)
    productos = Inventario.objects.filter(complete=True)
    cartItems = order.get_cart_quantity
    myfilter=InventoryFilter(request.GET, queryset=productos)
    productos = myfilter.qs

    #Set up pagination
    p = Paginator(productos, 30)
    page = request.GET.get('page')
    productos_list = p.get_page(page)


    context= {
        'myfilter': myfilter,
        'productos_list':productos_list,
        'productos':productos,
        'productosordenados':cartItems,
        }
    return render(request, 'solicitud/product_selection.html', context)

#Vista para crear solicitud
@login_required(login_url='user-login')
def checkout(request):
    usuario = Profile.objects.get(staff=request.user)

    #Tengo que revisar primero si ya existe una orden pendiente del usuario
    orders = Order.objects.filter(staff__distrito = usuario.distrito)
    #consecutivo = orders.count() + 1
    proyectos = Proyecto.objects.filter(activo=True)
    subproyectos = Subproyecto.objects.all()
    tipo = Tipo_Orden.objects.get(tipo ='normal')

    order, created = Order.objects.get_or_create(staff = usuario, complete = False, tipo=tipo, distrito = usuario.distrito)

    if usuario.tipo.supervisor:
        supervisores = Profile.objects.filter(staff=request.user)
        order.supervisor = usuario
    else:
        supervisores = Profile.objects.filter(tipo__supervisor = True)

    if usuario.tipo.superintendente:
        superintendentes = Profile.objects.filter(staff=request.user)
        order.superintendente = usuario
    else:
        superintendentes = Profile.objects.filter(tipo__superintendente = True)


    form = OrderForm(instance = order)


    if order.staff != usuario:
        productos = None
        cartItems = 0
    else:
        productos = order.articulosordenados_set.all()
        cartItems = order.get_cart_quantity


    if request.method =='POST':
        form = OrderForm(request.POST, instance=order)
        order.created_at = date.today()
        order.created_at_time = datetime.now().time()

        if usuario.tipo.supervisor == True:
            for producto in productos:
                # We fetch inventory product corresponding to product (that's why we use product.id)
                # We create a new product line in a new database to control the ArticlestoDeliver (ArticulosparaSurtir)
                prod_inventario = Inventario.objects.get(id = producto.producto.id)
                ordensurtir , created = ArticulosparaSurtir.objects.get_or_create(articulos = producto)
                #cond:1 evalua si la cantidad en inventario es mayor que lo solicitado
                if prod_inventario.cantidad >= producto.cantidad and order.tipo.tipo == "normal":
                    prod_inventario.cantidad = prod_inventario.cantidad - producto.cantidad
                    prod_inventario.cantidad_apartada = producto.cantidad + prod_inventario.cantidad_apartada
                    prod_inventario._change_reason = f'Se modifica el inventario en view: autorizada_sol:{order.id} cond:1'
                    ordensurtir.cantidad = producto.cantidad
                    ordensurtir.precio = prod_inventario.price
                    ordensurtir.surtir = True
                    ordensurtir.requisitar = False
                    ordensurtir.save()
                    prod_inventario.save()
                elif producto.cantidad >= prod_inventario.cantidad and producto.cantidad > 0: #si la cantidad solicitada es mayor que la cantidad en inventario
                    ordensurtir.cantidad = prod_inventario.cantidad #lo que puedes surtir es igual a lo que tienes en el inventario
                    ordensurtir.precio = prod_inventario.price
                    ordensurtir.cantidad_requisitar = producto.cantidad - ordensurtir.cantidad #lo que falta por surtir
                    prod_inventario.cantidad_apartada = prod_inventario.cantidad_apartada + prod_inventario.cantidad
                    prod_inventario.cantidad = 0
                    if ordensurtir.cantidad > 0: #si lo que se puede surtir es mayor que 0
                        ordensurtir.surtir = True
                    ordensurtir.requisitar = True
                    order.requisitar = True
                    if producto.producto.producto.servicio == True:
                        requi, created = Requis.objects.get_or_create(complete = True, orden = order)
                        requitem, created = ArticulosRequisitados.objects.get_or_create(req = requi, producto = ordensurtir, cantidad = producto.cantidad)
                        requi.folio = str(usuario.distrito.abreviado)+str(order.id).zfill(4)
                        order.requisitar=False
                        ordensurtir.requisitar=False
                        requi.save()
                        requitem.save()
                    prod_inventario.save()
                    ordensurtir.save()
                    order.save()
            order.autorizar = True
            order.approved_at = date.today()
            order.approved_at_time = datetime.now().time()
            email = EmailMessage(
                f'Solicitud Autorizada {order.id}',
                f'Estás recibiendo este correo porque ha sido aprobada la solicitud {order.id}\n Este mensaje ha sido automáticamente generado por SAVIA X',
                'savia@vordtec.com',
                [order.staff.staff.email],
                )
            #email.attach(f'OC_folio:{compra.folio}.pdf',archivo_oc,'application/pdf')
            email.send()
            order.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)

        abrev= usuario.distrito.abreviado
        order.folio = str(abrev) + str(order.id).zfill(4)
        for orden in orders:
            if orden.folio == order.folio:
                order.folio = str(abrev) + str(order.id).zfill(4)
        if form.is_valid():
            order.complete = True
            order.save()
            form.save()
            messages.success(request, f'La solicitud {order.folio} ha sido creada')
            cartItems = '0'
            return redirect('solicitud-matriz')


    context= {
        'form':form,
        'productos':productos,
        'orden':order,
        'productosordenados':cartItems,
        'supervisores':supervisores,
        'superintendentes':superintendentes,
        'proyectos':proyectos,
        'subproyectos':subproyectos,
    }
    return render(request, 'solicitud/checkout.html', context)

def product_quantity_edit(request, pk):
    item = ArticulosOrdenados.objects.get(id= pk)
    form= ArticulosOrdenadosForm(instance = item)

    if request.method == 'POST':
        form = ArticulosOrdenadosForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204)

    context = {
        'form': form,
        'item':item,
        }

    return render(request, 'solicitud/product_quantity_edit.html', context)

#Vista para crear solicitud
@login_required(login_url='user-login')
def checkout_resurtimiento(request):
    usuario = Profile.objects.get(staff=request.user)
    #Tengo que revisar primero si ya existe una orden pendiente del usuario
    superintendentes = Profile.objects.filter(tipo__superintendente=True)
    subproyectos = Subproyecto.objects.all()
    orders = Order.objects.filter(staff__distrito = usuario.distrito, complete = False)
    #consecutivo = orders.count()+1



    tipo = Tipo_Orden.objects.get(tipo ='resurtimiento')
    order, created = Order.objects.get_or_create(staff = usuario, complete = False, tipo=tipo, distrito = usuario.distrito)
    almacen = Operacion.objects.get(nombre = "ALMACEN")


    if usuario.tipo.almacen:
        supervisores = Profile.objects.filter(staff=request.user)
        order.supervisor = usuario
        order.area = almacen

    if order.staff != usuario:
        productos = None
        cartItems = 0
    else:
        productos = order.articulosordenados_set.all()
        cartItems = order.get_cart_quantity

    form = OrderForm(instance = order)


    if request.method =='POST':
        form = OrderForm(request.POST, instance=order)
        order.complete = True
        order.created_at = date.today()
        order.created_at_time = datetime.now().time()
        abrev= usuario.distrito.abreviado
        order.folio = str(abrev) + str(order.id).zfill(4)

        requi, created = Requis.objects.get_or_create(complete = True, orden = order)
        requi.folio = str(abrev) + str(requi.id).zfill(4)
        requi.save()
        for producto in productos:
            ordensurtir , created = ArticulosparaSurtir.objects.get_or_create(articulos = producto)
            requitem, created = ArticulosRequisitados.objects.get_or_create(req = requi, producto= ordensurtir, cantidad = producto.cantidad)
            ordensurtir.requisitar = True
            ordensurtir.cantidad_requisitar = producto.cantidad
            ordensurtir.save()
            requitem.save()
        order.requisitar = True
        order.autorizar = True
        order.approved_at = date.today()
        order.approved_at_time = datetime.now().time()
        requi.save()
        order.save()
        abrev= usuario.distrito.abreviado
        order.folio = str(abrev) + str(order.id).zfill(4)
        if form.is_valid():
            order.save()
            form.save()
            messages.success(request, f'La solicitud {order.folio} ha sido creada')
            cartItems = '0'
            return redirect('solicitud-matriz')

    context= {
        'form':form,
        'productos':productos,
        'orden':order,
        'productosordenadosres':cartItems,
        'supervisores':supervisores,
        'superintendentes':superintendentes,
        'subproyectos':subproyectos,
    }
    return render(request, 'solicitud/checkout_resurtimiento.html', context)


#Vista para crear solicitud
@login_required(login_url='user-login')
def checkout_editar(request, pk):

    order = Order.objects.get(id=pk)

    usuario = Profile.objects.get(id=request.user.id)

    productos = order.articulosordenados_set.all()
    cartItems = order.get_cart_quantity
    form = OrderForm(instance=order, distrito = usuario.distrito)


    if request.method =='POST':
        form = OrderForm(request.POST, instance=order, distrito = usuario.distrito)
        order.complete = True
        if form.is_valid():
            form.save()
            cartItems = '0'
            return redirect('solicitud-matriz')

    context= {
        'form':form,
        'productos':productos,
        'orden':order,
        'productosordenados':cartItems,
    }
    return render(request, 'solicitud/checkout.html', context)

@login_required(login_url='user-login')
def solicitud_pendiente(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)


    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    if perfil.tipo.superintendente == True:
        ordenes = Order.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    elif perfil.tipo.supervisor == True:
        ordenes = Order.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    else:
        ordenes = Order.objects.filter(complete=True, staff = perfil).order_by('-folio')

    myfilter=SolicitudesFilter(request.GET, queryset=ordenes)
    ordenes = myfilter.qs

    #Set up pagination
    p = Paginator(ordenes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    if request.method =='POST' and 'btnExcel' in request.POST:

        return convert_excel_solicitud_matriz(ordenes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'solicitud/solicitudes_pendientes.html',context)

@login_required(login_url='user-login')
def solicitud_matriz(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)


     #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    if perfil.tipo.superintendente == True:
        ordenes = Order.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    elif perfil.tipo.supervisor == True:
        ordenes = Order.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    else:
        ordenes = Order.objects.filter(complete=True, staff = perfil).order_by('-folio')

    myfilter=SolicitudesFilter(request.GET, queryset=ordenes)
    ordenes = myfilter.qs

    #Set up pagination
    p = Paginator(ordenes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    if request.method =='POST' and 'btnExcel' in request.POST:

        return convert_excel_solicitud_matriz(ordenes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'solicitud/solicitudes_creadas.html',context)


@login_required(login_url='user-login')
def solicitud_matriz_productos(request):

    perfil = Profile.objects.get(staff__id=request.user.id)

     #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    if perfil.tipo.superintendente == True:
        productos = ArticulosOrdenados.objects.filter(orden__complete=True, orden__staff__distrito=perfil.distrito).order_by('-orden__folio')
    elif perfil.tipo.supervisor == True:
        productos = ArticulosOrdenados.objects.filter(orden__complete=True, orden__staff__distrito=perfil.distrito, orden__supervisor=perfil).order_by('-orden__folio')
    else:
        productos = ArticulosOrdenados.objects.filter(orden__complete=True, orden__staff = perfil).order_by('-orden__folio')

    myfilter=SolicitudesProdFilter(request.GET, queryset=productos)
    productos = myfilter.qs
    perfil = Profile.objects.get(staff__id=request.user.id)


    #Set up pagination
    p = Paginator(productos, 15)
    page = request.GET.get('page')
    productos_list = p.get_page(page)

    if request.method =='POST' and 'btnExcel' in request.POST:

        return convert_excel_solicitud_matriz_productos(productos)

    context= {
        'productos':productos_list,
        'myfilter':myfilter,
        }
    return render(request, 'solicitud/solicitudes_creadas_productos.html',context)



@login_required(login_url='user-login')
def inventario(request):
    perfil = Profile.objects.get(staff=request.user)
    existencia = Inventario.objects.filter(complete=True, producto__servicio = False, producto__gasto = False).order_by('producto__codigo')
    entries = EntradaArticulo.objects.all()
    entradas = entries.annotate(Sum('cantidad'))
    for item in existencia:
        query = entries.filter(articulo_comprado__producto__producto__articulos__producto = item, agotado = False)
        if query.exists():
            cantidad = query.aggregate(Sum('cantidad_por_surtir'))
            item.cantidad_entradas = cantidad['cantidad_por_surtir__sum']
            item.save()

    if perfil.tipo.nombre == 'Admin' or perfil.tipo.nombre == 'SuperAdm':
        perfil_flag = True
    else:
        perfil_flag = False



    #apartado = ArticulosparaSurtir.objects.values('articulos__producto__producto__codigo').annotate(cantidad_total=Sum('cantidad'))
    #Este es el metodo que utilicé para multiplicar 2 columnas de un mismo modelo y devolver el total
    list_inv = existencia.values_list('cantidad', 'cantidad_apartada','price')
    valor_inv_raw = sum((t[0] + t[1])*t[2] for t in list_inv)
    valor_inv = valor_inv_raw

    myfilter = InventarioFilter(request.GET, queryset=existencia)
    existencia = myfilter.qs

    #Set up pagination
    p = Paginator(existencia, 50)
    page = request.GET.get('page')
    existencia_list = p.get_page(page)




    if request.method =='POST' and 'btnExcel' in request.POST:
        return convert_excel_inventario(existencia, valor_inv_raw )

    context = {
        'perfil_flag':perfil_flag,
        'existencia': existencia,
        'myfilter': myfilter,
        'existencia_list':existencia_list,
        'entradas':entradas,
        'valor_inv': valor_inv,
        }

    return render(request,'dashboard/inventario.html', context)

@login_required(login_url='user-login')
def upload_batch_inventario(request):

    form = Inventario_BatchForm(request.POST or None, request.FILES or None)


    if form.is_valid():
        form.save()
        form = Inventario_BatchForm()
        inventario_list = Inventario_Batch.objects.get(activated = False)

        f = open(inventario_list.file_name.path, 'r')
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if Product.objects.filter(codigo=row[0]):
                producto = Product.objects.get(codigo=row[0])
                if Distrito.objects.filter(nombre = row[1]):
                    distrito = Distrito.objects.get(nombre = row[1])
                    if Almacen.objects.filter(nombre = row[2]):
                        almacen = Almacen.objects.get(nombre = row[2])
                        inventario = Inventario(producto=producto,distrito=distrito, almacen=almacen, ubicacion=row[3], estante=row[4], cantidad=row[5], price=row[6], minimo=row[7],comentario=row[8],complete=True)
                        inventario.save()
                        #marcas_str = row[2]
                        #marcas_names = ast.literal_eval(marcas_str)
                        #marcas_names = map(str.lower, marcas_names) # normalize them, all lowercase
                        #marcas_names = list(set(marcas_names)) # remove duplicates

                        #for marca in marcas_names:
                        #    marca, _ = Marca.objects.get_or_create(nombre=marca)
                        #    inventario.marca.add(marca)
                        #    inventario.save()
                    else:
                        messages.error(request,'El almacén no existe en la base de datos')
                else:
                     messages.error(request,'El distrito no existe en la base de datos')
            else:
                messages.error(request,f'El producto código:{row[0]} ya existe dentro de la base de datos')

        inventario_list.activated = True
        inventario_list.save()
    elif request.FILES:
        messages.error(request,'El formato no es CSV')




    context = {
        'form': form,
        }

    return render(request,'dashboard/upload_batch_inventario.html', context)




def inventario_add(request):
    #usuario = request.user.id
    perfil = Profile.objects.get(staff__id=request.user.id)

    #productos.exclude(id__in=existing)
    form = InventarioForm()
    #form.fields['producto'].queryset = productos


    if request.method =='POST':
        form = InventarioForm(request.POST)
        item = form.save(commit=False)
        item.complete = True
        item._change_reason = 'Se agrega producto el inventario en view: inventario_add'
        item.distrito = perfil.distrito
        if form.is_valid():
            form.save()
            item.save()
            return HttpResponse(status=204)
    #else:
        #form = InventarioForm()

    context = {
        'form': form,
        #'productos':productos,
        }

    return render(request,'dashboard/inventario_add.html',context)

@login_required(login_url='user-login')
def inventario_update_modal(request, pk):
    perfil = Profile.objects.get(staff=request.user)
    item = Inventario.objects.get(id=pk)



    if perfil.tipo.nombre == 'SuperAdm' or perfil.tipo.nombre == 'Admin':
        flag_perfil = True
    else:
        flag_perfil = False


    if request.method =='POST':
        if perfil.tipo.nombre == 'SuperAdm' or perfil.tipo.nombre == 'Admin':
            form = Inv_UpdateForm(request.POST, instance=item)
        else:
            form = Inv_UpdateForm_almacenista(request.POST, instance= item)
        if request.POST['comentario'] and 'btnUpdate' in request.POST:
            if form.is_valid():
                item = form.save(commit=False)
                item._change_reason = item.comentario +'. Se modifica inventario en view: inventario_update_modal'
                item.save()
                messages.success(request, f'El artículo {item.producto.codigo}:{item.producto.nombre} se ha actualizado exitosamente')
                return HttpResponse(status=204)
        else:
            messages.error(request, 'Debes agregar un comentario con respecto al cambio realizado')
    else:
        if perfil.tipo.nombre == 'SuperAdm' or perfil.tipo.nombre == 'Admin':
            form = Inv_UpdateForm(instance=item)
        else:
            form = Inv_UpdateForm_almacenista(instance= item)


    context = {
        'flag_perfil':flag_perfil,
        'form': form,
        'item':item,
        }

    return render(request,'dashboard/inventario_update_modal.html',context)


@login_required(login_url='user-login')
def historico_inventario(request):
    registros = Inventario.history.all()

    context = {
        'registros':registros,
        }

    return render(request,'dashboard/historico_inventario.html',context)


@login_required(login_url='user-login')
def inventario_delete(request, pk):
    item = Inventario.objects.get(id=pk)

    if request.method == 'POST':
        item.delete()
        return redirect('solicitud-inventario')

    return render(request,'dashboard/inventario_delete.html')

@login_required(login_url='user-login')
def solicitud_autorizacion(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    #usuario = request.user.id
    perfil = Profile.objects.get(staff__id=request.user.id)
    #perfil = Profile.objects.get(id=usuario)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    ordenes = Order.objects.filter(complete=True, autorizar=None, staff__distrito=perfil.distrito).order_by('-folio')
    ordenes = ordenes.filter(supervisor=perfil)
    myfilter=SolicitudesFilter(request.GET, queryset=ordenes)
    ordenes = myfilter.qs


    context= {
        'myfilter':myfilter,
        'ordenes':ordenes,
        #'perfil':perfil,
        }

    return render(request, 'autorizacion/solicitudes_pendientes_autorizacion.html',context)

def detalle_autorizar(request, pk):
    productos = ArticulosOrdenados.objects.filter(orden=pk)

    context = {
        'productos': productos,
     }
    return render(request,'autorizacion/detail.html', context)

@login_required(login_url='user-login')
def autorizada_sol(request, pk):
    usuario = request.user.id
    perfil = Profile.objects.get(staff__id=request.user.id)
    #perfil = Profile.objects.get(id=usuario)
    order = Order.objects.get(id = pk)
    productos = ArticulosOrdenados.objects.filter(orden = pk)
    requis = Requis.objects.filter(orden__staff__distrito = perfil.distrito)
    consecutivo = requis.count() + 1

    if request.method =='POST':
        #We go trough all the products one by one contained in the order
        for producto in productos:
            # We fetch inventory product corresponding to product (that's why we use product.id)
            # We create a new product line in a new database to control the ArticlestoDeliver (ArticulosparaSurtir)
            prod_inventario = Inventario.objects.get(id = producto.producto.id)
            ordensurtir , created = ArticulosparaSurtir.objects.get_or_create(articulos = producto)
            #cond:1 evalua si la cantidad en inventario es mayor que lo solicitado
            if prod_inventario.cantidad >= producto.cantidad and order.tipo.tipo == "normal":
                prod_inventario.cantidad = prod_inventario.cantidad - producto.cantidad
                prod_inventario.cantidad_apartada = producto.cantidad + prod_inventario.cantidad_apartada
                prod_inventario._change_reason = f'Se modifica el inventario en view: autorizada_sol:{order.id} cond:1'
                ordensurtir.cantidad = producto.cantidad
                ordensurtir.precio = prod_inventario.price
                ordensurtir.surtir = True
                ordensurtir.requisitar = False
                ordensurtir.save()
                prod_inventario.save()
            elif producto.cantidad >= prod_inventario.cantidad and producto.cantidad > 0 and order.tipo.tipo == "normal": #si la cantidad solicitada es mayor que la cantidad en inventario
                ordensurtir.cantidad = prod_inventario.cantidad #lo que puedes surtir es igual a lo que tienes en el inventario
                ordensurtir.precio = prod_inventario.price
                ordensurtir.cantidad_requisitar = producto.cantidad - ordensurtir.cantidad #lo que falta por surtir
                prod_inventario.cantidad_apartada = prod_inventario.cantidad_apartada + prod_inventario.cantidad
                prod_inventario.cantidad = 0
                if ordensurtir.cantidad > 0: #si lo que se puede surtir es mayor que 0
                    ordensurtir.surtir = True
                ordensurtir.requisitar = True
                order.requisitar = True
                prod_inventario.save()
                ordensurtir.save()
            elif prod_inventario.cantidad + prod_inventario.cantidad_entradas == 0 or order.tipo.tipo == "resurtimiento":
                ordensurtir.requisitar = True
                ordensurtir.cantidad_requisitar = producto.cantidad
                order.requisitar = True
                if producto.producto.producto.servicio == True:
                    requi, created = Requis.objects.get_or_create(complete = True, orden = order)
                    requitem, created = ArticulosRequisitados.objects.create(req = requi, producto= ordensurtir, cantidad = producto.cantidad)
                    requi.folio = str(usuario.distrito.abreviado)+str(order.id).zfill(4)
                    order.requisitar=False
                    ordensurtir.requisitar=False
                    requi.save()
                    requitem.save()
                ordensurtir.save()
                order.save()
        order.autorizar = True
        order.approved_at = date.today()
        order.approved_at_time = datetime.now().time()
        #send_mail(
        #    f'Solicitud Autorizada {order.folio}',
        #    f'{order.staff.staff.first_name}, la solicitud {order.folio} ha sido autorizada. Este mensaje ha sido automáticamente generado por SAVIA X',
        #    'saviax.vordcab@gmail.com',
        #    [order.staff.staff.email],
        #    )
        order.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)
        order.save()

        messages.success(request, f'{perfil.staff.first_name} has autorizado la solicitud {order.folio}')
        return redirect('solicitud-pendientes-autorizacion')


    context = {
        'orden': order,
        'productos': productos,
    }

    return render(request,'autorizacion/autorizada.html', context)

def cancelada_sol(request, pk):
    order = Order.objects.get(id = pk)
    productos = ArticulosOrdenados.objects.filter(orden = pk)

    if request.method =='POST':
        order.autorizar = False
        order.save()
        messages.error(request, f'La orden {order} ha sido cancelada')
        return redirect('solicitud-pendientes-autorizacion')


    context = {
        'orden': order,
        'productos': productos,
    }

    return render(request,'autorizacion/cancelada.html', context)


def status_sol(request, pk):
    solicitud = Order.objects.get(id = pk)
    product_solicitudes = ArticulosOrdenados.objects.filter(orden=pk)
    num_prod_sol= product_solicitudes.count

    try:
        requi = Requis.objects.get(orden = pk)
    except Requis.DoesNotExist:
        requi = None


    if requi != None:
        exist_req = True
        if not requi.autorizar:
            requi_cancelada = True
        else:
            requi_cancelada = False
        compras = Compra.objects.filter(req=requi)
        product_requis = ArticulosRequisitados.objects.filter(req=requi)
        num_prod_req = product_requis.count()
        if compras != None:
            pagos = Pago.objects.filter(oc__req = requi)
            #productos_comprados = ArticuloComprado.objects.filter(oc = compras)
            exist_oc=True
            if pagos:
                exist_pago=True
                entradas = Entrada.objects.filter(oc__req = requi)
                exist_entradas = False
                if entradas:
                    exist_entradas = True
                    articulos_entradas = EntradaArticulo.objects.filter(entrada__oc__req = requi)
                    exist_salidas = False
                    salidas = ValeSalidas.objects.filter(solicitud = solicitud)
                    if salidas:
                        exist_salidas = True
                    context = {
                        'salidas':salidas,
                        'exist_salidas': exist_salidas,
                        'solicitud': solicitud,
                        'exist_entradas': exist_entradas,
                        'entradas': entradas,
                        'articulos_entradas': articulos_entradas,
                        'product_solicitudes': product_solicitudes,
                        'num_prod_sol': num_prod_sol,
                        'product_requis':product_requis,
                        'requi': requi,
                        'exist_oc': exist_oc,
                        'exist_pago':exist_pago,
                        'num_prod_req': num_prod_req,
                        'compras':compras,
                        'pagos':pagos,
                        }
                else:
                    context = {
                        'solicitud': solicitud,
                        #'productos_comp': productos_comprados,
                        'product_solicitudes': product_solicitudes,
                        'num_prod_sol': num_prod_sol,
                        'product_requis':product_requis,
                        'requi': requi,
                        'exist_oc': exist_oc,
                        'exist_pago':exist_pago,
                        'exist_entradas':exist_entradas,
                        'num_prod_req': num_prod_req,
                        'compras':compras,
                        'pagos':pagos,
                        }
            else:
                exist_pago=False
                context = {
                    'solicitud': solicitud,
                    'exist_pago': exist_pago,
                    'product_solicitudes': product_solicitudes,
                    'num_prod_sol': num_prod_sol,
                    'product_requis':product_requis,
                    'requi': requi,
                    'num_prod_req': num_prod_req,
                    'exist_oc': exist_oc,
                    'compras':compras,
                }
        else:
            exist_oc = False
            context = {
            'solicitud': solicitud,
            'product_solicitudes': product_solicitudes,
            'num_prod_sol': num_prod_sol,
            'num_prod_req': num_prod_req,
            'requi': requi,
            'exist_req': exist_req,
            'exist_oc': exist_oc,
        }
    else:
        exist_req = False
        context = {
            'solicitud': solicitud,
            'product_solicitudes': product_solicitudes,
            'num_prod_sol': num_prod_sol,
            'exist_req': exist_req,
        }



    return render(request,'solicitud/detalle.html', context)


# AJAX
def load_subproyectos(request):

    proyecto_id = request.GET.get('proyecto_id')
    subproyectos = Subproyecto.objects.filter(proyecto_id = proyecto_id)

    return render(request, 'solicitud/subproyecto_dropdown_list_options.html',{'subproyectos': subproyectos})

def convert_excel_inventario(existencia, valor_inventario):
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
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)

    columns = ['Código','Producto','Distrito','Cantidad','Cantidad Apartada','Precio']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        if col_num == 0:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 10
        if col_num== 1:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30
        else:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 15


    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia X. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    (ws.cell(column = columna_max, row = 3, value='Inventario Costo Total:')).style = messages_style
    (ws.cell(column = columna_max +1, row=3, value = valor_inventario)).style = money_resumen_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20
    ws.column_dimensions[get_column_letter(columna_max + 1)].width = 20

    rows = existencia.values_list('producto__codigo','producto__nombre','distrito__nombre','cantidad','cantidad_apartada','price')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            if col_num > 2:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = body_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
            if col_num <= 2:
                (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style

    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

def convert_excel_solicitud_matriz_productos(productos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Solicitudes_por_producto_' + str(dt.date.today())+'.xlsx'
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

    columns = ['Folio','Solicitante','Proyecto','Subproyecto','Operación','Cantidad','Código', 'Producto','Creado']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 4 or col_num == 7:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25



    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia X. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20

    rows = productos.values_list('orden__id',Concat('orden__staff__staff__first_name',Value(' '),'orden__staff__staff__last_name'),'orden__proyecto__nombre','orden__subproyecto__nombre',
                                'orden__operacion__nombre','cantidad','producto__producto__codigo','producto__producto__nombre','orden__created_at')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = body_style
            if col_num == 8:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

def convert_excel_solicitud_matriz(ordenes):
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
    money_style = NamedStyle(name='money_style', number_format='$ #,##0.00')
    money_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(money_style)
    money_resumen_style = NamedStyle(name='money_resumen_style', number_format='$ #,##0.00')
    money_resumen_style.font = Font(name ='Calibri', size = 14, bold = True)
    wb.add_named_style(money_resumen_style)

    columns = ['Folio','Solicitante','Proyecto','Subproyecto','Operación','Creado']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25

    columna_max = len(columns)+2

    (ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por Savia X. UH}')).style = messages_style
    (ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}')).style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 20

    rows = ordenes.values_list('id',Concat('staff__staff__first_name',Value(' '),'staff__staff__last_name'),'proyecto__nombre','subproyecto__nombre',
                                'area__nombre','created_at')

    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 5:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)