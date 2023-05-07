from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from compras.models import Compra, ArticuloComprado
from compras.filters import CompraFilter
from compras.views import attach_oc_pdf
from dashboard.models import Inventario, Order, ArticulosparaSurtir
from requisiciones.models import Salidas
from .models import Entrada, EntradaArticulo, Reporte_Calidad
from .forms import EntradaArticuloForm, Reporte_CalidadForm
from user.models import Profile
import json
from django.db.models import Sum
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from datetime import date, datetime
import decimal
from django.core.mail import EmailMessage

# Create your views here.
@login_required(login_url='user-login')
def pendientes_entrada(request):
    usuario = Profile.objects.get(staff=request.user.id)


    if usuario.tipo.almacen == True:
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= False, entrada_completa = False, autorizado2= True).order_by('-folio')
        for compra in compras:
            articulos_entrada  = ArticuloComprado.objects.filter(oc=compra, entrada_completa = False)
            servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
            cant_entradas = articulos_entrada.count()
            cant_servicios = servicios_pendientes.count()

            if  cant_entradas == cant_servicios:
                compra.solo_servicios = True
                compra.save()
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= False, entrada_completa = False, autorizado2= True).order_by('-folio')
    else:
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= True, entrada_completa = False, autorizado2= True, req__orden__staff = usuario).order_by('-folio')




    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

    context = {
        'compras':compras,
        'myfilter':myfilter,
        }

    return render(request, 'entradas/pendientes_entrada.html', context)

@login_required(login_url='user-login')
def pendientes_calidad(request):
    articulos_entrada = EntradaArticulo.objects.filter(articulo_comprado__producto__producto__articulos__producto__producto__especialista = True, liberado = False)

    context = {
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/pendientes_calidad.html', context)

@login_required(login_url='user-login')
def devolucion_a_proveedor(request):

    articulos = Reporte_Calidad.objects.filter(completo = True, autorizado = False)

    context = {
        'articulos':articulos,
        }

    return render(request, 'entradas/devolucion_a_proveedor.html', context)

@login_required(login_url='user-login')
def articulos_entrada(request, pk):

    usuario = Profile.objects.get(staff=request.user.id)
    if usuario.tipo.almacen == True:
        articulos = ArticuloComprado.objects.filter(oc=pk, entrada_completa = False, seleccionado = False, producto__producto__articulos__producto__producto__servicio = False)
    else:
        articulos = ArticuloComprado.objects.filter(oc=pk, entrada_completa = False, seleccionado = False, producto__producto__articulos__producto__producto__servicio = True)


    compra = Compra.objects.get(id=pk)
    conteo_de_articulos = articulos.count()


    entrada, created = Entrada.objects.get_or_create(oc=compra, almacenista= usuario, completo = False)
    articulos_entrada = EntradaArticulo.objects.filter(entrada = entrada)
    form = EntradaArticuloForm()

    for articulo in articulos:
        if articulo.cantidad_pendiente == None:
            articulo.cantidad_pendiente = articulo.cantidad


    if request.method == 'POST' and 'entrada' in request.POST:
        num_art_comprados = ArticuloComprado.objects.filter(oc=compra).count()
        entrada.completo = True
        entrada.entrada_date = date.today()
        entrada.entrada_hora = datetime.now().time()
        articulos_comprados = ArticuloComprado.objects.filter(oc=pk)
        articulos_entregados = articulos_comprados.filter(entrada_completa=True)
        articulos_seleccionados = articulos_entregados.filter(seleccionado = True)
        num_art_entregados = articulos_entregados.count()
        for elemento in articulos_seleccionados:
            elemento.seleccionado = False
            elemento.save()

        for articulo in articulos_entrada:
            producto_surtir = ArticulosparaSurtir.objects.get(articulos = articulo.articulo_comprado.producto.producto.articulos)
            producto_surtir.seleccionado = False
            if producto_surtir.articulos.producto.producto.especialista == True:
                producto_surtir.surtir = False
                articulo.liberado = False
                archivo_oc = attach_oc_pdf(request, articulo.articulo_comprado.oc.id)
                email = EmailMessage(
                        f'Compra Autorizada {compra.get_folio}',
                        f'Estimado *Inserte nombre de especialista*,\n Estás recibiendo este correo porque se ha recibido en almacén el producto código:{producto_surtir.articulos.producto.producto.codigo} descripción:{producto_surtir.articulos.producto.producto.nombre} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                        'savia@vordcab.com',
                        ['ulises_huesc@hotmail.com'],
                        )
                email.attach(f'OC_folio:{articulo.articulo_comprado.oc.folio}.pdf',archivo_oc,'application/pdf')
                email.send()
            if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                #Estas son todas las solicitudes pendientes por surtir que se podrían surtir con el resurtimiento
                productos_surtir = ArticulosparaSurtir.objects.filter(articulos__producto__producto = articulo.articulo_comprado.producto.producto.articulos.producto.producto, salida = False, articulos__orden__tipo__tipo = 'normal')
                inv_de_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto)
                for producto in productos_surtir:    #Recorremos todas las solicitudes pendientes por surtir una por una
                    if producto_surtir.cantidad > 0:
                        if producto_surtir.cantidad > producto.cantidad_requisitar:
                            producto.cantidad = producto.cantidad_requisitar
                            producto.cantidad_requisitar = 0
                            solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                            solicitud.requisitar = False
                            solicitud.save()
                            inv_de_producto.cantidad = inv_de_producto.cantidad - producto.cantidad   #Se reduce el inventario en la medida que existan solicitudes pendientes por surtir
                            inv_de_producto.cantidad_apartada = inv_de_producto.cantidad_apartada + producto.cantidad    #A la vez que aumenta la cantidad apartada
                            producto_surtir.cantidad = producto_surtir.cantidad - producto.cantidad_requisitar
                            producto.requisitar = False
                            producto.surtir = True
                            producto.save()
                            producto_surtir.save()
                            inv_de_producto.save()
            if entrada.oc.req.orden.tipo.tipo == 'normal':
                if articulo.articulo_comprado.producto.producto.articulos.producto.producto.servicio == True:
                    producto_surtir.surtir = False
                else:
                    producto_surtir.surtir = True
            producto_surtir.save()
        for articulo in articulos_comprados:
            articulo.seleccionado = False
            articulo.save()
        #Se compara los articulos comprados contra los articulos que han entrado y que están totalmente entregados
        if num_art_comprados == num_art_entregados:
            compra.entrada_completa = True
        compra.save()
        entrada.save()
        messages.success(request, f'La entrada {entrada.id} se ha realizado con éxito')
        return redirect('pendientes_entrada')

    context = {
        'articulos':articulos,
        'entrada':entrada,
        'compra':compra,
        'form':form,
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/articulos_entradas.html', context)


def update_entrada(request):
    data = json.loads(request.body)
    cantidad = int(data["cantidad_ingresada"])
    action = data["action"]
    producto_id = int(data["producto"])
    pk = int(data["entrada_id"])
    producto_comprado = ArticuloComprado.objects.get(id = producto_id)
    entrada = Entrada.objects.get(id = pk, completo = False)
    entradas_producto = EntradaArticulo.objects.filter(articulo_comprado = producto_comprado, entrada__oc = producto_comprado.oc, entrada__completo = True).aggregate(Sum('cantidad'))
    suma_entradas = entradas_producto['cantidad__sum']
    entradas_producto = EntradaArticulo.objects.filter(articulo_comprado = producto_comprado, entrada__oc = producto_comprado.oc, entrada__completo = True).aggregate(Sum('cantidad_por_surtir'))

    pendientes_surtir = entradas_producto['cantidad_por_surtir__sum']
    if pendientes_surtir == None:   #Esto sucede cuando no hay ningún producto en esos articulos
        pendientes_surtir = 0

    entrada_item, created = EntradaArticulo.objects.get_or_create(entrada = entrada, articulo_comprado = producto_comprado)
    producto_inv = Inventario.objects.get(producto = producto_comprado.producto.producto.articulos.producto.producto)

    #if not entrada_item.cantidad:
    entrada_item.cantidad = cantidad


    if entrada.oc.req.orden.tipo.tipo == 'resurtimiento': #si es resurtimiento
        producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto_comprado.producto.producto.articulos, surtir=False, articulos__orden__tipo__tipo = 'resurtimiento')
    else:
        producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto_comprado.producto.producto.articulos)

    if producto_inv.producto.servicio == False:
        monto_inventario = producto_inv.cantidad * producto_inv.price + producto_inv.cantidad_apartada * producto_inv.price

        cantidad_inventario = producto_inv.cantidad + producto_inv.cantidad_apartada

        monto_total = monto_inventario + entrada_item.cantidad * producto_comprado.precio_unitario

        nueva_cantidad_inventario =  cantidad_inventario + entrada_item.cantidad
    if suma_entradas is None:
        suma_entradas = 0

    if action == "add":
        total_entradas_pendientes = pendientes_surtir + entrada_item.cantidad
        total_entradas = suma_entradas + entrada_item.cantidad

        if total_entradas > producto_comprado.cantidad: #Si la cantidad de las entradas es mayor a la cantidad de la compra se rechaza
            messages.error(request,f'La cantidad de entradas sobrepasa la cantidad comprada {suma_entradas} > {cantidad}')
        else:
            entrada_item.cantidad_por_surtir = cantidad
            producto_comprado.cantidad_pendiente = producto_comprado.cantidad - total_entradas
            #Cree una variable booleana temporal para quitarlo del seleccionable
            producto_comprado.seleccionado = True
            if producto_inv.producto.servicio == False:
                if cantidad_inventario == 0:
                    precio_unit_promedio = producto_comprado.precio_unitario
                else:
                    precio_unit_promedio = monto_total/nueva_cantidad_inventario

                producto_inv.price = precio_unit_promedio
            #Esta parte determina el comportamiento de todos las solicitudes que se tienen que activar cuando la entrada es de resurtimiento
            if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                if producto_surtir:
                    producto_inv.cantidad_entradas = producto_inv.cantidad_entradas + entrada_item.cantidad
                    if producto_surtir.cantidad_requisitar > entrada_item.cantidad:                                 #Si el producto pendiente de requisitar es mayor que las entradas
                        producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - entrada_item.cantidad  #Al producto pendiente por requisitar se le resta lo que entra
                        producto_inv.cantidad = producto_inv.cantidad + entrada_item.cantidad - producto_surtir.cantidad_requisitar #--------- No hay necesidad de apartar cuando la entrada es de resurtimiento
                    elif producto_surtir.cantidad_requisitar <= entrada_item.cantidad:                 #Si el producto pendiente de requisitar es menor o igual que las entradas
                        producto_surtir.cantidad = producto_surtir.cantidad_requisitar                 #la cantidad disponible para surtir es igual a la cantidad por requisitar, es decir, se cubre toda la necesidad
                        producto_surtir.cantidad_requisitar = 0                                        #Al cubrirse toda la necesidad la cantidad por requisitar pasa a 0
                        producto_inv.cantidad = producto_inv.cantidad + entrada_item.cantidad - producto_surtir.cantidad_requisitar #El producto disponible en el inventario es la suma de lo que ya estaba ahí más lo que entró menos lo que ho se había surtido y que ahora queda apartado
                        solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                        solicitud.requisitar = False
                        solicitud.save()
                    producto_surtir.precio = producto_comprado.precio_unitario
                    producto_surtir.save()
                    producto_inv.save()
                producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para resurtimiento'
            else:
                producto_inv.cantidad_entradas = producto_inv.cantidad_entradas + entrada_item.cantidad
                producto_inv.cantidad_apartada = producto_inv.cantidad_apartada + entrada_item.cantidad
                producto_surtir.cantidad = total_entradas_pendientes                        #Al producto disponible para surtir se le suma lo que entra
                producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - total_entradas_pendientes  #Al producto pendiente por requisitar se le resta lo que entra
                producto_inv.save()
                producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para solicitud normal'
                entrada.pagado_date = date.today()
                entrada.pagado_hora = datetime.now().time()
                entrada.save()
                producto_surtir.save()
            #Se guardan todas las bases de datos
            if producto_comprado.cantidad == total_entradas:  #Si la cantidad de la compra es igual a la cantida entonces la entrada está completamente entregada
                producto_comprado.entrada_completa = True
            #cantidad_entradas = entradas_producto.cantidad - entradas_producto.cantidad_por_surtir
            messages.success(request,'Haz agregado exitosamente un producto')
            if producto_comprado.producto.producto.articulos.producto.producto.servicio == True:
                salida, created = Salidas.objects.get_or_create(producto = producto_surtir, salida_firmada=True, cantidad = entrada_item.cantidad)
                salida.comentario = 'Esta salida es un  servicio por lo tanto no pasa por almacén y no existe registro de la salida del mismo'
                producto_surtir.surtir = False
                salida.save()
            entrada_item.save()
            producto_comprado.save()
            producto_inv.save()


    elif action == "remove":
        monto_total = monto_inventario - (entrada_item.cantidad * producto_comprado.precio_unitario)
        if monto_total == 0:
            producto_inv.price = 0
        else:
            producto_inv.price = monto_total/cantidad_inventario
        #cantidad_total = cantidad_inventario - entrada_item.cantidad
        if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
            if producto_surtir.cantidad > entrada_item.cantidad:
                producto_surtir.cantidad = producto_surtir.cantidad - entrada_item.cantidad
            if producto_surtir.cantidad <= entrada_item.cantidad:
                producto_surtir.cantidad_requisitar = producto_surtir.cantidad
                producto_surtir.cantidad = 0
                producto_inv.cantidad = producto_inv.cantidad - entrada_item.cantidad + producto_surtir.cantidad
                producto_inv.cantidad_apartada = producto_inv.cantidad_apartada - producto_surtir.cantidad_requisitar
                producto_surtir.save()

        else:
            producto_inv.cantidad_apartada = producto_inv.cantidad_apartada - entrada_item.cantidad
            producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar + entrada_item.cantidad
            producto_surtir.cantidad = producto_surtir.cantidad - entrada_item.cantidad
            if producto_surtir == 0:
                producto_surtir.surtir = False
                producto_surtir.precio = 0
            producto_surtir.save()
        producto_inv._change_reason = 'Se está borrando una entrada. view: update_entrada'
        producto_inv.cantidad_entradas = producto_inv.cantidad_entradas - entrada_item.cantidad
        producto_comprado.cantidad_pendiente = producto_comprado.cantidad_pendiente + entrada_item.cantidad
        producto_comprado.entrada_completa = False
        producto_comprado.seleccionado = False
        messages.success(request,'Has eliminado el artículo con éxito')
        #Se borra el elemento de las entradas
        #Guardado de bases de datos
        entrada_item.save()
        producto_inv.save()
        producto_comprado.save()
        entrada_item.delete()
    return JsonResponse('Item was '+action, safe=False)



def reporte_calidad(request, pk):
    perfil = Profile.objects.get(staff__id = request.user.id)
    articulo_entrada = EntradaArticulo.objects.get(id = pk, liberado = False)
    form = Reporte_CalidadForm()
    articulos_reportes = Reporte_Calidad.objects.filter(articulo = articulo_entrada, completo = True)
    reporte_actual, created = Reporte_Calidad.objects.get_or_create(articulo = articulo_entrada, completo = False)
    sum_articulos_reportes = 0

    for item in articulos_reportes:
        sum_articulos_reportes = item.cantidad + sum_articulos_reportes

    restantes_liberacion = articulo_entrada.cantidad - sum_articulos_reportes


    if request.method =='POST':
        form = Reporte_CalidadForm(request.POST, instance = reporte_actual)
        if int(request.POST['cantidad']) <=  restantes_liberacion:
            if not request.POST['autorizado'] == None:
                if form.is_valid():
                    item = form.save()
                    item.articulo = articulo_entrada
                    item.reporte_date = date.today()
                    item.reporte_hora = datetime.now().time()
                    producto_surtir = ArticulosparaSurtir.objects.get(articulos = articulo_entrada.articulo_comprado.producto.producto.articulos)
                    articulos_restantes = articulo_entrada.cantidad - item.cantidad - sum_articulos_reportes
                    if item.autorizado == True:
                        if articulos_restantes == 0:
                            articulo_entrada.liberado = True
                        producto_surtir.cantidad = producto_surtir.cantidad + item.cantidad
                        producto_surtir.surtir = True
                        producto_surtir.save()
                    if item.autorizado == False:
                        if articulos_restantes == 0:
                            articulo_entrada.liberado = True
                    articulo_entrada.save()
                    item.completo = True
                    item.save()
                    messages.success(request, 'Has generado exitosamente tu reporte')
                    return HttpResponse(status=204)
            else:
                messages.error(request, 'Debes elegir un modo de liberación')
        else:
            messages.error(request, 'La cantidad liberada no puede ser mayor que cantidad de entradas restante')

    #else:
        #form = InventarioForm()

    context = {
        'form': form,
        'articulo_entrada':articulo_entrada,
        'restantes_liberacion': restantes_liberacion,
        }

    return render(request,'entradas/calidad_entrada.html',context)