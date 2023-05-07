from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Product, Subfamilia, Order, Products_Batch, Familia, Unidad
from compras.models import Proveedor, Proveedor_Batch, Proveedor_Direcciones_Batch, Proveedor_direcciones, Estatus_proveedor, Estado
from solicitudes.models import Subproyecto, Proyecto
from requisiciones.models import Salidas, ValeSalidas
from user.models import Profile, Distrito, Banco
from .forms import ProductForm, Products_BatchForm, AddProduct_Form, Proyectos_Form, ProveedoresForm, Proyectos_Add_Form, Proveedores_BatchForm, ProveedoresDireccionesForm, Proveedores_Direcciones_BatchForm, Subproyectos_Add_Form
from django.contrib.auth.models import User
from .filters import ProductFilter, ProyectoFilter, ProveedorFilter, SubproyectoFilter
from django.contrib import messages
import csv
from django.core.paginator import Paginator
from django.db.models import Sum
#import decimal

# Create your views here.
@login_required(login_url='user-login')
def index(request):
    usuario = Profile.objects.get(staff=request.user)
    #usuario = Profile.objects.get(id=request.user.id)
    #vale_salidas = ValeSalidas.objects.filter(material_recibido_por = usuario)
    #salidas = Salidas.objects.filter(vale_salida = vale_salidas) | No jala me marca que la búsqueda por un valor exacto debe estar limtado a un resultado no debería ser porque hay 3
    subproyectos = Subproyecto.objects.all()
    #productos = Inventario.objects.filter(producto = salidas.producto.articulos.producto.producto)
    labels = []
    data = []
    subproy = []
    gast = []
    pres = []


    #for salida in salidas:
    #    if salida.producto.articulos.producto.producto.nombre not in labels:
    #        labels.append(salida.producto.articulos.producto.producto.nombre)
    #        data.append(salida.cantidad)
    #    else:
    #        index = labels.index(salida.producto.articulos.producto.producto.nombre)
    #        data[index] = data[index]+salida.cantidad

    for subproyecto in subproyectos:
        subproy.append(subproyecto.nombre)
        gast.append(format(subproyecto.gastado, '.2f'))
        pres.append(format(subproyecto.presupuesto, '.2f'))

    context= {
        #'usuario':usuario,
        'labels':labels,
        'data':data,
        'subproyecto':subproy,
        'gastado':gast,
        }
    return render(request,'dashboard/index.html',context)

@login_required(login_url='user-login')
def proyectos(request):
    proyectos = Proyecto.objects.all()

    myfilter=ProyectoFilter(request.GET, queryset=proyectos)
    proyectos = myfilter.qs

    #Set up pagination
    p = Paginator(proyectos, 50)
    page = request.GET.get('page')
    proyectos_list = p.get_page(page)

    context = {
        'proyectos':proyectos,
        'proyectos_list':proyectos_list,
        'myfilter':myfilter,
        }

    return render(request,'dashboard/proyectos.html',context)

@login_required(login_url='user-login')
def subproyectos(request, pk):
    proyecto = Proyecto.objects.get(id=pk)
    subproyectos = Subproyecto.objects.filter(proyecto=proyecto)

    myfilter=SubproyectoFilter(request.GET, queryset=subproyectos)
    subproyectos = myfilter.qs

    #Set up pagination
    p = Paginator(subproyectos, 50)
    page = request.GET.get('page')
    subproyectos_list = p.get_page(page)

    context = {
        'proyecto':proyecto,
        'subproyectos':subproyectos,
        'subproyectos_list':subproyectos_list,
        'myfilter':myfilter,
        }

    return render(request,'dashboard/subproyectos.html',context)



@login_required(login_url='user-login')
def proyectos_edit(request, pk):

    proyecto = Proyecto.objects.get(id=pk)

    if request.method =='POST':
        form = Proyectos_Form(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request,f'Has actualizado correctamente el proyecto {proyecto.nombre}')
            return redirect('configuracion-proyectos')
    else:
        form = Proyectos_Form(instance=proyecto)


    context = {
        'form': form,
        'proyecto':proyecto,
        }
    return render(request,'dashboard/proyectos_edit.html', context)

@login_required(login_url='user-login')
def proveedor_direcciones(request, pk):

    direcciones = Proveedor_direcciones.objects.filter(nombre__id=pk)

    #if request.method =='POST':
        #form = Proyectos_Form(request.POST, instance=proyecto)
     #   if form.is_valid():
      #      form.save()
            #messages.success(request,f'Has actualizado correctamente el proyecto {proyecto.nombre}')
       #     return redirect('configuracion-proyectos')
    #else:
        #form = Proyectos_Form(instance=proyecto)


    context = {
        #'form': form,
        'direcciones':direcciones,
        }
    return render(request,'dashboard/direcciones_proveedor.html', context)

@login_required(login_url='user-login')
def proyectos_add(request):


    form = Proyectos_Add_Form()

    if request.method =='POST':
        form = Proyectos_Add_Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'Has agregado correctamente el proyecto')
            return redirect('configuracion-proyectos')
    else:
        form = Proyectos_Add_Form()

    context = {
        'form': form,
        }

    return render(request,'dashboard/proyectos_add.html',context)

@login_required(login_url='user-login')
def subproyectos_add(request, pk):
    proyecto = Proyecto.objects.get(id=pk)
    form = Subproyectos_Add_Form()

    if request.method =='POST':
        form = Subproyectos_Add_Form(request.POST)
        if form.is_valid():
            subproyecto = form.save(commit=False)
            subproyecto.proyecto = proyecto
            subproyecto.save()
            messages.success(request,'Has agregado correctamente el subproyecto')
            return redirect('subproyectos', pk=proyecto.id)
    else:
        form = Subproyectos_Add_Form()

    context = {
        'form': form,
        'proyecto':proyecto,
        }

    return render(request,'dashboard/subproyectos_add.html',context)

@login_required(login_url='user-login')
def subproyectos_edit(request, pk):
    subproyecto = Subproyecto.objects.get(id=pk)
    proyecto = Proyecto.objects.get(id=subproyecto.proyecto.id)
    form = Subproyectos_Add_Form(instance=subproyecto)

    if request.method =='POST':
        form = Subproyectos_Add_Form(request.POST, instance=subproyecto)
        if form.is_valid():
            form.save()
            messages.success(request,'Has editado correctamente el subproyecto')
            return redirect('subproyectos', pk=subproyecto.proyecto.id)
    else:
        form = Subproyectos_Add_Form(instance=subproyecto)

    context = {
        'form': form,
        'proyecto':proyecto,
        }

    return render(request,'dashboard/subproyectos_add.html',context)


@login_required(login_url='user-login')
def staff(request):
    workers = User.objects.all()
    context= {
        'workers': workers,
        }
    return render(request,'dashboard/staff.html', context)

@login_required(login_url='user-login')
def product(request):
    items = Product.objects.filter(completado = True).order_by('codigo')

    myfilter=ProductFilter(request.GET, queryset=items)
    items = myfilter.qs

    #Set up pagination
    p = Paginator(items, 50)
    page = request.GET.get('page')
    items_list = p.get_page(page)

    context = {
        'items': items,
        'myfilter':myfilter,
        'items_list':items_list,
        }


    return render(request,'dashboard/product.html', context)


@login_required(login_url='user-login')
def proveedores(request):
    proveedores = Proveedor.objects.all()

    total_prov = proveedores.count()

    myfilter=ProveedorFilter(request.GET, queryset=proveedores)
    proveedores = myfilter.qs

    #Set up pagination
    p = Paginator(proveedores, 50)
    page = request.GET.get('page')
    proveedores_list = p.get_page(page)

    context = {
        'proveedores': proveedores,
        'myfilter':myfilter,
        'proveedores_list':proveedores_list,
        'total_prov':total_prov,
        }


    return render(request,'dashboard/proveedores.html', context)


@login_required(login_url='user-login')
def proveedores_update(request, pk):

    proveedores = Proveedor.objects.get(id=pk)

    if request.method =='POST':
        form = ProveedoresForm(request.POST, instance=proveedores)
        if form.is_valid():
            form.save()
            messages.success(request,f'Has actualizado correctamente el proyecto {proveedores.razon_social}')
            return redirect('configuracion-proyectos')
    else:
        form = ProveedoresForm(instance=proveedores)

    context = {
        'form': form,
        'proveedores':proveedores,
        }

    return render(request,'dashboard/proveedores_update.html', context)

@login_required(login_url='user-login')
def upload_batch_proveedores(request):

    form = Proveedores_BatchForm(request.POST or None, request.FILES or None)


    if form.is_valid():
        form.save()
        form = Proveedores_BatchForm()
        proveedores_list = Proveedor_Batch.objects.get(activated = False)

        f = open(proveedores_list.file_name.path, 'r')
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if not Proveedor.objects.filter(razon_social=row[0]):
                proveedor = Proveedor(razon_social=row[0], rfc=row[1])
                proveedor.save()
            else:
                messages.error(request,f'El proveedor código:{row[0]} ya existe dentro de la base de datos')

        proveedores_list.activated = True
        proveedores_list.save()
    elif request.FILES:
        messages.error(request,'El formato no es CSV')

    context = {
        'form': form,
        }

    return render(request,'dashboard/upload_batch_proveedor.html', context)

@login_required(login_url='user-login')
def upload_batch_proveedores_direcciones(request):

    form = Proveedores_Direcciones_BatchForm(request.POST or None, request.FILES or None)


    if form.is_valid():
        form.save()
        form = Proveedores_Direcciones_BatchForm()
        proveedores_list = Proveedor_Direcciones_Batch.objects.get(activated=False)

        f = open(proveedores_list.file_name.path, 'r')
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if Proveedor.objects.filter(razon_social=row[0]):
                nombre = Proveedor.objects.get(razon_social=row[0])
                if Distrito.objects.filter(nombre = row[1]):
                    distrito = Distrito.objects.get(nombre = row[1])
                    if Banco.objects.filter(nombre= row[6]):
                        banco = Banco.objects.get(nombre = row[6])
                        if Estatus_proveedor.objects.filter(nombre = row[11]):
                            estatus = Estatus_proveedor.objects.get(nombre = row[11])
                            if Estado.objects.filter(nombre = row[3]):
                                estado = Estado.objects.get(nombre = row[3])
                                proveedor_direccion = Proveedor_direcciones(nombre=nombre, distrito=distrito,domicilio=row[2],estado=estado,contacto=row[4],email=row[5], banco=banco, clabe=row[7], cuenta=row[8], financiamiento=row[9],dias_credito=row[10],estatus=estatus)
                                proveedor_direccion.save()
                            else:
                                messages.error(request,f'El estado:{row[3]} no existe dentro de la base de datos')
                        else:
                             messages.error(request,f'El estatus:{row[11]} no existe dentro de la base de datos')
                    else:
                         messages.error(request,f'El banco:{row[6]} no existe dentro de la base de datos')
                else:
                    messages.error(request,f'El distrito:{row[1]} no existe dentro de la base de datos')
            else:
                messages.error(request,f'El proveedor código:{row[0]} no existe dentro de la base de datos')

        proveedores_list.activated = True
        proveedores_list.save()
    elif request.FILES:
        messages.error(request,'El formato no es CSV')

    context = {
        'form': form,
        }

    return render(request,'dashboard/upload_batch_proveedor_direcciones.html', context)



@login_required(login_url='user-login')
def upload_batch_products(request):

    form = Products_BatchForm(request.POST or None, request.FILES or None)


    if form.is_valid():
        form.save()
        form = Products_BatchForm()
        product_list = Products_Batch.objects.get(activated = False)

        f = open(product_list.file_name.path, 'r')
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if not Product.objects.filter(codigo=row[0]):
                if Unidad.objects.filter(nombre = row[2]):
                    unidad = Unidad.objects.get(nombre = row[2])
                    if Familia.objects.filter(nombre = row[3]):
                        familia = Familia.objects.get(nombre = row[3])
                        if Subfamilia.objects.filter(nombre = row[4], familia = familia):
                            subfamilia = Subfamilia.objects.get(nombre = row[4], familia = familia)
                            producto = Product(codigo=row[0],nombre=row[1], unidad=unidad, familia=familia, subfamilia=subfamilia,especialista=row[5],iva=row[6],activo=row[7],servicio=row[8],baja_item=False,completado=True)
                            producto.save()
                        else:
                            producto = Product(codigo=row[0],nombre=row[1], unidad=unidad, familia=familia,especialista=row[5],iva=row[6],activo=row[7],servicio=row[8],baja_item=False,completado=True)
                            producto.save()
                    else:
                        messages.error(request,f'La familia no existe dentro de la base de datos, producto:{row[0]}')
                else:
                    messages.error(request,f'La unidad no existe dentro de la base de datos, producto:{row[0]}')
            else:
                messages.error(request,f'El producto código:{row[0]} ya existe dentro de la base de datos')

        product_list.activated = True
        product_list.save()
    elif request.FILES:
        messages.error(request,'El formato no es CSV')




    context = {
        'form': form,
        }

    return render(request,'dashboard/upload_batch_products.html', context)


@login_required(login_url='user-login')
def order(request):
    orders = Order.objects.all()
    context= {
        'orders':orders,
        }

    return render(request,'dashboard/order.html', context)

@login_required(login_url='user-login')
def product_delete(request, pk):
    item = Product.objects.get(id=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('dashboard-product')

    return render(request,'dashboard/product_delete.html')


@login_required(login_url='user-login')
def add_product(request):
    item, created = Product.objects.get_or_create(completado=False)

    if request.method =='POST':
        form = AddProduct_Form(request.POST, request.FILES or None, instance = item)
        #form.save(commit=False)
        item.completado = True
        if form.is_valid():
            form.save()
            item.save()
            messages.success(request,f'Has agregado correctamente el producto {item.nombre}')
            return redirect('dashboard-product')
    else:
        form = AddProduct_Form()


    context = {
        'form': form,
        'item':item,
        }
    return render(request,'dashboard/add_product.html', context)

@login_required(login_url='user-login')
def product_update(request, pk):
#def product_update_modal(request, pk):

    item = Product.objects.get(id=pk)

    if request.method =='POST':
        form = AddProduct_Form(request.POST, request.FILES or None, instance=item, )
        if form.is_valid():
            form.save()
            messages.success(request,f'Has actualizado correctamente el producto {item.nombre}')
            return redirect('dashboard-product')
    else:
        form = AddProduct_Form(instance=item)


    context = {
        'form': form,
        'item':item,
        }
    return render(request,'dashboard/product_update.html', context)



def load_subfamilias(request):

    familia_id = request.GET.get('familia_id')
    subfamilias = Subfamilia.objects.filter(familia_id = familia_id)

    return render(request, 'dashboard/subfamilia_dropdown_list_options.html',{'subfamilias': subfamilias})


@login_required(login_url='user-login')
def staff_detail(request, pk):
    worker = User.objects.get(id=pk)
    context={
        'worker': worker,
        }
    return render(request,'dashboard/staff_detail.html', context)