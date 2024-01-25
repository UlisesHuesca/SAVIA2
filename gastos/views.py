from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Prefetch, Max
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings

from .models import Solicitud_Gasto, Articulo_Gasto, Entrada_Gasto_Ajuste, Conceptos_Entradas, Factura, Tipo_Gasto
from .forms import Solicitud_GastoForm, Articulo_GastoForm, Articulo_Gasto_Edit_Form, Pago_Gasto_Form,  Entrada_Gasto_AjusteForm, Conceptos_EntradasForm, FacturaForm #Articulo_Gasto_Factura_Form,
from .filters import Solicitud_Gasto_Filter
from user.models import Profile
from dashboard.models import Inventario, Order, ArticulosparaSurtir, ArticulosOrdenados, Tipo_Orden, Product
from solicitudes.models import Proyecto, Subproyecto, Operacion
from tesoreria.models import Pago, Cuenta
from tesoreria.forms import Facturas_Gastos_Form 
from compras.views import attach_oc_pdf
from requisiciones.views import get_image_base64

#PDF generator
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter, portrait
from reportlab.rl_config import defaultPageSize 
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from bs4 import BeautifulSoup


from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
import json
import xml.etree.ElementTree as ET
import decimal
import os
import io
from user.decorators import perfil_seleccionado_required

# Create your views here.
@perfil_seleccionado_required
@login_required(login_url='user-login')
def crear_gasto(request):
    colaborador = Profile.objects.all()
    articulos_gasto = Articulo_Gasto.objects.all()
    conceptos = Product.objects.all()
    pk = request.session.get('selected_profile_id')
    usuario = colaborador.get(id = pk)
    if usuario.tipo.superintendente and not usuario.tipo.nombre == "Admin":
        superintendentes = colaborador.filter(staff =  usuario.staff )  
    else:
        superintendentes = colaborador.filter(tipo__superintendente=True, distritos = usuario.distritos).exclude(tipo__nombre="Admin")
    
    proyectos = Proyecto.objects.filter(activo=True, distrito = usuario.distritos)
    #subproyectos = Subproyecto.objects.all()
    tipos = Tipo_Gasto.objects.filter()
    colaboradores = colaborador.filter(distritos = usuario.distritos)

    
    tipos_para_select2 = [
        {
            'id': item.id,
            'text': str(item.tipo)
        } for item in tipos
    ]


    proyectos_para_select2 = [
        {
            'id': item.id, 
            'text': str(item.nombre)
        } for item in proyectos
    ]

    superintendentes_para_select2 = [
        {
            'id': super.id, 
            'text': str(super.staff.staff.first_name) + (' ') + str(super.staff.staff.last_name)
        } for super in superintendentes
    ]

    gasto, created = Solicitud_Gasto.objects.get_or_create(complete= False, staff=usuario)

    max_folio = Solicitud_Gasto.objects.filter(distrito = usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']

    
    articulo, created = articulos_gasto.get_or_create(completo = False, staff=usuario)

    productos = articulos_gasto.filter(gasto=gasto, completo = True)

    
    colaboradores_para_select2 = [
        {
            'id': item.id,
            'text': str(item.staff.staff.first_name) + (' ') + str(item.staff.staff.last_name)
        } for item in colaboradores
    ]
    

    articulos_gasto = conceptos.filter(gasto = True)
    facturas = Factura.objects.filter(solicitud_gasto = gasto)
    form_product = Articulo_GastoForm()
    form = Solicitud_GastoForm()
    factura_form = FacturaForm()

    productos_para_select2 = [
        {
            'id': item.id,
            'text': str(item.nombre),
            'iva': str(item.iva)
        } for item in articulos_gasto
    ]

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = Solicitud_GastoForm(request.POST, instance=gasto)
            #abrev= usuario.distrito.abreviado
            if form.is_valid():
                max_folio = Solicitud_Gasto.objects.filter(distrito = usuario.distritos, complete=True).aggregate(Max('folio'))['folio__max']
                gasto.folio = max_folio + 1
                gasto.distrito = usuario.distritos
                gasto = form.save(commit=False)
                gasto.complete = True
                gasto.created_at = datetime.now()
                gasto.staff =  usuario
                gasto.save()
                form.save()
                messages.success(request, f'La solicitud {gasto.folio} ha sido creada')
                return redirect('solicitudes-gasto')
        if "btn_producto" in request.POST:
            form_product = Articulo_GastoForm(request.POST, request.FILES or None, instance=articulo)
            if form_product.is_valid():
                articulo = form_product.save(commit=False)
                articulo.gasto = gasto
                articulo.completo = True
                articulo.save()
                messages.success(request, 'Haz agregado un artículo correctamente')
                return redirect('crear-gasto')
        if "btn_factura" in request.POST:
            factura_form = FacturaForm(request.POST, request.FILES)
            if factura_form.is_valid():
                factura = factura_form.save(commit=False)
                factura.solicitud_gasto = gasto  # Asume que ya tienes una instancia de Solicitud_Gasto en 'gasto'
                factura.fecha_subida = datetime.now()
                factura.save()
                messages.success(request, 'Factura agregada correctamente.')
                return redirect('crear-gasto')

    #total = sum([factura.emisor['total'] for factura in facturas if factura.emisor and 'total' in factura.emisor and factura.emisor['total']])



    context= {
        'tipos_para_select2':tipos_para_select2,
        'colaboradores_para_select2':colaboradores_para_select2,
        'superintendentes_para_select2':superintendentes_para_select2,
        'proyectos_para_select2':proyectos_para_select2,
        'productos_para_select2':productos_para_select2,
        'facturas':facturas,
        'productos':productos,
        #'colaborador':colaborador,
        'form':form,
        #'total': total,
        'form_product': form_product,
        #'articulos':articulos,
        #'articulos_gasto':articulos_gasto,
        'gasto':gasto,
        #'superintendentes':superintendentes,
        #'proyectos':proyectos,
        #'subproyectos':subproyectos,
        'factura_form': factura_form,
    }
    return render(request, 'gasto/crear_gasto.html', context)

def delete_gasto(request, pk):
    articulo = Articulo_Gasto.objects.get(id=pk)
    messages.success(request,f'El articulo {articulo.producto} ha sido eliminado exitosamente')
    articulo.delete()

    return redirect('crear-gasto')

def eliminar_factura(request, pk):
    articulo = Factura.objects.get(id=pk)
    messages.success(request,f'La factura {articulo.id} ha sido eliminada exitosamente')
    articulo.delete()

    return redirect('crear-gasto')

def editar_gasto(request, pk):
    producto = Articulo_Gasto.objects.get(id=pk)

    form = Articulo_Gasto_Edit_Form(instance=producto)

    if request.method =='POST':
        form = Articulo_Gasto_Edit_Form(request.POST, instance=producto)

        if form.is_valid():
            form.save()

            messages.success(request,f'Se ha guardado el artículo {producto} correctamente')
            return HttpResponse(status=204)
        #else:
            #messages.error(request,'Se lo llevo SPM')


    context= {
        'producto': producto,
        'form': form,
        }

    return render(request, 'gasto/editar_gasto.html', context)

@perfil_seleccionado_required
@login_required(login_url='user-login')
def solicitudes_gasto(request):
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)

    # Preparar un Prefetch para articulos_gasto
    articulos_gasto_prefetch = Prefetch('articulo_gasto_set', queryset=Articulo_Gasto.objects.filter(completo=True, producto__isnull=False, proyecto__isnull=False), to_attr='articulos_filtrados')
    
    if perfil.tipo.nombre == "Admin":  
        solicitudes = Solicitud_Gasto.objects.filter(complete=True,  distrito = perfil.distritos).prefetch_related(articulos_gasto_prefetch).order_by('-created_at') #Temporalmente le metí el filtro de distrito
    elif perfil.tipo.nombre == "Gerente" or perfil.tipo.superintendente == True:
        solicitudes = Solicitud_Gasto.objects.filter(complete=True, distrito = perfil.distritos).prefetch_related(articulos_gasto_prefetch).order_by('-folio')
    else:
        solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff = perfil).prefetch_related(articulos_gasto_prefetch).order_by('-folio')

    

    myfilter = Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

    for solicitud in solicitudes:
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=solicitud)

        proyectos = set()
        subproyectos = set()

        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        solicitud.proyectos = ', '.join(proyectos)
        solicitud.subproyectos = ', '.join(subproyectos)
    #Set up pagination
    p = Paginator(solicitudes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'gasto/solicitudes_gasto.html',context)

@login_required(login_url='user-login')
def detalle_gastos(request, pk):
    productos = Articulo_Gasto.objects.filter(gasto__id=pk)
    facturas = Factura.objects.filter(solicitud_gasto__id = pk)

    context= {
        'productos':productos,
        'facturas':facturas,
        'pk':pk,
        }

    return render(request, 'gasto/detalle_gasto.html', context)

@login_required(login_url='user-login')
def gastos_pendientes_autorizar(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)

    solicitudes = Solicitud_Gasto.objects.filter(complete=True, autorizar = None, superintendente = perfil).order_by('-folio')
    ids_solicitudes_validadas = [solicitud.id for solicitud in solicitudes if solicitud.get_validado]

    solicitudes = Solicitud_Gasto.objects.filter(id__in=ids_solicitudes_validadas)

    myfilter=Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

    for solicitud in solicitudes:
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=solicitud)

        proyectos = set()
        subproyectos = set()

        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        solicitud.proyectos = ', '.join(proyectos)
        solicitud.subproyectos = ', '.join(subproyectos)
    #Set up pagination
    p = Paginator(solicitudes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #Set up pagination
    p = Paginator(solicitudes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'gasto/pendientes_autorizar_gasto.html', context)

@login_required(login_url='user-login')
def gastos_pendientes_autorizar2(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)    

    solicitudes = Solicitud_Gasto.objects.filter(complete=True, autorizar = True, autorizar2 = None, distrito = perfil.distritos).order_by('-folio')

    myfilter=Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

    for solicitud in solicitudes:
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=solicitud)

        proyectos = set()
        subproyectos = set()

        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        solicitud.proyectos = ', '.join(proyectos)
        solicitud.subproyectos = ', '.join(subproyectos)
    #Set up pagination
    p = Paginator(solicitudes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #Set up pagination
    p = Paginator(solicitudes, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'gasto/pendientes_autorizar_gasto2.html', context)

@login_required(login_url='user-login')
def autorizar_gasto(request, pk):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)    

    productos = Articulo_Gasto.objects.filter(gasto__id=pk)
    facturas = Factura.objects.filter(solicitud_gasto__id = pk)

    context= {
        'productos':productos,
        'facturas':facturas,
        'pk':pk,
        }

    gasto = Solicitud_Gasto.objects.get(id = pk)
    productos = Articulo_Gasto.objects.filter(gasto = gasto)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        gasto.autorizar = True
        gasto.approved_at = datetime.now()
        #gasto.approved_at_time = datetime.now().time()
        gasto.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)
        gasto.save()
        messages.success(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has autorizado la solicitud {gasto.id}')
        return redirect ('gastos-pendientes-autorizar')


    context = {
        'gasto': gasto,
        'productos': productos,
    }

    return render(request,'gasto/autorizar_gasto.html', context)


@login_required(login_url='user-login')
def cancelar_gasto(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    gasto = Solicitud_Gasto.objects.get(id = pk)
    productos = Articulo_Gasto.objects.filter(gasto = gasto)

    if request.method =='POST' and 'btn_cancelar' in request.POST:
        gasto.autorizar = False
        gasto.approved_at = datetime.now()
        #gasto.approved_at_time = datetime.now().time()
        gasto.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)
        gasto.save()
        messages.info(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has cancelado la solicitud {gasto.id}')
        return redirect ('gastos-pendientes-autorizar')

    context = {
        'gasto': gasto,
        'productos': productos,
    }

    return render(request,'gasto/cancelar_gasto.html', context)

@login_required(login_url='user-login')
def autorizar_gasto2(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    gasto = Solicitud_Gasto.objects.get(id = pk)
    productos = Articulo_Gasto.objects.filter(gasto = gasto)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        gasto.autorizar2 = True
        gasto.approbado_fecha2 = datetime.now()
        #gasto.approved_at_time2 = datetime.now().time()
        gasto.save()
        messages.success(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has autorizado el gasto {gasto.id}')
        return redirect ('gastos-pendientes-autorizar2')


    context = {
        'gasto': gasto,
        'productos': productos,
    }

    return render(request,'gasto/autorizar_gasto2.html', context)


@login_required(login_url='user-login')
def cancelar_gasto2(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    gasto = Solicitud_Gasto.objects.get(id = pk)
    productos = Articulo_Gasto.objects.filter(gasto = gasto)

    if request.method =='POST' and 'btn_cancelar' in request.POST:
        gasto.autorizar2 = False
        gasto.approbado_fecha2 = datetime.now()
        #gasto.approved_at_time2 = datetime.now().time()
        gasto.save()
        messages.info(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has cancelado la solicitud {gasto.id}')
        return redirect ('gastos-pendientes-autorizar2')

    context = {
        'gasto': gasto,
        'productos': productos,
    }

    return render(request,'gasto/cancelar_gasto2.html', context)




# Create your views here.
@login_required(login_url='user-login')
@perfil_seleccionado_required
def pago_gastos_autorizados(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)

    if usuario.tipo.tesoreria == True:
        gastos = Solicitud_Gasto.objects.filter(autorizar=True, pagada=False, distrito = usuario.distritos, autorizar2=True).order_by('-approbado_fecha2')
        myfilter = Solicitud_Gasto_Filter(request.GET, queryset=gastos)
        gastos = myfilter.qs

        p = Paginator(gastos, 50)
        page = request.GET.get('page')
        gastos_list = p.get_page(page)



        context= {
            'gastos_list':gastos_list,
            'gastos':gastos,
            'myfilter':myfilter,
            }
    else:
        context= {

        }

    return render(request, 'gasto/pago_gastos_autorizados.html',context)

@login_required(login_url='user-login')
def pago_gasto(request, pk):
    pk_usuario = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_usuario)
    gasto = Solicitud_Gasto.objects.get(id=pk)
    
    pagos_alt = Pago.objects.filter(gasto=gasto, hecho=True)
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')

    pago, created = Pago.objects.get_or_create(tesorero = usuario, gasto__distrito = usuario.distritos, hecho=False, gasto=gasto)
    form = Pago_Gasto_Form()
    remanente = gasto.get_total_solicitud - gasto.monto_pagado
    
    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta), 
        } for cuenta in cuentas]

    if request.method == 'POST':
        form = Pago_Gasto_Form(request.POST or None, request.FILES or None, instance = pago)
        if form.is_valid():
            pago = form.save(commit = False)
            #pago.gasto = gasto
            pago.pagado_date = datetime.now()
            #pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            total_pagado = round(gasto.monto_pagado  + pago.monto,2)
            total_sol = round(gasto.get_total_solicitud,2)
            #El bloque a continuación se generó para resolver los problemas de redondeo, se comparan las dos cantidades redondeadas en una variable y se activa una bandera (flag) que indica si son iguales o no!
            if total_sol == total_pagado:
                flag = True
            else:
                flag = False
            if total_pagado > gasto.get_total_solicitud:
                messages.error(request,f'{usuario.staff.staff.first_name}, el monto introducido más los pagos anteriores superan el monto total del viático')
            else:
                if flag:
                    gasto.pagada = True
                    gasto.save()
                pago.save()
                pagos = Pago.objects.filter(gasto=gasto, hecho=True)
                #archivo_oc = attach_oc_pdf(request, gasto.id)
                email = EmailMessage(
                    f'Gasto Autorizado {gasto.id}',
                    f'Estimado(a) {gasto.staff.staff.staff.first_name} {gasto.staff.staff.staff.last_name}:\n\nEstás recibiendo este correo porque ha sido pagado el gasto con folio: {gasto.folio}.\n\n\nGrupo Vordcab S.A de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA 2.0',
                    'savia@vordtec.com',
                    ['ulises_huesc@hotmail.com',gasto.staff.staff.staff.email],
                    )
                #email.attach(f'OC_folio_{gasto.id}.pdf',archivo_oc,'application/pdf')
                email.attach('Pago.pdf',request.FILES['comprobante_pago'].read(),'application/pdf')
                if pagos.count() > 0:
                    for item in pagos:
                        email.attach(f'Gasto{gasto.folio}_P{item.id}.pdf',item.comprobante_pago.read(),'application/pdf')
                email.send()

                messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.staff.first_name}')
                return redirect('pago-gastos-autorizados')

        else:
            form = Pago_Gasto_Form()
            messages.error(request,f'{usuario.staff.staff.first_name}, No se pudo subir tu documento')

    context= {
        'gasto':gasto,
        'pago':pago,
        'cuentas_para_select2':cuentas_para_select2,
        'form':form,
        'pagos_alt':pagos_alt,
        #'cuentas':cuentas,
        'remanente':remanente,
    }

    return render(request,'gasto/pago_gasto.html',context)

@login_required(login_url='user-login')
def matriz_facturas_gasto(request, pk):
    gasto = Solicitud_Gasto.objects.get(id = pk)
    articulos_gasto = Articulo_Gasto.objects.filter(gasto = gasto)
    facturas = Factura.objects.filter(solicitud_gasto = gasto)
    form =  Facturas_Gastos_Form(instance=gasto)
    factura_form = FacturaForm()
    
    if request.method == 'POST':
        form = Facturas_Gastos_Form(request.POST, instance=gasto)
        if "btn_factura_completa" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request,'Haz cambiado el status de facturas completas')
                return redirect('matriz-pagos')
            else:
                messages.error(request,'No está validando')
        if "btn_factura" in request.POST:
            factura_form = FacturaForm(request.POST, request.FILES)
            if factura_form.is_valid():
                factura = factura_form.save(commit=False)
                factura.solicitud_gasto = gasto  # Asume que ya tienes una instancia de Solicitud_Gasto en 'gasto'
                factura.fecha_subida = datetime.now()
                factura.save()
                next_url = request.GET.get('next', 'matriz-pagos')
                messages.success(request, 'Factura agregada correctamente.')
                return redirect(next_url)

    context={
        'form':form,
        'factura_form':factura_form,
        'articulos_gasto':articulos_gasto,
        'gasto':gasto,
        'facturas':facturas,
        }

    return render(request, 'gasto/matriz_factura_gasto.html', context)

def facturas_gasto(request, pk):
    articulo = Articulo_Gasto.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)
    #factura, created = Facturas.objects.get_or_create(pago=pago, hecho=False)
    #form = Articulo_Gasto_Factura_Form(instance= articulo)

    #if request.method == 'POST':
    #    form = Articulo_Gasto_Factura_Form(request.POST or None, request.FILES or None, instance = articulo)
    #    if form.is_valid():
    #        form.save()
    #        messages.success(request,'Las facturas se subieron de manera exitosa')
    #        return redirect('matriz-compras')
    #    else:
    #        form = Articulo_Gasto_Factura_Form()
    #        messages.error(request,'No se pudo subir tu documento')

    context={
        'articulo':articulo,
        #'form':form,
        
        }

    return render(request, 'gasto/facturas_gasto.html', context)

@login_required(login_url='user-login')
def matriz_gasto_entrada(request):
    #articulos_gasto = Articulo_Gasto.objects.filter(gasto = gasto)

    #articulos_gasto = Articulo_Gasto.objects.all()
    articulos_gasto = Articulo_Gasto.objects.filter(Q(producto__nombre = "MATERIALES")|Q(producto__nombre = "HERRAMIENTA"), completo = True, validacion = False, gasto__autorizar = None, gasto__tipo__tipo='REEMBOLSO')

    context={
        'articulos_gasto':articulos_gasto,
        #'form':form,
    }

    return render(request, 'gasto/matriz_entrada_almacen.html', context)

@login_required(login_url='user-login')
def gasto_entrada(request, pk):
    pk_usuario = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_usuario)
    #Tengo que revisar primero si ya existe una orden pendiente del usuario
    articulo_gasto = Articulo_Gasto.objects.get(id=pk)
    facturas = Factura.objects.filter(solicitud_gasto=articulo_gasto.gasto)
    entrada, created = Entrada_Gasto_Ajuste.objects.get_or_create(completo= False, almacenista=usuario, gasto = articulo_gasto)
    
    last_order = Order.objects.filter(staff__distritos = usuario.distritos).order_by('-last_folio_number').first()
    productos = Conceptos_Entradas.objects.filter(entrada=entrada, completo = True)
    articulos = Inventario.objects.filter(producto__gasto = False,  distrito = usuario.distritos)
    form_product = Conceptos_EntradasForm()
    form = Entrada_Gasto_AjusteForm()
    
    productos_para_select2 = [
        {
            'id': item.id,
            'text': str(item.producto.nombre),
            'iva': str(item.producto.iva)
        } for item in articulos
    ]


    if request.method =='POST':
        if "input_agregar" in request.POST:
            form = Entrada_Gasto_AjusteForm(request.POST, instance = entrada)
            if form.is_valid():
                #El elemento entrada es el principal y es el objeto 
                entrada = form.save(commit=False)
                entrada.completo = True
                entrada.completado_fecha = datetime.now()
                entrada.save()
                articulo_gasto.validacion = True
                articulo_gasto.save()
                messages.success(request, f'La entrada del gasto {entrada.id} ha sido creada')
               
                #abrev= usuario.distritos.abreviado <----- el folio ya no lleva
                if last_order == None or last_order.last_folio_number==None:
                    #No hay órdenes para este distrito todavía
                    folio_number = 1
                else:
                    folio_number = last_order.last_folio_number + 1
                last_folio_number = folio_number

                #Se crea una solicitud para poder despachar los artículos
                tipo = Tipo_Orden.objects.get(tipo ='normal')
                folio = folio_number
                orden_producto, created = Order.objects.get_or_create(staff = articulo_gasto.staff, complete = None, distrito = articulo_gasto.staff.distritos)
                orden_producto.folio = folio
                orden_producto.tipo = tipo
                orden_producto.last_folio_number = last_folio_number
                orden_producto.created_at = datetime.now()
                orden_producto.approved_at = datetime.now()
                orden_producto.autorizar = True
                orden_producto.supervisor = articulo_gasto.staff
                orden_producto.superintendente = articulo_gasto.gasto.superintendente
                operacion = Operacion.objects.get(nombre="GASTO")
                orden_producto.operacion = operacion
                orden_producto.complete = True
                #Esta parte es un poco confusa, porque los articulos no siempre están dirigidos al mismo proyecto y subproyecto
                orden_producto.proyecto = articulo_gasto.proyecto
                orden_producto.subproyecto = articulo_gasto.subproyecto
                orden_producto.save()
                #----------------------------------------------------------------#
                #Los productos son cada uno de los items contenidos en la entrada por ajuste y son un objeto "inventario"
                #por cada uno de los productos se va a hacer lo siguiente
                for item_producto in productos:

                    producto_inventario = Inventario.objects.get(producto= item_producto.concepto_material.producto)
                    #productos_por_surtir = ArticulosparaSurtir.objects.filter(articulos__producto=producto_inventario, requisitar = True)
                    articulo_ordenado = ArticulosOrdenados.objects.create(producto=producto_inventario, orden = orden_producto, cantidad=item_producto.cantidad)
                    productos_por_surtir = ArticulosparaSurtir.objects.create(
                        articulos = articulo_ordenado,
                        cantidad=item_producto.cantidad,
                        precio = item_producto.precio_unitario,
                        surtir=True,
                        comentario="esta solicitud es proveniente de un gasto",
                        created_at=date.today(),
                        created_at_time=datetime.now().time(),
                    )
                    #Calculo el precio  y agrega al inventario

                    if producto_inventario.price == 0:
                        producto_inventario.price = item_producto.precio_unitario
                    producto_inventario.price = ((item_producto.precio_unitario * item_producto.cantidad)+ ((producto_inventario.cantidad_apartada + producto_inventario.cantidad) * producto_inventario.price))/(producto_inventario.cantidad + item_producto.cantidad + producto_inventario.cantidad_apartada)
                    #La cantidad en inventario + la cantidad del producto en la entrada <-----esta parte es la que no veo sucediendo
                    producto_inventario.cantidad_apartada = producto_inventario.cantidad_apartada + item_producto.cantidad
                    #producto_inventario.save()
                    producto_inventario._change_reason = f'Esta es una entrada desde un gasto {item_producto.id}'
                    producto_inventario.save()

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
                        <p>Estimado {articulo_gasto.staff.staff.staff.first_name} {articulo_gasto.staff.staff.staff.last_name},</p>
                        <p>Estás recibiendo este correo porque tu gasto folio:{articulo_gasto.gasto} {articulo_gasto.producto.nombre} ha sido validado</p>
                        <p>y ha recibido entrada de almacén por {usuario.staff.staff.first_name} {usuario.staff.staff.last_name}.</p>
                        <p>Favor de pasar a firmar el vale de salida para terminar con este proceso.</p>
                        <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                        <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                    </body>
                </html>
                """
                email = EmailMessage(
                    f'Entrada de producto por gasto: {articulo_gasto.producto.nombre} |Gasto: {articulo_gasto.gasto.id}',
                    body=html_message,
                    from_email = 'savia@vordcab.com',
                    to = ['ulises_huesc@hotmail.com'],#articulo_gasto.staff.staff.email],
                    headers={'Content-Type': 'text/html'}
                    )
                email.content_subtype = "html " # Importante para que se interprete como HTML
                email.send()
                
                return redirect('matriz-gasto-entrada')
        if "input_producto" in request.POST:
            articulo, created = Conceptos_Entradas.objects.get_or_create(completo = False, entrada = entrada)
            form_product = Conceptos_EntradasForm(request.POST, instance=articulo)
            if form_product.is_valid():
                articulo = form_product.save(commit=False)
                articulo.completo = True
                articulo.save()
                messages.success(request, 'Has guardado exitosamente un artículo')
                return redirect('gasto-entrada',pk= pk)

    context= {
        'facturas':facturas,
        'articulo_gasto':articulo_gasto,
        'productos_para_select2':productos_para_select2,
        'productos':productos,
        'form':form,
        'form_product': form_product,
        'articulos':articulos,
        'entrada':entrada,
    }

    return render(request, 'gasto/crear_entrada.html', context)

def delete_articulo_entrada(request, pk):
   
    articulo = Conceptos_Entradas.objects.get(id=pk)
    gasto = articulo.entrada.gasto.id
    messages.success(request,f'El articulo {articulo.concepto_material} ha sido eliminado exitosamente')
    articulo.delete()

    return redirect('gasto-entrada',pk= gasto)

def render_pdf_gasto(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    gasto = Solicitud_Gasto.objects.get(id=pk)
    productos = Articulo_Gasto.objects.filter(gasto=gasto)
    

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
    #c.drawString(160,caja_iso-30,'F-ADQ-N4-01.02')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    #c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    #c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'01/2024')

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
    c.drawCentredString(280,755,'Comprobación de Gastos')
    c.setLineWidth(.3) #Grosor
    c.line(20,caja_proveedor-8,20,575) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(585,caja_proveedor-8,585,575) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

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
    c.drawString(30,caja_proveedor-60,'Clase')
    c.drawString(30,caja_proveedor-80,'Banco:')
    c.drawString(30,caja_proveedor-100,'Fecha:')
    # Segunda columna del encabezado
    c.drawString(280,caja_proveedor-60,'Depositar a:')
    c.drawString(280,caja_proveedor-20,'Cuenta:')
    c.drawString(280,caja_proveedor-40,'Clabe:')


    
    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_proveedor-20,'FOLIO:')
    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_proveedor-20, str(gasto.folio))

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(100,caja_proveedor-20, gasto.staff.staff.staff.first_name+' '+ gasto.staff.staff.staff.last_name)
    c.drawString(100,caja_proveedor-40, gasto.staff.distritos.nombre)
    c.drawString(100,caja_proveedor-60, gasto.tipo.tipo)
    if gasto.staff.staff.banco:
        c.drawString(100,caja_proveedor-80, gasto.staff.staff.banco.nombre)
    else:
        c.drawString(100,caja_proveedor-80, "Sin registro")
    c.drawString(100,caja_proveedor-100, gasto.approved_at.strftime("%d/%m/%Y"))
    # Segunda Columna del encabezado
    if gasto.colaborador:
        c.drawString(350,caja_proveedor-60,gasto.colaborador.staff.staff.first_name+' '+ gasto.colaborador.staff.staff.last_name)
        if gasto.staff.staff.cuenta_bancaria:
            c.drawString(350,caja_proveedor-20,gasto.colaborador.staff.cuenta_bancaria)
        else:
            c.drawString(350,caja_proveedor-20, "Sin registro")
        if gasto.staff.staff.clabe:
            c.drawString(350,caja_proveedor-40,gasto.colaborador.staff.clabe)
        else:
            c.drawString(350,caja_proveedor-40, "Sin registro")
    else:
        c.drawString(350,caja_proveedor-60,gasto.staff.staff.staff.first_name+' '+ gasto.staff.staff.staff.last_name)
        if gasto.staff.staff.cuenta_bancaria:
            c.drawString(350,caja_proveedor-20,gasto.staff.staff.cuenta_bancaria)
        else:
            c.drawString(350,caja_proveedor-20, "Sin registro")
        if gasto.staff.staff.clabe:
            c.drawString(350,caja_proveedor-40,gasto.staff.staff.clabe)
        else:
            c.drawString(350,caja_proveedor-40, "Sin registro")

    #Create blank list
    data =[]

    data.append(['''Código''', '''Nombre''', '''Cantidad''','''Precio''', '''Subtotal''', '''Total''','''Comentario'''])


    high = 540
    for producto in productos:
         # Convert to Decimal and round to two decimal places
        cantidad_redondeada = Decimal(producto.cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        precio_unitario_redondeado = Decimal(producto.precio_unitario).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        subtotal = Decimal(cantidad_redondeada * precio_unitario_redondeado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = Decimal(subtotal) + Decimal(producto.otros_impuestos)
        data.append([
            producto.producto.codigo, 
            producto.producto.nombre,
            cantidad_redondeada, 
            precio_unitario_redondeado,
            subtotal, 
            total,
            producto.comentario,
            ])
        high = high - 18


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

    if gasto.comentario is not None:
        comentario = gasto.comentario
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
    # Personalizar el estilo de los párrafos
    custom_style = ParagraphStyle(
    'CustomStyle',
        parent=styles['BodyText'],
        fontSize=6,  # Reducir el tamaño de la fuente a 6
        leading=8,   # Aumentar el espacio entre líneas para asegurar que el texto no se superponga
        alignment=TA_LEFT,  # Alineación del texto
        # Puedes añadir más ajustes si es necesario
    )
    for i, row in enumerate(data):
        for j, item in enumerate(row):
            if i!=0 and j == 6:
                data[i][j] = Paragraph(item, custom_style)

    table = Table(data, colWidths=[1.2 * cm, 6 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5* cm, 6 * cm,])
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
    # Crear una lista de datos para la tabla secundaria
    data_secundaria = []
    data_secundaria.append(['Proyecto', 'Subproyecto'])  # Encabezados de la tabla secundaria

    # Añadir filas de proyectos y subproyectos
    for producto in productos:
        data_secundaria.append([producto.proyecto.nombre, producto.subproyecto.nombre])

    # Crear la tabla secundaria
    table_secundaria = Table(data_secundaria, colWidths=[7 * cm, 7 * cm])  # Ajusta las medidas según necesites

    # Estilo para la tabla secundaria
    table_secundaria_style = TableStyle([
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (1,0), colors.grey),  # Fondo gris para los encabezados
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),  # Texto blanco para los encabezados
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),  # Texto negro para el cuerpo
        ('FONTSIZE', (0,0), (-1,-1), 8),  # Tamaño de fuente para toda la tabla
        # Añade aquí más estilos si lo necesitas
    ])

    table_secundaria.setStyle(table_secundaria_style)

    # Posición de la tabla secundaria en el PDF
    x_pos = 20  # Ajusta la posición X como sea necesario
    y_pos = high - (len(data) * 18) - 20  # Ajusta la posición Y según el espacio ocupado por la primera tabla y cualquier otro contenido

    # Dibujar la tabla secundaria en el canvas
    table_secundaria.wrapOn(c, width, height)
    table_secundaria.drawOn(c, x_pos, y_pos)

    c.setFillColor(prussian_blue)
    c.rect(20,y_pos-50,565,25, fill=True, stroke=False)
    c.setFillColor(white)
    c.drawCentredString(320,y_pos-45,'Observaciones')
    c.setFillColor(black)
    c.drawCentredString(230,y_pos-190, gasto.staff.staff.staff.first_name +' '+ gasto.staff.staff.staff.last_name)
    c.line(180,y_pos-195,280,y_pos-195)
    c.drawCentredString(230,y_pos-205, 'Solicitado')
   
    c.setFillColor(black)
    c.drawCentredString(410,y_pos-190, gasto.superintendente.staff.staff.first_name +' '+ gasto.superintendente.staff.staff.last_name)
    c.line(360,y_pos-195,460,y_pos-195)
    c.drawCentredString(410,y_pos-205,'Aprobado por')


    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='Comprobación_Gasto_' + str(gasto.folio) +'.pdf')