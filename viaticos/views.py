from django.shortcuts import render, redirect
from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse, FileResponse

from user.models import Profile
from solicitudes.models import Proyecto, Subproyecto, Operacion
from dashboard.models import Inventario, Product
from tesoreria.models import Cuenta, Pago, Facturas
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura, Puntos_Intermedios
from .forms import Solicitud_ViaticoForm, Concepto_ViaticoForm, Pago_Viatico_Form, Viaticos_Factura_Form, Puntos_Intermedios_Form
from tesoreria.forms import Facturas_Viaticos_Form
from .filters import Solicitud_Viatico_Filter
from user.decorators import perfil_seleccionado_required

from decimal import Decimal, ROUND_HALF_UP
import io
import json

from datetime import date, datetime

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
# Create your views here.
# Create your views here.
@login_required(login_url='user-login')
def solicitud_viatico(request):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    usuario = colaborador.get(id = pk_perfil)
    proyectos = Proyecto.objects.filter(activo=True, distrito = usuario.distritos)
    #subproyectos = Subproyecto.objects.all()
    viatico, created = Solicitud_Viatico.objects.get_or_create(complete= False)
    colaboradores = colaborador.filter(distritos = usuario.distritos)
    puntos = Puntos_Intermedios.objects.filter(solicitud = viatico)
    error_messages = {}
    
    if usuario.tipo.superintendente and not usuario.tipo.nombre == "Admin":
       superintendentes = colaborador.filter(staff =  usuario.staff )  
    else:
        superintendentes = colaborador.filter(tipo__superintendente = True, distritos = usuario.distritos, staff__staff__is_active = True).exclude(tipo__nombre="Admin")

    max_folio = Solicitud_Viatico.objects.all().aggregate(Max('folio'))['folio__max']
    folio_probable = max_folio + 1

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

    colaboradores_para_select2 = [
        {
            'id': item.id,
            'text': str(item.staff.staff.first_name) + (' ') + str(item.staff.staff.last_name)
        } for item in colaboradores
    ]

    form = Solicitud_ViaticoForm(instance = viatico)
    form2 = Puntos_Intermedios_Form()

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = Solicitud_ViaticoForm(request.POST, instance=viatico)
            max_folio = Solicitud_Viatico.objects.all().aggregate(Max('folio'))['folio__max']
            nuevo_folio = (max_folio or 0) + 1
            #abrev= usuario.distrito.abreviado
            if form.is_valid():
                viatico = form.save(commit=False)
                viatico.complete = True
                viatico.created_at = date.today()
                viatico.created_at_time = datetime.now().time()
                viatico.staff =  usuario
                viatico.distrito = usuario.distritos
                viatico.folio = nuevo_folio
                viatico.gerente = colaborador.get(tipo__gerente = True, distritos = usuario.distritos, st_activo = True)
                if not viatico.colaborador:
                    viatico.colaborador = usuario
                viatico.save()
                messages.success(request, f'La solicitud {viatico.folio} ha sido creada')
                return redirect('solicitudes-viaticos')
            else:
                for field, errors in form.errors.items():
                    error_messages[field] = errors.as_text()
        if "btn_punto" in request.POST:
            form2 = Puntos_Intermedios_Form(request.POST)
            #abrev= usuario.distrito.abreviado
            if form2.is_valid():
                punto = form2.save(commit=False)
                punto.solicitud = viatico
                punto.save()
                messages.success(request, f'El punto intermedio se ha agregado correctamente')
                return redirect('solicitud-viatico')
            else:
                for field, errors in form2.errors.items():
                    error_messages[field] = errors.as_text()


    context= {
        'proyectos_para_select2':proyectos_para_select2,
        'error_messages': error_messages,
        'superintendentes_para_select2':superintendentes_para_select2,
        'colaboradores_para_select2':colaboradores_para_select2,
        'form':form,
        'form2':form2,
        'puntos':puntos,
        'viatico':viatico,
        'folio_probable': folio_probable,
        #'superintendentes':superintendentes,
        #'proyectos':proyectos,
        #'subproyectos':subproyectos,
    }
    return render(request, 'viaticos/crear_viaticos.html', context)

def eliminar_punto(request):
    data= json.loads(request.body)
    id = data["id"]
    punto = Puntos_Intermedios.objects.get(id=id)
    punto.delete()
    response_data = {
            'action': 'Item was removed',
        }


    return JsonResponse(response_data)

@login_required(login_url='user-login')
def viaticos_pendientes_autorizar(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, autorizar = None, distrito = perfil.distritos).order_by('-folio')

    myfilter=Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    #Set up pagination
    p = Paginator(viaticos, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'viaticos/pendientes_autorizar_viaticos.html', context)

@login_required(login_url='user-login')
def viaticos_pendientes_autorizar2(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')

    viaticos = Solicitud_Viatico.objects.filter(complete=True, autorizar = True, montos_asignados=True, autorizar2 = None).order_by('-folio')

    myfilter=Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    #Set up pagination
    p = Paginator(viaticos, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'viaticos/pendientes_autorizar_viaticos2.html', context)


@login_required(login_url='user-login')
def detalles_viaticos(request, pk):
    viatico = Solicitud_Viatico.objects.get(id=pk)

    context= {
        'viatico': viatico,
        }

    return render(request, 'viaticos/detalles_viaticos.html', context)

@login_required(login_url='user-login')
def detalles_viaticos2(request, pk):
    viatico = Solicitud_Viatico.objects.get(id=pk)
    conceptos = Concepto_Viatico.objects.filter(viatico = viatico, completo = True)

    context= {
        'viatico': viatico,
        'conceptos':conceptos,
        }

    return render(request, 'viaticos/detalles_viaticos_montos.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def autorizar_viaticos(request, pk):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk_perfil)
    viatico = Solicitud_Viatico.objects.get(id = pk)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        viatico.autorizar = True
        viatico.approved_at = date.today()
        viatico.approved_at_time = datetime.now().time()
        viatico.save()
        messages.success(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has autorizado la solicitud {viatico.folio}')
        return redirect ('viaticos-pendientes-autorizar')


    context = {
        'viatico': viatico,
    }

    return render(request,'viaticos/autorizar_viaticos.html', context)

@login_required(login_url='user-login')
def autorizar_viaticos2(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    viatico = Solicitud_Viatico.objects.get(id = pk)
    conceptos = Concepto_Viatico.objects.filter(viatico = viatico, completo = True)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        viatico.autorizar2 = True
        viatico.approved_at2 = date.today()
        viatico.approved_at_time2 = datetime.now().time()
        viatico.save()
        messages.success(request, f'{perfil.staff.staff.first_name} {perfil.staff.staff.last_name} has autorizado la solicitud {viatico.id}')
        return redirect ('viaticos-pendientes-autorizar2')


    context = {
        'viatico': viatico,
        'conceptos': conceptos,
    }

    return render(request,'viaticos/autorizar_viaticos2.html', context)


@login_required(login_url='user-login')
def cancelar_viaticos(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    viatico = Solicitud_Viatico.objects.get(id = pk)


    if request.method =='POST' and 'btn_cancelar' in request.POST:
        viatico.autorizar = False
        viatico.approved_at = date.today()
        viatico.approved_at_time = datetime.now().time()
        viatico.save()
        messages.info(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has cancelado la solicitud {viatico.id}')
        return redirect ('viaticos-pendientes-autorizar')

    context = {
        'viatico': viatico,
    }

    return render(request,'viaticos/cancelar_viaticos.html', context)

@login_required(login_url='user-login')
def cancelar_viaticos2(request, pk):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    perfil = colaborador.get(id = pk_perfil)
    viatico = Solicitud_Viatico.objects.get(id = pk)
    conceptos = Concepto_Viatico.objects.filter(viatico = viatico, completo = True)


    if request.method =='POST' and 'btn_cancelar' in request.POST:
        viatico.autorizar2 = False
        viatico.approbado_fecha2 = date.today()
        viatico.approved_at_time2 = datetime.now().time()
        viatico.save()
        messages.info(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has cancelado la solicitud {viatico.id}')
        return redirect ('viaticos-pendientes-autorizar2')

    context = {
        'viatico': viatico,
        'conceptos': conceptos,
    }


    return render(request,'viaticos/cancelar_viaticos2.html', context)

@login_required(login_url='user-login')
def solicitudes_viaticos(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    perfil = colaborador.get(id = pk_perfil)

    if perfil.tipo.nombre == "Admin" or perfil.tipo.nombre == "Control" or perfil.tipo.nombre == "Gerente" or perfil.tipo.superintendente == True:
        viaticos = Solicitud_Viatico.objects.filter(complete=True, distrito = perfil.distritos).order_by('-folio')
    else:
        viaticos = Solicitud_Viatico.objects.filter(complete=True, staff = perfil).order_by('-folio')

    myfilter=Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    #Set up pagination
    p = Paginator(viaticos, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'viaticos/solicitudes_viaticos.html', context)


@login_required(login_url='user-login')
@perfil_seleccionado_required
def viaticos_autorizados(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    perfil = colaborador.get(id = pk_perfil)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, distrito = perfil.distritos, autorizar = True, montos_asignados = False).order_by('-folio')

    myfilter=Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    #Set up pagination
    p = Paginator(viaticos, 10)
    page = request.GET.get('page')
    ordenes_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'ordenes_list':ordenes_list,
        'myfilter':myfilter,
        }

    return render(request, 'viaticos/viaticos_autorizados.html', context)

def asignar_montos(request, pk):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    usuario = colaborador.get(id = pk_perfil)
    viatico = Solicitud_Viatico.objects.get(id = pk)
    viatico_query= Solicitud_Viatico.objects.filter(id = pk)
    concepto, created = Concepto_Viatico.objects.get_or_create(completo = False, staff=usuario)

    conceptos = Concepto_Viatico.objects.filter(viatico = viatico, completo = True)
    error_messages = {}

    concepto_viatico = Product.objects.filter(viatico = True)

    form = Concepto_ViaticoForm()
    form.fields['producto'].queryset = concepto_viatico

    if request.method =="POST":
        if "btn_producto" in request.POST:
            form = Concepto_ViaticoForm(request.POST, instance=concepto)
            if form.is_valid():
                concepto = form.save(commit=False)
                concepto.viatico = viatico
                concepto.completo = True
                concepto.save()
                messages.success(request,'Se ha agregado un concepto de viático con éxito')
                return redirect('asignar-montos', pk=viatico.id)
            else:
                for field, errors in form.errors.items():
                    error_messages[field] = errors.as_text()
                form.fields['producto'].queryset = concepto_viatico
                form.fields['viatico'].queryset = viatico_query
        if "btn_asignar" in request.POST:
            conceptos = concepto_viatico.count()
            if conceptos > 0:
                viatico.montos_asignados = True
                viatico.save()
                messages.success(request,'Has agregado montos al viático con éxito')
                return redirect('viaticos_autorizados')
            else:
                messages.error(request,'No tienes conceptos agregados')



    context= {
        'error_messages':error_messages,
        'viatico':viatico,
        'conceptos':conceptos,
        'form':form,
    }

    return render(request, 'viaticos/asignar_montos.html', context)

def delete_viatico(request, pk):
    concepto = Concepto_Viatico.objects.get(id=pk)
    messages.success(request,f'El articulo {concepto.producto} ha sido eliminado exitosamente')
    concepto.delete()

    return redirect('asignar-montos', pk=concepto.viatico.id)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def viaticos_autorizados_pago(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    perfil = colaborador.get(id = pk_perfil)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_viatico.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, distrito = perfil.distritos, autorizar = True, autorizar2 = True, pagada=False).order_by('-folio')

    myfilter=Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    #Set up pagination
    p = Paginator(viaticos, 10)
    page = request.GET.get('page')
    viaticos_list = p.get_page(page)

    #if request.method =='POST' and 'btnExcel' in request.POST:

        #return convert_excel_solicitud_matriz(solicitudes)

    context= {
        'viaticos_list':viaticos_list,
        'myfilter':myfilter,
        }

    return render(request, 'viaticos/viaticos_autorizados_pago.html', context)

@login_required(login_url='user-login')
def viaticos_pagos(request, pk):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    usuario = colaborador.get(id = pk_perfil)
    viatico = Solicitud_Viatico.objects.get(id=pk)
    conceptos = Concepto_Viatico.objects.filter(viatico=viatico)
    pagos = Pago.objects.filter(viatico=viatico, hecho=True)
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
    pago, created = Pago.objects.get_or_create(tesorero = usuario, viatico__distrito = usuario.distritos, hecho=False, viatico=viatico)
    form = Pago_Viatico_Form()
    remanente = viatico.get_total - viatico.monto_pagado
#'text': str(super.staff.staff.first_name) + (' ') + str(super.staff.staff.last_name)
    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) + (' ') + str(cuenta.moneda), 
        } for cuenta in cuentas]

    if request.method == 'POST':
        form = Pago_Viatico_Form(request.POST or None, request.FILES or None, instance = pago)

        if form.is_valid():
            pago = form.save(commit = False)
            #pago.viatico = viatico
            pago.pagado_date = date.today()
            pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            total_pagado = round(viatico.monto_pagado  + pago.monto, 2)
            total_sol = round(viatico.get_total,2)
            if total_sol == total_pagado:
                flag = True
            else:
                flag = False
            if total_pagado > viatico.get_total:
                messages.error(request,f'{usuario.staff.staff.first_name}, el monto introducido más los pagos anteriores superan el monto total del viático')
            else:
                if flag:
                    viatico.pagada = True
                    viatico.save()
                pago.save()
                pagos = Pago.objects.filter(viatico=viatico, hecho=True)
                email = EmailMessage(
                    f'Viatico Autorizado {viatico.id}',
                    f'Estimado(a) {viatico.staff.staff}:\n\nEstás recibiendo este correo porque ha sido pagado el viatico con folio: {viatico.id}.\n\n\nGrupo Vordcab S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA 2.0',
                    'savia@vordcab.com',
                    ['ulises_huesc@hotmail.com'],[viatico.staff.staff.staff.email],
                    )
                if pagos.count() > 0:
                    for pago in pagos:
                        email.attach(f'Pago_folio_{pago.id}.pdf',pago.comprobante_pago.path,'application/pdf')
                email.send()
                messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.staff.first_name}')
                return redirect('viaticos-autorizados-pago')
        else:
            form = Pago_Viatico_Form()
            messages.error(request,f'{usuario.staff.staff.first_name}, No se pudo subir tu documento')

    context= {
        'viatico':viatico,
        'pago':pago,
        'form':form,
        'conceptos': conceptos,
        'pagos':pagos,
        'cuentas_para_select2':cuentas_para_select2,
        #'cuentas':cuentas,
        'remanente':remanente,
    }

    return render(request,'viaticos/viaticos_pagos.html',context)



@login_required(login_url='user-login')
def facturas_viaticos(request, pk):
    colaborador = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id')
    usuario = colaborador.get(id = pk_perfil)

    concepto = Concepto_Viatico.objects.get(id = pk)
    viatico = Solicitud_Viatico.objects.get(id = concepto.viatico.id)
    facturas = Viaticos_Factura.objects.filter(solicitud_viatico = viatico, hecho=True)
    factura, created = Viaticos_Factura.objects.get_or_create(solicitud_viatico = viatico, hecho=False)

    form = Viaticos_Factura_Form()

    if request.method == 'POST':
        if "btn_factura" in request.POST:
            form = Viaticos_Factura_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit = False)
                factura.fecha_subido = date.today()
                #factura.hora_subido = datetime.now().time()
                factura.hecho = True
                factura.subido_por = usuario
                factura.save()
                messages.success(request,'Haz registrado tu factura')
                return redirect('facturas-viaticos', pk= concepto.id) #No content to render nothing and send a "signal" to javascript in order to close window
            else:
                messages.error(request,'No está validando')


    context={
        'concepto':concepto,
        'form':form,
        'facturas':facturas,
        'viatico':viatico,
        }

    return render(request, 'viaticos/matriz_facturas.html', context)

@login_required(login_url='user-login')
def matriz_facturas_viaticos(request, pk):
    viatico = Solicitud_Viatico.objects.get(id = pk)
    concepto_viatico = Concepto_Viatico.objects.filter(viatico = viatico)
    form = Facturas_Viaticos_Form(instance=viatico)

    if request.method == 'POST':
        form = Facturas_Viaticos_Form(request.POST, instance=viatico)
        if "btn_factura_completa" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request,'Haz cambiado el status de facturas completas')
                return redirect('matriz-pagos')
            else:
                messages.error(request,'No está validando')

    context={
        'form':form,
        'concepto_viatico': concepto_viatico,
        'viatico': viatico,
        }

    return render(request, 'viaticos/matriz_facturas_viaticos.html', context)

def factura_viatico_edicion(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    factura = Viaticos_Factura.objects.get(id = pk)

    form = Viaticos_Factura_Form(instance= factura)

    if request.method == 'POST':
        if 'btn_edicion' in request.POST:
            form = Viaticos_Factura_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit = False)
                factura.subido_por = usuario
                factura.save()
                form.save()
                messages.success(request,'Las facturas se subieron de manera exitosa')
            else:
                messages.error(request,'No se pudo subir tu documento')


    context={
        'factura':factura,
        'form':form,
        }

    return render(request, 'viaticos/factura_viatico_edicion.html', context)

def render_pdf_viatico(request, pk):
    #Configuration of the PDF object
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    viatico = Solicitud_Viatico.objects.get(id=pk)
    conceptos = Concepto_Viatico.objects.filter(viatico = viatico)
    

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
    #c.drawString(150,caja_iso-20,'Número de documento')
    #c.drawString(160,caja_iso-30,'F-ADQ-N4-01.02')
    #c.drawString(245,caja_iso-20,'Clasificación del documento')
    #c.drawString(275,caja_iso-30,'Controlado')
    #c.drawString(355,caja_iso-20,'Nivel del documento')
    #c.drawString(380,caja_iso-30, 'N5')
    #c.drawString(440,caja_iso-20,'Revisión No.')
    #c.drawString(452,caja_iso-30,'000')
    #c.drawString(510,caja_iso-20,'Fecha de Emisión')
    #c.drawString(525,caja_iso-30,'01/2024')

    caja_proveedor = caja_iso - 50
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Solicitud
    c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    c.rect(20,460,565,2, fill=True, stroke=False) #Linea posterior horizontal 
    c.setFillColor(white)
    c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,755,'Comprobación de Viáticos')
    c.setLineWidth(.3) #Grosor
    c.line(20,caja_proveedor-8,20,460) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    c.line(585,caja_proveedor-8,585,460) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec

    c.setFillColor(white)
    c.setFont('Helvetica-Bold',11)
    #c.drawString(120,caja_proveedor,'Infor')
    c.drawString(300,caja_proveedor, 'Detalles')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    # Primera columna
    c.drawString(30,caja_proveedor-20,'Solicitó:')
    c.drawString(30,caja_proveedor-40,'Distrito:')
    c.drawString(30,caja_proveedor-60,'Proyecto:')
    c.drawString(30,caja_proveedor-80,'Subproyecto:')
    c.drawString(30,caja_proveedor-100,'Lugar de partida:')
    c.drawString(30,caja_proveedor-120,'Lugar de Comisión:')
    c.drawString(30,caja_proveedor-140,'Fecha de partida:')
    c.drawString(30,caja_proveedor-160,'Fecha de retorno:')
    c.drawString(30,caja_proveedor-180,'Comisión:')
    # Segunda columna del encabezado
    c.drawString(320,caja_proveedor-20,'Banco:')
    c.drawString(320,caja_proveedor-40,'Cuenta:')
    c.drawString(320,caja_proveedor-60,'Clabe:')
    c.drawString(320,caja_proveedor-80,'Colaborador:')
    c.drawString(320,caja_proveedor-100,'Nivel:')
    c.drawString(320, caja_proveedor-120,'Transporte')
    c.drawString(320, caja_proveedor-140,'Hospedaje')

    c.drawString(320,caja_proveedor-200,'Fecha de Elaboración:')



    
    c.setFont('Helvetica-Bold',12)
    c.drawString(500,caja_proveedor-20,'FOLIO:')
    c.setFillColor(rojo)
    c.setFont('Helvetica-Bold',12)
    c.drawString(540,caja_proveedor-20, str(viatico.folio))

    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawString(120,caja_proveedor-20, viatico.staff.staff.staff.first_name+' '+ viatico.staff.staff.staff.last_name)
    c.drawString(120,caja_proveedor-40, viatico.staff.distritos.nombre)
    c.drawString(120,caja_proveedor-60, viatico.proyecto.nombre)
    c.drawString(120,caja_proveedor-80, viatico.subproyecto.nombre)
   
    c.drawString(120,caja_proveedor-100, viatico.lugar_partida)
    c.drawString(120,caja_proveedor-120, viatico.lugar_comision)
    c.drawString(120,caja_proveedor-140, viatico.fecha_partida.strftime("%d/%m/%Y"))
    c.drawString(120,caja_proveedor-160, viatico.fecha_retorno.strftime("%d/%m/%Y"))
    if viatico.motivo:
        c.drawString(120,caja_proveedor-180, viatico.motivo)
    # Segunda Columna del encabezado
   
        
   
   

    if viatico.colaborador:
        c.drawString(380, caja_proveedor-80, viatico.colaborador.staff.staff.first_name+' '+viatico.colaborador.staff.staff.last_name)
        c.drawString(380, caja_proveedor-100, str(viatico.colaborador.staff.nivel))
        if viatico.colaborador.staff.banco:
            c.drawString(120,caja_proveedor-20, viatico.colaborador.staff.banco.nombre)
        else:
            c.drawString(380,caja_proveedor-20, "Sin registro")
        if viatico.colaborador.staff.cuenta_bancaria:
            c.drawString(380,caja_proveedor-40,viatico.colaborador.staff.cuenta_bancaria)
        else:
            c.drawString(380,caja_proveedor-40, "Sin registro")
        if viatico.colaborador.staff.clabe:
            c.drawString(380,caja_proveedor-60,viatico.colaborador.staff.clabe)
        else:
            c.drawString(380,caja_proveedor-60, "Sin registro")
    else:
        c.drawString(380, caja_proveedor-80,'Solicitante')
        c.drawString(380, caja_proveedor-100, viatico.staff.staff.staff.first_name+' '+viatico.staff.staff.staff.last_name)
        if viatico.staff.staff.banco:
            c.drawString(120,caja_proveedor-20, viatico.staff.staff.banco.nombre)
        else:
            c.drawString(380,caja_proveedor-20, "Sin registro")
        if viatico.staff.staff.cuenta_bancaria:
            c.drawString(380,caja_proveedor-40,viatico.staff.staff.cuenta_bancaria)
        else:
            c.drawString(380,caja_proveedor-40, "Sin registro")
        if viatico.staff.staff.clabe:
            c.drawString(380,caja_proveedor-60,viatico.staff.staff.clabe)
        else:
            c.drawString(380,caja_proveedor-60, "Sin registro")
   
    
    c.drawString(380, caja_proveedor-120, str(viatico.transporte))
    if viatico.hospedaje:
        c.drawString(380, caja_proveedor-140, "Requerido")
    else:
        c.drawString(380, caja_proveedor-140, "No Requerido")
    c.drawString(430,caja_proveedor-200, viatico.approved_at.strftime("%d/%m/%Y"))


    #Create blank list
    data =[]

    data.append(['''Código''', '''Nombre''', '''Cantidad''','''Precio''', '''Subtotal''', '''Total''','''Comentario'''])


    high = 440
    for concepto in conceptos:
         # Convert to Decimal and round to two decimal places
        cantidad_redondeada = Decimal(concepto.cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        precio_unitario_redondeado = Decimal(concepto.precio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        subtotal = Decimal(cantidad_redondeada * precio_unitario_redondeado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        #total = Decimal(subtotal) + Decimal(concepto.otros_impuestos)
        data.append([
            concepto.producto.codigo, 
            concepto.producto.nombre,
            cantidad_redondeada, 
            precio_unitario_redondeado,
            subtotal, 
            concepto.comentario,
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

    if viatico.comentario_general is not None:
        comentario = viatico.comentario_general
    else:
        comentario = "No hay comentarios"

    
   
    # Crear un marco (frame) en la posición específica
    frame = Frame(50, 0, width, high-50, id='normal')
    options_conditions_paragraph = Paragraph(comentario, styleN)
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

    table = Table(data, colWidths=[1.2 * cm, 6 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5* cm, 7 * cm,])
    table_style = TableStyle([ #estilos de la tabla
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
        ])
    table.setStyle(table_style)

    #pdf size
    table.wrapOn(c, width, height)
    table.drawOn(c, 20, high)
    # Crear una lista de datos para la tabla secundaria
    data_secundaria = []
    data_secundaria.append(['Proyecto', 'Subproyecto'])  # Encabezados de la tabla secundaria

  

    c.setFillColor(prussian_blue)
    c.rect(20,high-50,565,25, fill=True, stroke=False)
    c.setFillColor(white)
    c.drawCentredString(320,high-45,'Comentario General')
    c.setFillColor(black)
    c.drawCentredString(230,high-190, viatico.staff.staff.staff.first_name +' '+ viatico.staff.staff.staff.last_name)
    c.line(180,high-195,280,high-195)
    c.drawCentredString(230,high-205, 'Solicitado')
   
    c.setFillColor(black)
    c.drawCentredString(410,high-190, viatico.superintendente.staff.staff.first_name +' '+ viatico.superintendente.staff.staff.last_name)
    c.line(360,high-195,460,high-195)
    c.drawCentredString(410,high-205,'Aprobado por')
    
    

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='Comprobación_viatico_' + str(viatico.folio) +'.pdf')
