from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Max, Exists, OuterRef, Subquery, Avg
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.cache import cache
from compras.models import Compra, ArticuloComprado, Evidencia
from compras.filters import CompraFilter
from compras.views import attach_oc_pdf
from dashboard.models import Inventario, Order, ArticulosparaSurtir
from requisiciones.models import Salidas, ArticulosRequisitados, Requis
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo, Tipo_Nc
from .forms import EntradaArticuloForm, Reporte_CalidadForm, NoConformidadForm, NC_ArticuloForm, Cierre_NCForm
from proveedores_externos.forms import UploadFileForm

from tesoreria.models import Pago
from user.models import Profile
from requisiciones.views import get_image_base64
import json
import decimal
import os
from datetime import date, datetime
from user.decorators import perfil_seleccionado_required, tipo_usuario_requerido
from io import BytesIO
from decimal import Decimal, ROUND_DOWN
from django.core.mail import EmailMessage, BadHeaderError
from smtplib import SMTPException
import socket
# Import Excel Stuff
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
import datetime as dt

# views.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color, black, white
from reportlab.lib.units import cm
from reportlab.lib import colors


# Create your views here.
@perfil_seleccionado_required
def pendientes_entrada(request):
    pk = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk)
    

    if usuario.tipo.nombre == "Admin":
        compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True).order_by('-folio')
        #compras = Compra.objects.filter(req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True).order_by('-folio')
        for compra in compras:
            articulos_entrada  = ArticuloComprado.objects.filter(oc=compra, entrada_completa = False)
            servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
            cant_entradas = articulos_entrada.count()
            cant_servicios = servicios_pendientes.count()
            # Definir la subconsulta para obtener la fecha del primer pago realizado para cada compra
            #primer_pago_subquery = Pago.objects.filter(
            #    oc=OuterRef('pk'),  # Referencia a la compra en la consulta principal
            #    hecho=True
            #    ).order_by('pagado_real').values('pagado_real')[:1]  # Selecciona la fecha del primer pago
            if  cant_entradas == cant_servicios and cant_entradas > 0:
                compra.solo_servicios = True
                compra.save()
            compras = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True, solo_servicios = False).order_by('-folio')
            #compras = Compra.objects.filter(req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True).order_by('-folio')
    elif usuario.tipo.almacen == True:
        compras = Compra.objects.filter(
            Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True)| Q(monto_pagado__gt=0), 
            Q(solo_servicios=False) | (Q(solo_servicios=True) & Q(req__orden__staff=usuario)),
            req__orden__distrito = usuario.distritos,  
            entrada_completa = False, 
            autorizado2= True).order_by('-folio')
        for compra in compras:
            articulos_entrada  = ArticuloComprado.objects.filter(oc=compra, entrada_completa = False)
            servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
            cant_entradas = articulos_entrada.count()
            cant_servicios = servicios_pendientes.count()
            # Definir la subconsulta para obtener la fecha del primer pago realizado para cada compra
            #primer_pago_subquery = Pago.objects.filter(
            #    oc=OuterRef('pk'),  # Referencia a la compra en la consulta principal
            #    hecho=True
            #    ).order_by('pagado_real').values('pagado_real')[:1]  # Selecciona la fecha del primer pago
            if  cant_entradas == cant_servicios and cant_entradas > 0:
                compra.solo_servicios = True
                compra.save()
        #El filtro devuelve todas las compras a crédito (O) pagadas (O) cuyo monto de los pagado sea mayor que 0 (Y)
        # que NO sea un servicio (O) que sea un servicio (Y) del usuario que generó la order (Y)
        # que sea del distrito del usuario (Y) que la entrada NO este completa (Y) que este autorizada 
        compras = Compra.objects.filter(
            Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0),
            Q(solo_servicios=False) | (Q(solo_servicios=False) & Q(req__orden__staff=usuario)),
            req__orden__distrito = usuario.distritos,  
            entrada_completa = False, 
            autorizado2= True).order_by('-folio')
        #compras = Compra.objects.filter(autorizado2= True)
    else:
        compras = Compra.objects.none()


    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

    
    # Ahora, usamos este queryset de compras para filtrar ArticuloComprado.
    articulos_comprados = ArticuloComprado.objects.filter(oc__in=compras, entrada_completa = False).order_by('-oc__folio')

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_matriz_compras_pendientes(articulos_comprados)

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


@perfil_seleccionado_required
def entrada_servicios(request):
    pk = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk)
    print(usuario)
    

    if usuario.tipo.nombre == "Admin":
        compras = Compra.objects.filter(
            Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), 
            req__orden__distrito = usuario.distritos, solo_servicios= True,
            entrada_completa = False, autorizado2= True).order_by('-folio')
    else:
        compras = Compra.objects.filter(
                Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), 
                req__orden__staff = usuario,
                solo_servicios= True,
                entrada_completa = False, 
                autorizado2= True, 
                ).order_by('-folio')
        
        #print(compras)
        for compra in compras:
            articulos_entrada  = ArticuloComprado.objects.filter(oc=compra, entrada_completa = False)
            servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
            cant_entradas = articulos_entrada.count()
            cant_servicios = servicios_pendientes.count()
                
            if  cant_entradas == cant_servicios and cant_entradas > 0:
                compra.solo_servicios = True
                compra.save()
        compras = Compra.objects.filter(
            Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), 
            req__orden__staff = usuario,
            entrada_completa = False, 
            autorizado2= True, 
            solo_servicios = True).order_by('-folio')
        #print(usuario.staff.staff.first_name)


    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs

    
    # Ahora, usamos este queryset de compras para filtrar ArticuloComprado.
    articulos_comprados = ArticuloComprado.objects.filter(oc__in=compras, entrada_completa = False).order_by('-oc__folio')

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_matriz_compras_pendientes(articulos_comprados)

    #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    context = {
        'compras':compras,
        'myfilter':myfilter,
        'compras_list':compras_list,
        }

    return render(request, 'entradas/pendientes_servicios.html', context)

@perfil_seleccionado_required
def pendientes_calidad(request):
    pk = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk)
    
    articulos_entrada = EntradaArticulo.objects.filter(articulo_comprado__producto__producto__articulos__producto__producto__critico = True, liberado = False, articulo_comprado__oc__req__orden__distrito = usuario.distritos)

     #Set up pagination
    p = Paginator(articulos_entrada, 50)
    page = request.GET.get('page')
    articulos_entrada_list = p.get_page(page)

    print(articulos_entrada)
    context = {
        'articulos_entrada_list':articulos_entrada_list,
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/pendientes_calidad.html', context)

@perfil_seleccionado_required
def devolucion_a_proveedor(request):

    articulos = Reporte_Calidad.objects.filter(completo = True, autorizado = False)

    context = {
        'articulos':articulos,
        }

    return render(request, 'entradas/devolucion_a_proveedor.html', context)

def entrada_usada(request):
    return render(request, 'entradas/entrada_been_used.html')


@perfil_seleccionado_required
@tipo_usuario_requerido('almacenista')
def articulos_entrada(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    compra = Compra.objects.get(id=pk)
    try:
        entrada = Entrada.objects.get(oc=compra, almacenista= usuario, completo = False)
    except Entrada.DoesNotExist:
        entrada = None  # Set entrada to None if no matching object is foundexcept 
    
    # Check if the `pk` is currently in use
    #print('entrada_value:', entrada)
    #print(cache.get(f'compra_in_use_{pk}'))
    if cache.get(f'compra_in_use_{pk}') and entrada is None:
        messages.error(request, "This entry is currently being accessed by another user.")
        return redirect('entrada-usada')  # Redirect to another view or template
    # Mark the `pk` as in use in the cache
    cache.set(f'compra_in_use_{pk}', True)  # Lock for 5 minutes (300 seconds)
    
    
    vale_entrada = Entrada.objects.filter(oc__req__orden__distrito = usuario.distritos)
    if usuario.tipo.almacen == True: #and compra.req.orden.staff == usuario:
        articulos = ArticuloComprado.objects.filter(oc=compra, entrada_completa=False, producto__producto__articulos__producto__producto__servicio = False, seleccionado = False)
    else:
        articulos = ArticuloComprado.objects.none()

    entrada, created = Entrada.objects.get_or_create(oc=compra, almacenista= usuario, completo = False)
    articulos_entrada = EntradaArticulo.objects.filter(entrada = entrada)
  
    conteo_de_articulos = articulos.count()
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

    
    form = EntradaArticuloForm()
    #max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
    max_folio = vale_entrada.aggregate(Max('folio'))['folio__max']
    nuevo_folio = (max_folio or 0) + 1
    
    for articulo in articulos:
        if articulo.cantidad_pendiente == None or articulo.cantidad_pendiente == "":
            articulo.cantidad_pendiente = articulo.cantidad


    if request.method == 'POST' and 'entrada' in request.POST:
        articulos_comprados = ArticuloComprado.objects.filter(oc=pk)
        num_art_comprados = articulos_comprados.count()
        max_folio = vale_entrada.aggregate(Max('folio'))['folio__max']
        nuevo_folio = (max_folio or 0) + 1
        entrada.completo = True
        entrada.folio = nuevo_folio
        entrada.entrada_date = datetime.now()
        #max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
        articulos_entregados = articulos_comprados.filter(entrada_completa=True)
        articulos_seleccionados = articulos_entregados.filter(seleccionado = True)
        num_art_entregados = articulos_entregados.count()
        for elemento in articulos_seleccionados:
            elemento.seleccionado = False
            elemento.save()
        
        #Parte para envio de mensaje si hay productos criticos en las entradas
        articulos_html = """
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Producto</th>
                        <th>Requerimiento</th>
                        <th>Comentarios</th>
                    </tr>
                </thead>
                <tbody>
            """
        productos_criticos = articulos_entrada.filter(articulo_comprado__producto__producto__articulos__producto__producto__critico=True)
        for articulo in productos_criticos:
            producto = articulo.articulo_comprado.producto.producto.articulos.producto.producto
            #requerimientos = producto.producto_calidad.requerimientos_calidad.all()
            pc = getattr(producto, "producto_calidad", None)  # o "productocalidad" si no usas related_name
            
            requerimientos = list(pc.requerimientos_calidad.all()) if pc else []
            # Tabla para productos criticos 
            if requerimientos:
                for requerimiento in requerimientos:
                    articulos_html += f"""
                        <tr>
                            <td>{producto.codigo}</td>
                            <td>{producto.nombre}</td>
                            <td>{requerimiento.requerimiento.nombre}</td>
                            <td>{requerimiento.comentarios}</td>
                        </tr>
                    """
            else:
                articulos_html += f"""
                    <tr>
                        <td>{producto.codigo}</td>
                        <td>{producto.nombre}</td>
                        <td>Sin requerimiento</td>
                        <td>Sin comentarios</td>
                    </tr>
                """
            articulos_html += """
                </tbody>
            </table>
            """
        if productos_criticos:
            # Consulta para obtener los usuarios
            calidad_usuarios = Profile.objects.filter(tipo__calidad=True, distritos=compra.req.orden.distrito)
            #calidad_usuarios = Profile.objects.filter(tipo__nombre = 'Admin')
            # Lista de correos electrónicos de los usuarios
            correos = [usuario.staff.staff.email for usuario in calidad_usuarios]
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
                                                    <p>Estimado Supervisor de Calidad,</p>
                                                </p>
                                                <p style="font-size: 16px; text-align: justify;">
                                                    Estás recibiendo este correo porque se ha recibido en almacén los siguientes productos críticos que requieren la liberación por parte de calidad.</p>
                                                <p>Productos a liberar</p>
                                                {articulos_html}
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
                    f'Entrada recibida: {entrada.folio}',
                    body=html_message,
                    from_email =settings.DEFAULT_FROM_EMAIL,
                    to=correos,
                    headers={'Content-Type': 'text/html'}
                    )
                email.content_subtype = "html " # Importante para que se interprete como HTML
                email.send()
                messages.success(request, f'La entrada {entrada.folio} ha sido creada')
            except (BadHeaderError, SMTPException, socket.gaierror) as e:
                error_message = f'La entrada {entrada.folio} ha sido creada, pero el correo no ha sido enviado debido a un error: {e}'
                messages.success(request, error_message)
        for articulo in articulos_entrada:
            producto_surtir2 = ArticulosparaSurtir.objects.filter(articulos = articulo.articulo_comprado.producto.producto.articulos)
            producto_surtir = ArticulosparaSurtir.objects.get(articulos = articulo.articulo_comprado.producto.producto.articulos)
            producto_surtir.seleccionado = False
            print(producto_surtir)
            if producto_surtir.articulos.producto.producto.critico == True:
                print('Esta entrado al ciclo de calidad')
                producto_surtir.surtir = False
                articulo.liberado = False
            ############################################################################ Acá empieza el resurtimiento
            if entrada.oc.req.orden.tipo.tipo == 'resurtimiento': # or 
                #Estas son todas las solicitudes pendientes por surtir que se podrían surtir con el resurtimiento
                productos_pendientes_surtir = ArticulosparaSurtir.objects.filter(
                    articulos__producto__producto = articulo.articulo_comprado.producto.producto.articulos.producto.producto,
                    salida = False, 
                    articulos__orden__tipo__tipo = 'normal',
                    cantidad_requisitar__gt=0,
                    requisitar = True,
                    articulos__producto__distrito = usuario.distritos
                    )
                inv_de_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto, distrito = usuario.distritos)
                print(inv_de_producto.cantidad)
                ################################################################################## Parte crítica del resurtimiento
                for producto in productos_pendientes_surtir:    #Recorremos todas las solicitudes pendientes por surtir una por una
                    if producto_surtir.cantidad > 0:             #Esto practicamente es un while gracias al for mientras la cantidad del resurtimiento sea mayor que 0
                        cantidad_requisitar = Decimal(producto.cantidad_requisitar).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                        cantidad_surtir = Decimal(producto_surtir.cantidad).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                        
                        # Determinamos la cantidad a surtir con min
                        cantidad_a_surtir = min(cantidad_requisitar, cantidad_surtir) #Se elige el mínimo entre la cantidad_requistar y la cantidad a surtir
                        # Realizamos las actualizaciones
                        producto_surtir.cantidad -= cantidad_a_surtir
                        producto.cantidad += cantidad_a_surtir
                        producto.cantidad_requisitar -= cantidad_a_surtir 
                        inv_de_producto.cantidad -= cantidad_a_surtir
                        inv_de_producto.cantidad_entradas -= cantidad_a_surtir
                        producto.surtir = True
                        # Actualizamos el estado del producto si ya no requiere más surtido
                        if producto.cantidad_requisitar == 0:
                            producto.requisitar = False
                           
                        
                        producto_surtir.save()
                        producto.save()
                        inv_de_producto.save()
                        solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                        productos_orden = ArticulosparaSurtir.objects.filter(articulos__orden = solicitud, requisitar=False).count()
                        if productos_orden == 0:
                            solicitud.requisitar = False
                            solicitud.save()
            #######################################################################################################
            elif entrada.oc.req.orden.tipo.tipo == 'normal' and articulo.articulo_comprado.producto.producto.articulos.producto.producto.activo == True:
                print('Activo valores antes de las cuentas')
                inv_de_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto, distrito = usuario.distritos)
                articulo.articulo_comprado.producto.producto.cantidad = 0
                articulo.articulo_comprado.producto.producto.cantidad_requisitar = 0
                articulo.articulo_comprado.producto.producto.surtir = False
                articulo.articulo_comprado.producto.producto.requisitar = False
                inv_de_producto.cantidad += articulo.cantidad
                #inv_de_producto.cantidad_entradas += articulo.cantidad
                inv_de_producto.save()
                articulo.save()
                print('Tiene producto activo esta orden de tipo normal')
            elif entrada.oc.req.orden.tipo.tipo == 'normal':
                if articulo.articulo_comprado.producto.producto.articulos.producto.producto.servicio == True:
                    producto_surtir.surtir = False
                else:
                    producto_surtir.surtir = True
                print('Entrada de tipo normal sin activo')
            producto_surtir.save()
            articulo.save()    
        evalua_entrada_completa(articulos_comprados,num_art_comprados, compra)
        entrada.save()
        messages.success(request, f'La entrada {entrada.folio} se ha realizado con éxito')
        cache.delete(f'compra_is_use_{pk}')
        return redirect('pendientes_entrada')
    
    elif cache.get(f'compra_in_use_{pk}') and usuario !=  entrada.almacenista:
        #messages.error(request, "This entry is currently being accessed by another user.")
        return redirect('entrada-usada')  # Redirect to another view or template

    context = {
        'articulos':articulos,
        'max_folio': nuevo_folio,
        'entrada':entrada,
        'compra':compra,
        'form':form,
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/articulos_entradas.html', context)

@perfil_seleccionado_required
def articulos_entrada_servicios(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    vale_entrada = Entrada.objects.filter(oc__req__orden__distrito = usuario.distritos)
    compra = Compra.objects.get(id = pk)
   
    articulos = ArticuloComprado.objects.filter(
        oc=pk, 
        entrada_completa = False,  
        seleccionado = False, 
        producto__producto__articulos__producto__producto__servicio = True)


    compra = Compra.objects.get(id=pk)
    conteo_de_articulos = articulos.count()


    entrada, created = Entrada.objects.get_or_create(oc=compra, almacenista= usuario, completo = False)
    articulos_entrada = EntradaArticulo.objects.filter(entrada = entrada)
    form = EntradaArticuloForm()
    #max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
    max_folio = vale_entrada.aggregate(Max('folio'))['folio__max']
    nuevo_folio = (max_folio or 0) + 1
    
    for articulo in articulos:
        if articulo.cantidad_pendiente == None or articulo.cantidad_pendiente == "":
            articulo.cantidad_pendiente = articulo.cantidad


    if request.method == 'POST' and 'entrada' in request.POST:
        articulos_comprados = ArticuloComprado.objects.filter(oc=pk)
        num_art_comprados = articulos_comprados.count()
        max_folio = vale_entrada.aggregate(Max('folio'))['folio__max']
        nuevo_folio = (max_folio or 0) + 1
        entrada.completo = True
        entrada.folio = nuevo_folio
        entrada.entrada_date = datetime.now()
        #max_folio = Requis.objects.filter(orden__distrito=usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
        articulos_entregados = articulos_comprados.filter(entrada_completa=True)
        articulos_seleccionados = articulos_entregados.filter(seleccionado = True)
        num_art_entregados = articulos_entregados.count()
        for elemento in articulos_seleccionados:
            elemento.seleccionado = False
            elemento.save()

        for articulo in articulos_entrada:
            producto_surtir = ArticulosparaSurtir.objects.get(articulos = articulo.articulo_comprado.producto.producto.articulos)
            producto_surtir.seleccionado = False
            print(producto_surtir)
            if producto_surtir.articulos.producto.producto.critico == True:
                print('Esta entrado al ciclo de calidad')
                producto_surtir.surtir = False
                articulo.liberado = False
                archivo_oc = attach_oc_pdf(request, articulo.articulo_comprado.oc.id)
            #    email = EmailMessage(
            #            f'Compra Autorizada {compra.get_folio}',
            #            f'Estimado *Inserte nombre de especialista*,\n Estás recibiendo este correo porque se ha recibido en almacén el producto código:{producto_surtir.articulos.producto.producto.codigo} descripción:{producto_surtir.articulos.producto.producto.nombre} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
            #            'savia@vordcab.com',
            #            ['ulises_huesc@hotmail.com'],
            #            )
            #    email.attach(f'OC_folio:{articulo.articulo_comprado.oc.folio}.pdf',archivo_oc,'application/pdf')
            #    email.send()
            elif entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                #Estas son todas las solicitudes pendientes por surtir que se podrían surtir con el resurtimiento
                productos_pendientes_surtir = ArticulosparaSurtir.objects.filter(
                    articulos__producto__producto = articulo.articulo_comprado.producto.producto.articulos.producto.producto,
                    salida = False, 
                    articulos__orden__tipo__tipo = 'normal',
                    cantidad_requisitar__gt=0,
                    articulos__producto__distrito = usuario.distritos
                    )
                inv_de_producto = Inventario.objects.get(producto = producto_surtir.articulos.producto.producto, distrito = usuario.distritos)
                print(inv_de_producto.cantidad)
                for producto in productos_pendientes_surtir:    #Recorremos todas las solicitudes pendientes por surtir una por una
                    if producto_surtir.cantidad > 0:             #Esto practicamente es un while gracias al for mientras la cantidad del resurtimiento sea mayor que 0
                        cantidad_requisitar = Decimal(producto.cantidad_requisitar).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                        cantidad_surtir = Decimal(producto_surtir.cantidad).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                        
                        # Determinamos la cantidad a surtir con min
                        cantidad_a_surtir = min(cantidad_requisitar, cantidad_surtir) #Se elige el mínimo entre la cantidad_requistar y la cantidad a surtir
                        # Realizamos las actualizaciones
                        producto_surtir.cantidad -= cantidad_a_surtir
                        producto.cantidad += cantidad_a_surtir
                        producto.cantidad_requisitar -= cantidad_a_surtir 
                        inv_de_producto.cantidad -= cantidad_a_surtir
                        inv_de_producto.cantidad_entradas -= cantidad_a_surtir
                        
                        # Actualizamos el estado del producto si ya no requiere más surtido
                        if producto.cantidad_requisitar == 0:
                            producto.requisitar = False
                            producto.surtir = True
                        
                        producto_surtir.save()
                        producto.save()
                        inv_de_producto.save()
                        solicitud = Order.objects.get(id = producto_surtir.articulos.orden.id)
                        productos_orden = ArticulosparaSurtir.objects.filter(articulos__orden = solicitud, requisitar=False).count()
                        if productos_orden == 0:
                            solicitud.requisitar = False
                            solicitud.save()
                        
            elif entrada.oc.req.orden.tipo.tipo == 'normal':
                if articulo.articulo_comprado.producto.producto.articulos.producto.producto.servicio == True:
                    producto_surtir.surtir = False
                else:
                    producto_surtir.surtir = True
            producto_surtir.save()
            articulo.save()    
        evalua_entrada_completa(articulos_comprados,num_art_comprados, compra)
        entrada.save()
        messages.success(request, f'La entrada {entrada.folio} se ha realizado con éxito')
        return redirect('entrada-servicios')

    context = {
        'articulos':articulos,
        'max_folio': nuevo_folio,
        'entrada':entrada,
        'compra':compra,
        'form':form,
        'articulos_entrada':articulos_entrada,
        }

    return render(request, 'entradas/servicios_entradas.html', context)

def evalua_entrada_completa(articulos_comprados, num_art_comprados, compra):
    for articulo in articulos_comprados:
        if articulo.cantidad_pendiente == 0:  #Si la cantidad de la compra es igual a la cantidad entonces la entrada está completamente entregada
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
        #entrada = entrada, 
        entrada__completo = True
    ).aggregate(
        suma_cantidad = Sum('cantidad'),                       #Suma de todos los artículos que han entrado
        suma_cantidad_por_surtir = Sum('cantidad_por_surtir') #Suma de todos los articulos que no se han despachado y que ya se les dio entrada
    )

    suma_cantidad = aggregation['suma_cantidad'] or 0
    pendientes_surtir = aggregation['suma_cantidad_por_surtir'] or 0
    #print(suma_cantidad)
    print('suma_cantidad:',suma_cantidad)
    entrada_item, created = EntradaArticulo.objects.get_or_create(entrada = entrada, articulo_comprado = producto_comprado)
    producto_inv = Inventario.objects.get(producto = producto_comprado.producto.producto.articulos.producto.producto, distrito = producto_comprado.oc.req.orden.distrito)

    if entrada.oc.req.orden.tipo.tipo == 'resurtimiento': #si es resurtimiento
        #Esto es solo el artículo original
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
        print('total entradas:',total_entradas)
        if total_entradas > producto_comprado.cantidad: #Si la cantidad de las entradas es mayor a la cantidad de la compra se rechaza
            messages.error(request,f'La cantidad de entradas sobrepasa la cantidad comprada {suma_cantidad} > {cantidad}')
        else:
            print('cantidad pendiente:',producto_comprado.cantidad_pendiente)
            #print(total_entradas)
            producto_comprado.cantidad_pendiente = producto_comprado.cantidad - total_entradas
            print('cantidad pendiente2:',producto_comprado.cantidad_pendiente)
            producto_comprado.save()
            
            if producto_inv.producto.servicio == False:
                if cantidad_inventario == 0:
                    precio_unit_promedio = producto_comprado.precio_unitario
                else:
                    precio_unit_promedio = monto_total/nueva_cantidad_inventario

                producto_inv.price = precio_unit_promedio

            if producto_inv.producto.critico == False:
            ##########################################################InicioEvitar
                #Esta parte determina el comportamiento de todos las solicitudes que se tienen que activar cuando la entrada es de resurtimiento
                if entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                    if producto_surtir: #producto_surtir es la solicitud de la que proviene el resurtimiento (ArticulosparaSurtir)
                        producto_inv.cantidad_entradas = pendientes_surtir + entrada_item.cantidad #la cantidad de entrada es igual a la sumatoria de la cantidad pendiente_surtir + cantidad de la entrada 
                        producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - entrada_item.cantidad 
                        producto_inv.cantidad = producto_inv.cantidad + entrada_item.cantidad 
                        if producto_surtir.cantidad_requisitar == 0:
                            producto_surtir.requisitar = False
                        producto_surtir.precio = producto_comprado.precio_unitario
                        producto_surtir.save()
                        producto_inv.save()
                    producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para resurtimiento'
                else:
                    producto_inv.cantidad_entradas = pendientes_surtir + entrada_item.cantidad #Todo lo que está pendiente en una entrada más la entrada misma
                    producto_inv.cantidad_apartada = producto_inv.apartada_entradas        #No se si esto siga teniendo sentido
                    producto_surtir.cantidad = producto_surtir.cantidad + entrada_item.cantidad                       #Al producto disponible para surtir se le suma lo que entra
                    #Es probable que esta cantidad ya le esté restando en otro lado
                    producto_surtir.cantidad_requisitar = producto_surtir.cantidad_requisitar - entrada_item.cantidad   #Al producto pendiente por requisitar se le resta lo que entra
                    producto_inv.save()
                    producto_inv._change_reason = 'Se modifica el inventario en view: update_entrada. Esto es una entrada para solicitud normal'
                    entrada.entrada_date = date.today()
                    entrada.entrada_hora = datetime.now().time()
                    entrada.save()
                    producto_surtir.save()
            #Se guardan todas las bases de datos
            ##########################################################Fin

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
            monto_total = monto_inventario
            print('monto_total:',monto_total)
        else:
            monto_total = 0
        if monto_total == 0:
            producto_inv.price = 0
        else:
            if cantidad_inventario == 0:
                producto_inv.price = 0
            else:
                producto_inv.price = monto_total/cantidad_inventario or 0
        if producto_inv.producto.critico == False:
            #########################################################################InicioEvitar     
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
            #######################################################################Fin
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
    

@perfil_seleccionado_required
def reporte_calidad(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    articulo_entrada = EntradaArticulo.objects.get(id = pk)
    form = Reporte_CalidadForm()
    evidencias = Evidencia.objects.filter(oc = articulo_entrada.entrada.oc)
    form_evidencia = UploadFileForm()
    calidad_producto = Reporte_Calidad.objects.filter(articulo = articulo_entrada, completo = True)
    reporte_actual, created = Reporte_Calidad.objects.get_or_create(articulo = articulo_entrada, completo = False)
    sum_articulos_reportes = 0
    requerimientos = articulo_entrada.articulo_comprado.producto.producto.articulos.producto.producto.producto_calidad.requerimientos_calidad.all()

    for item in calidad_producto:
        sum_articulos_reportes = item.cantidad + sum_articulos_reportes


    restantes_liberacion = articulo_entrada.cantidad - sum_articulos_reportes
    #print(restantes_liberacion)

    if request.method =='POST':
        print('Entró al post')
        if 'btn_evidencia' in request.POST:
            form_evidencia = UploadFileForm(request.POST, request.FILES)
            files_evidencia = request.FILES.getlist('evidencia_file')
            comentario = request.POST.get('comentario', None)
            if not files_evidencia:
                messages.error(request, 'Debes subir al menos un archivo de evidencia.')
            else: 
                for archivo_evidencia in files_evidencia:
                    Evidencia.objects.create(
                        oc=articulo_entrada.entrada.oc,
                        file=archivo_evidencia,
                        hecho=True,
                        uploaded=datetime.now(),
                        subido_por=perfil,
                        comentario=comentario
                    )
                messages.success(request, 'Las evidencias se subieron correctamente.')
            return redirect('reporte_calidad', pk=pk)
        if 'reporte' in request.POST:
            form = Reporte_CalidadForm(request.POST, request.FILES, instance = reporte_actual)
            print(form)
            print(decimal.Decimal(request.POST['cantidad']) )
            if decimal.Decimal(request.POST['cantidad']) <=  restantes_liberacion:
                if not request.POST['autorizado'] == None:
                    #if item.cantidad <= 0:
                    if form.is_valid():

                        item = form.save(commit=False)
                        item.articulo = articulo_entrada
                        item.reporte_date = date.today()
                        item.reporte_hora = datetime.now().time()
                        producto_surtir = ArticulosparaSurtir.objects.get(articulos = articulo_entrada.articulo_comprado.producto.producto.articulos)
                        articulos_restantes = articulo_entrada.cantidad - item.cantidad - sum_articulos_reportes
                        if item.autorizado == True:
                            if articulos_restantes == 0:
                                articulo_entrada.liberado = True
                                articulo_entrada.cantidad_por_surtir = articulo_entrada.cantidad_por_surtir + item.cantidad
                            #Lo estoy comentando porque según yo la cantidad ya está afectada en la cantidad en entró el sumarle sería afectarlo doble 
                            #Ya hice la verificación  no hay doble afectación a item, lo que haría falta es si el item proviene de un resurtimiento
                            if articulo_entrada.entrada.oc.req.orden.tipo.tipo == 'resurtimiento':
                                inventario = Inventario.objects.get(producto = articulo_entrada.articulo_comprado.producto.producto.articulos.producto, distrito = articulo_entrada.articulo_comprado.oc.req.orden.distrito)
                                inventario.cantidad = inventario.cantidad + item.cantidad
                                inventario.change_reason = 'Se modifica el inventario en view: reporte_calidad. Esto es una entrada para resurtimiento'
                                inventario.cantidad_entradas = inventario.cantidad_entradas + item.cantidad
                                inventario.save()

                            else:
                                producto_surtir.cantidad = producto_surtir.cantidad + item.cantidad
                                producto_surtir.surtir = True
                                producto_surtir.save()
                                producto = producto_surtir.articulos.producto
                                producto.cantidad_entradas += item.cantidad
                                producto.save()

                        if item.autorizado == False:
                        
                            #Esta condicional solo afectara la cantidad de articulos en la entrada si ya son los ultimos articulos dentro de la liberacion
                            #Esto es porque en caso de no ser así genera un error en las cantidades 
                            if restantes_liberacion == item.cantidad:
                                print(restantes_liberacion, item.cantidad)
                                articulo_entrada.cantidad = articulo_entrada.cantidad - item.cantidad
                            #Si hay un rechazo, se tienen que evaluar varias cuestiones
                            #1. Se tiene que afectar la cantidad de articulos entrada
                            articulo_entrada.cantidad_por_surtir = articulo_entrada.cantidad_por_surtir - item.cantidad
                            #2 El producto por surtir se tiene que decrementar porque se afectó en la vista update_entrada
                            producto_surtir.cantidad = producto_surtir.cantidad - item.cantidad
                            articulo_entrada.save()
                            producto_surtir.save()
                            #3 Si la cantidad del articulo y la entrada prácticamente se tendría que cancelar
                            if producto_surtir.cantidad == 0:
                                entrada = Entrada.objects.get(id = articulo_entrada.entrada.id)
                                entrada.cancelada = True
                                entrada.save()
                            #Si el item no es autorizado por calidad, se crea una NC
                            
                            tipo_nc = Tipo_Nc.objects.get(id = 2)
                            no_conformidad, created = No_Conformidad.objects.get_or_create(
                                oc = articulo_entrada.entrada.oc, 
                                almacenista=perfil, 
                                comentario = item.comentarios,
                                tipo_nc= tipo_nc,
                                completo = True, 
                                nc_date = date.today(),
                                nc_hora = datetime.now().time())
                            no_conformidad.save()
                            articulos_nc = NC_Articulo.objects.create(
                                nc = no_conformidad,
                                cantidad = item.cantidad,
                                articulo_comprado = articulo_entrada.articulo_comprado)
                            print('articulos_nc')
                            if articulos_restantes == 0:
                                articulo_entrada.liberado = True
                            articulos_nc.save()
                        articulo_entrada.save()
                        item.completo = True
                        item.save()
                        messages.success(request, 'Has generado exitosamente tu reporte')
                        return redirect('pendientes_calidad')
                else:
                    messages.error(request, 'Debes elegir un Status de liberación')
            else:
                messages.error(request, 'La cantidad liberada no puede ser mayor que cantidad de entradas restante')

    #else:
        #form = InventarioForm()

    context = {
        'evidencias': evidencias,
        'form': form,
        'articulo_entrada':articulo_entrada,
        'restantes_liberacion': restantes_liberacion,
        'requerimientos': requerimientos,
        }

    return render(request,'entradas/calidad_entrada.html',context)

@perfil_seleccionado_required
def matriz_nc(request):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    if perfil.tipo.nombre == "VIS_ADQ":
        ncs= No_Conformidad.objects.filter(completo = True)
    else:
        ncs= No_Conformidad.objects.filter(completo = True, oc__req__orden__distrito = perfil.distritos)
    

    context = {
        #'form': form,
        'ncs': ncs,
        'perfil': perfil,
        }

    return render(request,'entradas/matriz_nc.html',context)

@perfil_seleccionado_required
def productos_nc(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    articulos_nc = NC_Articulo.objects.filter(nc = pk)

    context = {
        'articulos_nc': articulos_nc,
    }

    return render(request, 'entradas/productos_nc.html', context)

@perfil_seleccionado_required
def cierre_nc(request, pk):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    nc = No_Conformidad.objects.get(id = pk)
    articulos_nc = NC_Articulo.objects.filter(nc = pk).first()
    form = Cierre_NCForm(instance = nc)

    if request.method == "POST":
        #and 'BtnCrear' in request.POST:
        form = Cierre_NCForm(request.POST, request.FILES, instance = nc)

        if form.is_valid():
            nc = form.save(commit=False)
            nc.fecha_cierre = date.today()
            nc.save()
            oc = Compra.objects.get(id = nc.oc.id)
            producto = ArticuloComprado.objects.get(id = articulos_nc.articulo_comprado.id)
            if nc.cierre.id == 3:
                #Se debería de reactivas la OC, en la variable entrada_completa = False
                oc.entrada_completa = False
                producto.entrada_completa = False
                producto.cantidad_pendiente = producto.cantidad_pendiente - articulos_nc.cantidad
                oc.save()
                producto.save()
            else:
                oc.entrada_completa = False
                oc.pagada = False #Estaba comentada la variable, pareciera que no funcionó en su momento
                oc.save()
                producto.entrada_completa = False
                producto.cantidad_pendiente = producto.cantidad_pendiente - articulos_nc.cantidad
                producto.save()

            return redirect('matriz-nc')

           

    context = {
        'form': form,
        'nc': nc,
        'articulos_nc': articulos_nc,
    }

    return render(request, 'entradas/cierre_nc.html', context)

@perfil_seleccionado_required
def matriz_reportes_calidad(request):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    reportes = Reporte_Calidad.objects.filter(completo = True, articulo__entrada__oc__req__orden__distrito = perfil.distritos)
    form = Reporte_CalidadForm()
    #articulos_reportes = Reporte_Calidad.objects.filter(articulo = articulo_entrada, completo = True)
    #reporte_actual, created = Reporte_Calidad.objects.get_or_create(articulo = articulo_entrada, completo = False)
    #sum_articulos_reportes = 0

    #for item in articulos_reportes:
    #    sum_articulos_reportes = item.cantidad + sum_articulos_reportes

    #restantes_liberacion = articulo_entrada.cantidad - sum_articulos_reportes


    context = {
        #'form': form,
        'reportes':reportes,
        #'restantes_liberacion': restantes_liberacion,
        }

    return render(request,'entradas/matriz_reportes_calidad.html',context)

@perfil_seleccionado_required
def productos(request, pk):
    compra = Compra.objects.get(id=pk)
    articulos_comprados = ArticuloComprado.objects.filter(oc=compra, entrada_completa=False)

    context = {
        'compra': compra,
        'articulos_comprados': articulos_comprados,
    }

    return render(request, 'entradas/productos.html', context)

@perfil_seleccionado_required
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
                    total_cantidad = EntradaArticulo.objects.filter(entrada__oc = compra, articulo_comprado = articulo.articulo_comprado).aggregate(total=Sum('cantidad'))['total']
                except ObjectDoesNotExist:
                    articulo_entradas = None
                
                
                cantidad_entradas = total_cantidad or 0
              
                articulo_requisitado = ArticulosRequisitados.objects.get(req=compra.req, producto=articulo.articulo_comprado.producto.producto)
                if articulo_comprado.cantidad_pendiente == None:
                    articulo_comprado.cantidad_pendiente = 0
                #Todo esto debería de pasar solo si la NC ya no se va a recibir es decir si el tipo de la conformidad = Material no disponible
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
                        <p>Estimado {no_conf.oc.creada_por.staff.staff.first_name} {no_conf.oc.creada_por.staff.staff.last_name},</p>
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
    #Solo se evaluan las cantidades pero no se afectan
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
        print(pendientes_surtir)
        print(suma_nc_producto)
        print(nc_item.cantidad)
        total_entradas_nc = pendientes_surtir + suma_nc_producto + nc_item.cantidad

        if total_entradas_nc > producto_comprado.cantidad: #Si la cantidad de las entradas es mayor a la cantidad de la compra se rechaza
            messages.error(request,f'La cantidad de entradas sobrepasa la cantidad comprada {total_entradas_nc} > {cantidad}')
        else:
            #producto_comprado.cantidad_pendiente = producto_comprado.cantidad - total_entradas_nc
            #Cree una variable booleana temporal para quitarlo del seleccionable
            producto_comprado.seleccionado = True
            messages.success(request,f'Has agregado el artículo con éxito {total_entradas_nc}')
            producto_comprado.save()
            nc_item.save()
    elif action == "remove":
        producto_comprado.seleccionado = False
        
        #Se borra el elemento de las entradas
        #Guardado de bases de datos
        nc_item.delete()
        producto_comprado.save()
        messages.success(request,'Has eliminado el artículo con éxito')
    return JsonResponse('Item was '+action, safe=False)


def convert_excel_matriz_compras_pendientes(articulos_comprados):
      #print('si entra a la función')
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Producto_pendientes")

     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})

    columns = ['Compra', 'Requisición','Solicitud', 'Codigo', 'Producto', 'Cantidad Pendiente', 'Unidad','Proveedor',
               'Usuario Solicitante','Pagada','Ultimo pago']

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA Vordcab. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Grupo Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    
   
    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    worksheet.set_column('L:L', 12,  money_style)
    worksheet.set_column('M:M', 12, money_style) 
    # Asumiendo que ya tienes tus datos de compras
    row_num = 0
    for articulo in articulos_comprados:
        row_num += 1
        # Aquí asumimos que ya hiciste el procesamiento necesario de cada compra
        pagos = Pago.objects.filter(oc=articulo.oc)
        if pagos:
            ultimo = pagos.last()
        else:
            ultimo = None
        if articulo.oc.pagada == True:
            pago = 'Pagada'
        elif articulo.oc.pagada == False and ultimo:
            pago = 'Pagada parcialmente'
        else:
            pago = 'No pagado'
        if pagos:
            ultimo = pagos.last()
            if ultimo.pagado_date:
                ultimo = str(ultimo.pagado_date.date())
            else:
                ultimo = ''
        else:
            ultimo = ''
        row = [
            articulo.oc.folio,
            articulo.oc.req.folio,
            articulo.oc.req.orden.folio,
            articulo.producto.producto.articulos.producto.producto.codigo,
            articulo.producto.producto.articulos.producto.producto.nombre,
            articulo.cantidad_pendiente if articulo.cantidad_pendiente != None else articulo.cantidad,
            articulo.producto.producto.articulos.producto.producto.unidad.nombre,
            articulo.oc.proveedor.nombre.razon_social,
            f"{articulo.oc.req.orden.staff.staff.staff.first_name} {articulo.oc.req.orden.staff.staff.staff.last_name}",
            pago,
            ultimo,
            
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

      
        #worksheet.write_formula(row_num, 19, f'=IF(ISBLANK(R{row_num+1}), L{row_num+1}, L{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Producto_pendientes_entrada_{dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response



PRUSSIAN_BLUE = Color(0.0859375, 0.1953125, 0.30859375)

def generar_pdf_reporte_calidad_individual(request, reporte_id):
    try:
        reporte = Reporte_Calidad.objects.select_related(
            "articulo__articulo_comprado__oc",
            "articulo__articulo_comprado__producto__producto__articulos__orden__proyecto",
            "articulo__articulo_comprado__producto__producto__articulos__orden__subproyecto",
        ).get(id=reporte_id)
    except Reporte_Calidad.DoesNotExist:
        raise Http404("Reporte no encontrado")

    compra = reporte.articulo.articulo_comprado.oc
    producto = reporte.articulo.articulo_comprado.producto.producto.articulos.producto.producto
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # --- Encabezado estilo Vordcab ---
    y = _draw_header(c, compra)

    # --- Título del reporte ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawCentredString(300, y - 20, "REPORTE DE CALIDAD")
    y -= 40

    # --- Datos generales ---
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    c.drawString(40, y, f"Folio OC: {compra.folio}")
    c.drawString(250, y, f"Proveedor: {compra.proveedor.nombre if compra.proveedor else ''}")
    y -= 20
    c.drawString(40, y, f"Proyecto: {reporte.articulo.articulo_comprado.producto.producto.articulos.orden.proyecto.nombre}")
    c.drawString(250, y, f"Subproyecto: {reporte.articulo.articulo_comprado.producto.producto.articulos.orden.subproyecto.nombre}")
    y -= 30

    # --- Información del producto ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Producto inspeccionado:")
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    y -= 15
    c.drawString(50, y, f"{producto.codigo} | {producto.nombre}")
    y -= 15
    c.drawString(50, y, f"Unidad: {producto.unidad.nombre if producto.unidad else ''}")
    y -= 25

    # --- Información del reporte ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Detalles del reporte:")
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    y -= 15
    c.drawString(50, y, f"Fecha: {reporte.reporte_date or 'N/A'}")
    c.drawString(250, y, f"Hora: {reporte.reporte_hora or 'N/A'}")
    y -= 15
    c.drawString(50, y, f"Cantidad revisada: {reporte.cantidad}")
    y -= 15
    c.drawString(50, y, f"Completo: {'Sí' if reporte.completo else 'No'}")
    c.drawString(250, y, f"Autorizado: {'Sí' if reporte.autorizado else 'Pendiente'}")
    y -= 15
    c.drawString(50, y, f"Comentarios: {reporte.comentarios or 'Sin comentarios'}")
    y -= 30

    # --- Requerimientos de criticidad ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Requerimientos de criticidad:")
    y -= 15
    c.setFont("Helvetica", 10)
    c.setFillColor(black)

    producto_calidad = getattr(producto, "producto_calidad", None)
    requerimientos = producto_calidad.requerimientos_calidad.all() if producto_calidad else []
    if requerimientos:
        for req in requerimientos:
            c.drawString(50, y, f"• {req.requerimiento.nombre}: {req.comentarios}")
            y -= 12
            if y < 100:
                c.showPage()
                y = _draw_header(c, compra)
                y -= 40
    else:
        c.drawString(50, y, "Sin requerimientos definidos.")
        y -= 20

    # --- Imagen del reporte ---
    if reporte.image:
        try:
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(PRUSSIAN_BLUE)
            c.drawString(40, y, "Evidencia fotográfica:")
            y -= 10
            c.drawImage(reporte.image.path, 60, y - 120, width=120, height=120)
            y -= 140
        except Exception:
            c.setFillColor(black)
            c.drawString(50, y, "(No se pudo cargar la imagen del reporte)")
            y -= 15

    # --- Pie de página ---
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(black)
    c.drawCentredString(300, 40, "Documento generado automáticamente por SAVIA 2.0")

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Reporte_Calidad_{reporte.id}.pdf"'
    response.write(pdf)
    return response



def pdf_reporte_calidad(request, reporte_id):
    PRUSSIAN_BLUE = Color(0.0859375, 0.1953125, 0.30859375)

    try:
        reporte = Reporte_Calidad.objects.select_related(
            "articulo__articulo_comprado__oc",
            "articulo__articulo_comprado__producto__producto__articulos__orden__proyecto",
            "articulo__articulo_comprado__producto__producto__articulos__orden__subproyecto",
        ).get(id=reporte_id)
    except Reporte_Calidad.DoesNotExist:
        raise Http404("Reporte no encontrado")

    compra = reporte.articulo.articulo_comprado.oc
    producto = reporte.articulo.articulo_comprado.producto.producto.articulos.producto.producto
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # --- Encabezado estilo Vordcab ---
    y = _draw_header(c, compra)

    # Sello de estado (usa reporte.autorizado)
    _draw_status_badge(c, reporte.autorizado)
    # (Opcional) Watermark diagonal suave
    _draw_watermark_if_needed(c, reporte.autorizado)


    # --- Título del reporte ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawCentredString(300, y - 20, "REPORTE DE CALIDAD")
    y -= 40

    # --- Datos generales ---
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    c.drawString(40, y, f"Folio OC: {compra.folio}")
    c.drawString(250, y, f"Proveedor: {compra.proveedor.nombre if compra.proveedor else ''}")
    y -= 20
    c.drawString(40, y, f"Proyecto: {reporte.articulo.articulo_comprado.producto.producto.articulos.orden.proyecto.nombre}")
    c.drawString(40, y - 12, f"Subproyecto: {reporte.articulo.articulo_comprado.producto.producto.articulos.orden.subproyecto.nombre}")
    y -= 30

    # --- Información del producto ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Producto inspeccionado:")
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    y -= 15
    c.drawString(50, y, f"{producto.codigo} | {producto.nombre}")
    y -= 15
    c.drawString(50, y, f"Unidad: {producto.unidad.nombre if producto.unidad else ''}")
    y -= 25

    # --- Información del reporte ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Detalles del reporte:")
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    y -= 15
    c.drawString(50, y, f"Fecha: {reporte.reporte_date or 'N/A'}")
    c.drawString(250, y, f"Hora: {reporte.reporte_hora or 'N/A'}")
    y -= 15
    c.drawString(50, y, f"Cantidad revisada: {reporte.cantidad}")
    y -= 15
    c.drawString(50, y, f"Completo: {'Sí' if reporte.completo else 'No'}")
    c.drawString(250, y, f"Autorizado: {'Sí' if reporte.autorizado else 'Pendiente'}")
    y -= 15
    c.drawString(50, y, f"Comentarios: {reporte.comentarios or 'Sin comentarios'}")
    y -= 30

    # --- Requerimientos de criticidad ---
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRUSSIAN_BLUE)
    c.drawString(40, y, "Requerimientos de criticidad:")
    y -= 15
    c.setFont("Helvetica", 10)
    c.setFillColor(black)

    producto_calidad = getattr(producto, "producto_calidad", None)
    requerimientos = producto_calidad.requerimientos_calidad.all() if producto_calidad else []
    if requerimientos:
        for req in requerimientos:
            c.drawString(50, y, f"• {req.requerimiento.nombre}: {req.comentarios}")
            y -= 12
            if y < 100:
                c.showPage()
                y = _draw_header(c, compra)
                y -= 40
    else:
        c.drawString(50, y, "Sin requerimientos definidos.")
        y -= 20

    # --- Imagen del reporte ---
    if reporte.image:
        try:
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(PRUSSIAN_BLUE)
            c.drawString(40, y, "Evidencia fotográfica:")
            y -= 10
            c.drawImage(reporte.image.path, 60, y - 200, width=200, height=200, preserveAspectRatio=True, mask='auto')
            y -= 140
        except Exception:
            c.setFillColor(black)
            c.drawString(50, y, "(No se pudo cargar la imagen del reporte)")
            y -= 15

    # --- Pie de página ---
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(black)
    c.drawCentredString(300, 40, "Documento generado automáticamente por SAVIA 2.0")

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Reporte_Calidad_{reporte.id}.pdf"'
    response.write(pdf)
    return response


# Encabezado corporativo reutilizable
def _draw_header(c, compra):
    prussian_blue = PRUSSIAN_BLUE
    c.setFillColor(black)
    c.setFont('Helvetica', 8)
    caja_iso = 760

    c.drawString(430, caja_iso, 'Preparado por:')
    #c.drawString(405, caja_iso - 10, 'SUPT. DE ADQUISIONES')
    c.drawString(520, caja_iso, 'Aprobación')
    c.drawString(515, caja_iso - 10, 'SUBD ADTVO')
    c.drawString(150, caja_iso - 20, 'Número de documento')
    #c.drawString(160, caja_iso - 30, 'SEOV-ADQ-N4-01.02')
    c.drawString(245, caja_iso - 20, 'Clasificación del documento')
    c.drawString(275, caja_iso - 30, 'Controlado')
    c.drawString(355, caja_iso - 20, 'Nivel del documento')
    c.drawString(380, caja_iso - 30, 'N5')
    c.drawString(440, caja_iso - 20, 'Revisión No.')
    #c.drawString(452, caja_iso - 30, '003')
    c.drawString(510, caja_iso - 20, 'Fecha de Emisión')
    #c.drawString(525, caja_iso - 30, '13/11/2017')

    c.setFillColor(prussian_blue)
    c.rect(150, 750, 250, 20, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(280, 755, 'Reporte de Calidad')
    c.setFillColor(black)
    c.drawInlineImage('static/images/logo_vordcab.jpg', 45, 730, 3 * cm, 1.5 * cm)
    return 700

def _draw_status_badge(c, status, x=400, y=705):
    """
    Dibuja un badge de estado en la esquina superior derecha.
    status: True -> AUTORIZADO (verde)
            False -> NO AUTORIZADO (rojo)
            None -> PENDIENTE (ámbar)
    (x,y) es la esquina inferior-izquierda del badge.
    """
    if status is True:
        txt, fill = "LIBERADO POR CALIDAD", colors.green
    elif status is False:
        txt, fill = "NO LIBERADO POR CALIDAD", colors.red
    else:
        txt, fill = "PENDIENTE", colors.orange

    # Caja
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.rect(x- 10, y, 150, 22, fill=True, stroke=False)

    # Texto
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    # Centrar horizontalmente en la caja (130 de ancho)
    c.drawCentredString(x + 65, y + 6, txt)

def _draw_watermark_if_needed(c, status):
    """
    Watermark diagonal suave según el estado.
    Solo para NO AUTORIZADO (rojo) o PENDIENTE (ámbar).
    """
    if status is True:
        return
    c.saveState()
    c.setFont("Helvetica-Bold", 60)
    c.setFillColor(colors.lightcoral if status is False else colors.lightgoldenrodyellow)
    # Girar y posicionar
    c.translate(120, 200)
    c.rotate(30)
    c.drawString(0, 0, "NO LIBERADO" if status is False else "PENDIENTE")
    c.restoreState()