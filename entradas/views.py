from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Max
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from compras.models import Compra, ArticuloComprado
from compras.filters import CompraFilter
from compras.views import attach_oc_pdf
from dashboard.models import Inventario, Order, ArticulosparaSurtir
from requisiciones.models import Salidas, ArticulosRequisitados, Requis
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo
from .forms import EntradaArticuloForm, Reporte_CalidadForm, NoConformidadForm, NC_ArticuloForm
from tesoreria.models import Pago
from user.models import Profile
from requisiciones.views import get_image_base64
import json
import decimal
import os
from datetime import date, datetime
from user.decorators import perfil_seleccionado_required

# Create your views here.
@perfil_seleccionado_required
@login_required(login_url='user-login')
def pendientes_entrada(request):
    pk = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk)
    

    if usuario.tipo.nombre == "Admin":
         compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True).order_by('-folio')
    elif usuario.tipo.almacen == True:
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), req__orden__distrito = usuario.distritos, solo_servicios= False, entrada_completa = False, autorizado2= True).order_by('-folio')
        for compra in compras:
            articulos_entrada  = ArticuloComprado.objects.filter(oc=compra, entrada_completa = False)
            servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
            cant_entradas = articulos_entrada.count()
            cant_servicios = servicios_pendientes.count()
            pago = Pago.objects.filter(oc=compra).first()
            if  cant_entradas == cant_servicios and cant_entradas > 0:
                compra.solo_servicios = True
                compra.save()
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), req__orden__distrito = usuario.distritos, solo_servicios= False, entrada_completa = False, autorizado2= True).order_by('-folio')
        #compras = Compra.objects.filter(autorizado2= True)
    else:
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= True, entrada_completa = False, autorizado2= True, req__orden__staff = usuario).order_by('-folio')


    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

    #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    context = {
        'compras':compras,
        'myfilter':myfilter,
        'compras_list':compras_list,
        }

    return render(request, 'entradas/pendientes_entrada.html', context)

@login_required(login_url='user-login')
def pendientes_calidad(request):
    articulos_entrada = EntradaArticulo.objects.filter(articulo_comprado__producto__producto__articulos__producto__producto__especialista = True, liberado = False)
    print(articulos_entrada)
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

@perfil_seleccionado_required
@login_required(login_url='user-login')
def articulos_entrada(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    
    if usuario.tipo.almacen == True:
        articulos = ArticuloComprado.objects.filter(oc=pk, entrada_completa = False,  seleccionado = False, producto__producto__articulos__producto__producto__servicio = False)
    else:
        articulos = ArticuloComprado.objects.filter(oc=pk, entrada_completa = False,  seleccionado = False, producto__producto__articulos__producto__producto__servicio = True)


    compra = Compra.objects.get(id=pk)
    conteo_de_articulos = articulos.count()


    entrada, created = Entrada.objects.get_or_create(oc=compra, almacenista= usuario, completo = False)
    articulos_entrada = EntradaArticulo.objects.filter(entrada = entrada)
    form = EntradaArticuloForm()
    max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']

    for articulo in articulos:
        if articulo.cantidad_pendiente == None:
            articulo.cantidad_pendiente = articulo.cantidad


    if request.method == 'POST' and 'entrada' in request.POST:
        num_art_comprados = ArticuloComprado.objects.filter(oc=compra).count()
        max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
        entrada.completo = True
        entrada.folio = max_folio
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
                productos_pendientes_surtir = ArticulosparaSurtir.objects.filter(
                    articulos__producto__producto = articulo.articulo_comprado.producto.producto.articulos.producto.producto,
                    salida = False, 
                    articulos__orden__tipo__tipo = 'normal',
                    cantidad_requisitar__gt=0
                    )
                inv_de_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto)
                for producto in productos_pendientes_surtir:    #Recorremos todas las solicitudes pendientes por surtir una por una
                    if producto_surtir.cantidad > 0:
                        inv_de_producto.cantidad = inv_de_producto.cantidad - producto.cantidad
                        if producto.cantidad_requisitar <= producto_surtir.cantidad:
                            producto_surtir.cantidad = producto_surtir.cantidad - producto.cantidad_requisitar
                            producto.cantidad = producto.cantidad + producto.cantidad_requisitar
                            producto.cantidad_requisitar = 0
                            producto.requisitar = False
                        else:
                            producto.cantidad_requisitar = producto.cantidad_requisitar - producto_surtir.cantidad
                            producto.cantidad = producto.cantidad + producto_surtir.cantidad
                            producto_surtir.cantidad = 0

                        #if producto_surtir.cantidad > producto.cantidad_requisitar:
                        #    producto.cantidad = producto.cantidad_requisitar
                        #    producto.cantidad_requisitar = 0
                        #    solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                        #    solicitud.requisitar = False
                        #    solicitud.save()
                        #    inv_de_producto.cantidad = inv_de_producto.cantidad - producto.cantidad   #Se reduce el inventario en la medida que existan solicitudes pendientes por surtir
                        #    inv_de_producto.cantidad_apartada = inv_de_producto.cantidad_apartada + producto.cantidad    #A la vez que aumenta la cantidad apartada
                        #    producto_surtir.cantidad = producto_surtir.cantidad - producto.cantidad_requisitar
                        #    producto.requisitar = False
                            producto.surtir = True
                            producto.save()
                            producto_surtir.save()
                            inv_de_producto.save()
                            solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                            productos_orden = ArticulosparaSurtir.objects.filter(articulos__orden = solicitud, requisitar=False).count()
                            if productos_orden == 0:
                                solicitud.requisitar = False
                                solicitud.save()
            if entrada.oc.req.orden.tipo.tipo == 'normal':
                if articulo.articulo_comprado.producto.producto.articulos.producto.producto.servicio == True:
                    producto_surtir.surtir = False
                else:
                    producto_surtir.surtir = True
            producto_surtir.save()
        evalua_entrada_completa(articulos_comprados,num_art_comprados, compra)
        #for articulo in articulos_comprados:
        #    if articulo.cantidad_pendiente == 0:  #Si la cantidad de la compra es igual a la cantida entonces la entrada está completamente entregada
        #        articulo.entrada_completa = True
        #    articulo.seleccionado = False
        #    articulo.save()
        #Se compara los articulos comprados contra los articulos que han entrado y que están totalmente entregados
        #num_art_entregados = articulos_comprados.filter(entrada_completa=True).count()
        #if num_art_comprados == num_art_entregados:
        #    compra.entrada_completa = True
        #compra.save()
        entrada.save()
        messages.success(request, f'La entrada {entrada.folio} se ha realizado con éxito')
        return redirect('pendientes_entrada')

    context = {
        'articulos':articulos,
        'max_folio': max_folio,
        'entrada':entrada,
        'compra':compra,
        'form':form,
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/articulos_entradas.html', context)

def evalua_entrada_completa(articulos_comprados, num_art_comprados, compra):
    for articulo in articulos_comprados:
        if articulo.cantidad_pendiente == 0:  #Si la cantidad de la compra es igual a la cantida entonces la entrada está completamente entregada
            articulo.entrada_completa = True
        articulo.seleccionado = False
        articulo.save()
        #Se compara los articulos comprados contra los articulos que han entrado y que están totalmente entregados
    num_art_entregados = articulos_comprados.filter(entrada_completa=True).count()
    if num_art_comprados == num_art_entregados:
        compra.entrada_completa = True
    compra.save()  

def update_entrada(request):
    data = json.loads(request.body)
    cantidad = decimal.Decimal(data["cantidad_ingresada"])
    action = data["action"]
    producto_id = int(data["producto"])
    pk = int(data["entrada_id"])
    referencia = data["referencia"]

    producto_comprado = ArticuloComprado.objects.get(id = producto_id)
    entrada = Entrada.objects.get(id = pk, completo = False)
    aggregation = EntradaArticulo.objects.filter(
        articulo_comprado = producto_comprado,
        entrada = entrada, 
        entrada__completo = True
    ).aggregate(
        suma_cantidad = Sum('cantidad'),
        suma_cantidad_por_surtir = Sum('cantidad_por_surtir')
    )

    suma_cantidad = aggregation['suma_cantidad'] or 0
    pendientes_surtir = aggregation['suma_cantidad_por_surtir'] or 0
    #print(suma_cantidad)
    #print(pendientes_surtir)
    entrada_item, created = EntradaArticulo.objects.get_or_create(entrada = entrada, articulo_comprado = producto_comprado)
    producto_inv = Inventario.objects.get(producto = producto_comprado.producto.producto.articulos.producto.producto, distrito = producto_comprado.oc.req.orden.distrito)

    if entrada.oc.req.orden.tipo.tipo == 'resurtimiento': #si es resurtimiento
        producto_surtir = ArticulosparaSurtir.objects.get(articulos = producto_comprado.producto.producto.articulos, surtir=False, articulos__orden__tipo__tipo = 'resurtimiento')
    else:
        #id= producto_comprado.producto.producto.id
        producto_surtir = ArticulosparaSurtir.objects.get(id= producto_comprado.producto.producto.id)

    if producto_inv.producto.servicio == False:
        monto_inventario = producto_inv.cantidad * producto_inv.price + producto_inv.apartada_entradas * producto_inv.price
        cantidad_inventario = producto_inv.cantidad + producto_inv.apartada_entradas
        monto_total = monto_inventario + entrada_item.cantidad * producto_comprado.precio_unitario
        nueva_cantidad_inventario =  cantidad_inventario + entrada_item.cantidad
    

    if action == "add":
        #if not entrada_item.cantidad:
        entrada_item.cantidad = cantidad
        entrada_item.cantidad_por_surtir = cantidad
        entrada_item.referencia = referencia
        entrada_item.save()
        total_entradas_pendientes = pendientes_surtir + entrada_item.cantidad
        total_entradas = suma_cantidad + entrada_item.cantidad

        if total_entradas > producto_comprado.cantidad: #Si la cantidad de las entradas es mayor a la cantidad de la compra se rechaza
            messages.error(request,f'La cantidad de entradas sobrepasa la cantidad comprada {suma_cantidad} > {cantidad}')
        else:
            entrada_item.cantidad_por_surtir = cantidad
            producto_comprado.cantidad_pendiente = producto_comprado.cantidad - total_entradas
            
            
            if producto_inv.producto.servicio == False:
                if cantidad_inventario == 0:
                    precio_unit_promedio = producto_comprado.precio_unitario
                else:
                    precio_unit_promedio = monto_total/nueva_cantidad_inventario

                producto_inv.price = precio_unit_promedio
            #Esta parte determina el comportamiento de todos las solicitudes que se tienen que activar cuando la entrada es de resurtimiento
            if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                if producto_surtir:
                    producto_inv.cantidad_entradas = pendientes_surtir + entrada_item.cantidad
                    producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - entrada_item.cantidad
                    producto_surtir.cantidad = producto_surtir.cantidad + entrada_item.cantidad
                    producto_inv.cantidad = producto_inv.cantidad + entrada_item.cantidad 
                    if producto_surtir.cantidad_requisitar == 0:
                        producto_surtir.requisitar = False
                    
                    producto_surtir.precio = producto_comprado.precio_unitario
                    producto_surtir.save()
                    producto_inv.save()
                producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para resurtimiento'
            else:
                producto_inv.cantidad_entradas = pendientes_surtir + entrada_item.cantidad
                producto_inv.cantidad_apartada = producto_inv.apartada_entradas
                producto_surtir.cantidad = producto_surtir.cantidad + entrada_item.cantidad                       #Al producto disponible para surtir se le suma lo que entra
                producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - entrada_item.cantidad   #Al producto pendiente por requisitar se le resta lo que entra
                producto_inv.save()
                producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para solicitud normal'
                entrada.entrada_date = date.today()
                entrada.entrada_hora = datetime.now().time()
                entrada.save()
                producto_surtir.save()
            #Se guardan todas las bases de datos
          
            #cantidad_entradas = entradas_producto.cantidad - entradas_producto.cantidad_por_surtir
            messages.success(request,'Haz agregado exitosamente un producto')
            if producto_comprado.producto.producto.articulos.producto.producto.servicio == True:
                salida, created = Salidas.objects.get_or_create(producto = producto_surtir, salida_firmada=True, cantidad = entrada_item.cantidad)
                salida.comentario = 'Esta salida es un  servicio por lo tanto no pasa por almacén y no existe registro de la salida del mismo'
                producto_surtir.surtir = False
                salida.save()
            #Cree una variable booleana temporal para quitarlo del seleccionable
            producto_comprado.seleccionado = True
            producto_comprado.save()
            producto_inv.save()


    elif action == "remove":
        if producto_inv.producto.servicio == False:
            monto_total = monto_inventario - (entrada_item.cantidad * producto_comprado.precio_unitario)
        else:
            monto_total = 0
        if monto_total == 0:
            producto_inv.price = 0
        else:
            if cantidad_inventario == 0:
                producto_inv.price = 0
            else:
                producto_inv.price = monto_total/cantidad_inventario or 0
        #cantidad_total = cantidad_inventario - entrada_item.cantidad
        if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
            producto_surtir.cantidad = producto_surtir.cantidad - entrada_item.cantidad
            producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar + entrada_item.cantidad
            producto_inv.cantidad = producto_inv.cantidad - entrada_item.cantidad
            producto_surtir.requisitar = True
            producto_surtir.save()
            #if producto_surtir.cantidad > entrada_item.cantidad:
            #    producto_surtir.cantidad = producto_surtir.cantidad - entrada_item.cantidad
            #if producto_surtir.cantidad <= entrada_item.cantidad:
            #    producto_surtir.cantidad_requisitar = producto_surtir.cantidad
            #    producto_surtir.cantidad = 0
            #    producto_inv.cantidad = producto_inv.cantidad - entrada_item.cantidad + producto_surtir.cantidad
            #    producto_inv.cantidad_apartada = producto_inv.cantidad_apartada - producto_surtir.cantidad_requisitar
            #    producto_surtir.save()

        else:
            #producto_inv.cantidad_apartada = producto_inv.cantidad_apartada - entrada_item.cantidad
            producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar + entrada_item.cantidad
            producto_surtir.cantidad = producto_surtir.cantidad - entrada_item.cantidad
            if producto_surtir == 0:
                producto_surtir.surtir = False
                producto_surtir.precio = 0
            producto_surtir.save()
        producto_inv._change_reason = 'Se está borrando una entrada. view: update_entrada'
        producto_inv.cantidad_entradas = producto_inv.cantidad_entradas - entrada_item.cantidad
        if producto_comprado.cantidad_pendiente == None:
            producto_comprado.cantidad_pendiente = 0
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
    mensaje ='Item was ' + action
    return JsonResponse(mensaje, safe=False)
    


def reporte_calidad(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
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
        if decimal.Decimal(request.POST['cantidad']) <=  restantes_liberacion:
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

def productos(request, pk):
    compra = Compra.objects.get(id=pk)
    articulos_comprados = ArticuloComprado.objects.filter(oc=compra, entrada_completa=False)

    context = {
        'compra': compra,
        'articulos_comprados': articulos_comprados,
    }

    return render(request, 'entradas/productos.html', context)


def no_conformidad(request, pk):
    # Obtén la compra y el perfil asociado con la sesión actual
    compra = Compra.objects.get(id=pk)
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    articulos = ArticuloComprado.objects.filter(oc=pk, entrada_completa = False, seleccionado = False, producto__producto__articulos__producto__producto__servicio = False)

    for articulo in articulos:
        if articulo.cantidad_pendiente == None:
            articulo.cantidad_pendiente = articulo.cantidad


    # Crear o obtener la instancia de No_Conformidad
    no_conformidad, created = No_Conformidad.objects.get_or_create(
        oc=compra,
        almacenista=perfil,
        completo = False,
    )

    articulos_nc = NC_Articulo.objects.filter(nc = no_conformidad, )
    form = NC_ArticuloForm()
    form2 = NoConformidadForm()

    productos_para_select2 = [
        {'id': producto.id,
         'text': str(producto.producto.producto.articulos.producto), 
         'cantidad': str(producto.cantidad), 
         'cantidad_pendiente': str(producto.cantidad_pendiente),
        } for producto in articulos]

    # Si el método de la petición es POST, procesar el formulario
    if request.method == "POST":
        #and 'BtnCrear' in request.POST:
        form2 = NoConformidadForm(request.POST, instance = no_conformidad)

        if form2.is_valid():
            no_conf = form2.save(commit=False)
            articulos_comprados = ArticuloComprado.objects.filter(oc=compra)
            num_art_comprados =articulos_comprados.count()
            for articulo in articulos_nc:
                articulo_comprado = articulos_comprados.get(producto=articulo.articulo_comprado.producto)
                try:
                    articulo_entradas = EntradaArticulo.objects.get(entrada__oc = compra, articulo_comprado = articulo.articulo_comprado)
                except ObjectDoesNotExist:
                    articulo_entradas = None
                
                if articulo_entradas is not None:
                    cantidad_entradas = articulo_entradas.cantidad
                else:
                    cantidad_entradas = 0
                articulo_requisitado = ArticulosRequisitados.objects.get(req=compra.req, producto=articulo.articulo_comprado.producto.producto)
                if articulo_comprado.cantidad_pendiente == None:
                    articulo_comprado.cantidad_pendiente = 0
                #Todo esto debería de pasar solo si la NC ya no se va a recibir es decir si el tipo de la conformidad = Material no disponibles
                if no_conf.tipo_nc.id == 1:
                    if articulo_comprado.cantidad == articulo.cantidad + cantidad_entradas: 
                       articulo_comprado.entrada_completa = True
                    articulo_comprado.seleccionado = False
                    articulo_requisitado.sel_comp = False
                articulo_comprado.save()
                articulo_requisitado.save()
                static_path = settings.STATIC_ROOT
                #Generación de correo
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
                        <p>Estimado {no_conf.oc.creada_por.staff.staff.staff.first_name} {no_conf.oc.creada_por.staff.staff.staff.last_name},</p>
                        <p>Estás recibiendo este correo porque no se levantado una NC de tu OC: {no_conf.oc.folio}| Req: {no_conf.oc.req.folio}</p>
                        <p>indicando que es una NC de tipo "{no_conf.tipo_nc.nombre}" por el siguiente motivo {no_conf.comentario}</p>
                        <p>El siguiente paso del sistema: Dar seguimiento a NC</p>
                        <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                        <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                    </body>
                </html>
                """
                email = EmailMessage(
                    f'Compra| No conformidad {no_conf.id} OC {no_conf.oc.get_folio}',
                    body=html_message,
                    from_email = 'savia@vordcab.com',
                    to =['ulises_huesc@hotmail.com' ,],#no_conf.oc.proveedor.email,no_conf.oc.creada_por.staff.staff.email,],
                    headers={'Content-Type': 'text/html'}
                    )
                email.content_subtype = "html " # Importante para que se interprete como HTML
                email.send()
            evalua_entrada_completa(articulos_comprados,num_art_comprados, compra)
            no_conf.completo = True
            no_conf.nc_date = date.today()
            no_conf.nc_hora = datetime.now().time()
            no_conf.save()
            messages.success(request,'Has completado la No Conformidad de manera exitosa')
            return redirect('pendientes_entrada')
        else:
            messages.error(request,'No está validando')
    #else:
        #messages.error(request,'Está siguiendo de largo')


    context = {
        'productos_para_select2':productos_para_select2,
        'compra':compra,
        #'articulos':articulos,
        'articulos_nc':articulos_nc,
        'form': form,
        'form2':form2,
        'no_conformidad': no_conformidad,
    }

    return render(request, 'entradas/no_conformidad.html', context)

def update_no_conformidad(request):
    data = json.loads(request.body)
    cantidad = decimal.Decimal(data["cantidad_ingresada"])
    action = data["action"]
    producto_id = int(data["producto"])
    pk = int(data["nc_id"])
    #referencia = data["referencia"]
    producto_comprado = ArticuloComprado.objects.get(id = producto_id)
    nc = No_Conformidad.objects.get(id = pk, completo = False)
    nc_producto = NC_Articulo.objects.filter(articulo_comprado = producto_comprado, nc__oc = producto_comprado.oc, nc__completo = True).aggregate(Sum('cantidad'))
    entradas_producto = EntradaArticulo.objects.filter(articulo_comprado = producto_comprado, entrada__oc = producto_comprado.oc, entrada__completo = True).aggregate(Sum('cantidad'))
    suma_entradas = entradas_producto['cantidad__sum']
    suma_nc_producto = nc_producto['cantidad__sum']
    entradas_producto = EntradaArticulo.objects.filter(articulo_comprado = producto_comprado, entrada__oc = producto_comprado.oc, entrada__completo = True).aggregate(Sum('cantidad_por_surtir'))
    pendientes_surtir = entradas_producto['cantidad_por_surtir__sum']
    if pendientes_surtir == None:   #Esto sucede cuando no hay ningún producto en esos articulos
        pendientes_surtir = 0
    if suma_nc_producto == None:
        suma_nc_producto = 0
    if suma_entradas == None:
        suma_entradas = 0


    nc_item, created = NC_Articulo.objects.get_or_create(nc = nc, articulo_comprado = producto_comprado)
    nc_item.cantidad = cantidad

    if action == "add":
        total_entradas_nc = pendientes_surtir + suma_nc_producto + nc_item.cantidad

        if total_entradas_nc > producto_comprado.cantidad: #Si la cantidad de las entradas es mayor a la cantidad de la compra se rechaza
            messages.error(request,f'La cantidad de entradas sobrepasa la cantidad comprada {suma_entradas} > {cantidad}')
        else:
            #producto_comprado.cantidad_pendiente = producto_comprado.cantidad - total_entradas_nc
            #Cree una variable booleana temporal para quitarlo del seleccionable
            producto_comprado.seleccionado = True
            messages.success(request,f'Has agregado el artículo con éxito {total_entradas_nc}')
            producto_comprado.save()
            nc_item.save()
    elif action == "remove":
        producto_comprado.seleccionado = False
        messages.success(request,'Has eliminado el artículo con éxito')
        #Se borra el elemento de las entradas
        #Guardado de bases de datos
        nc_item.delete()
    return JsonResponse('Item was '+action, safe=False)