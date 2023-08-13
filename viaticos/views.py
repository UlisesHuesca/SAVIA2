from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import date, datetime
from django.contrib import messages
from django.core.mail import EmailMessage
from user.models import Profile
from solicitudes.models import Proyecto, Subproyecto, Operacion
from dashboard.models import Inventario
from django.http import HttpResponse
from tesoreria.models import Cuenta, Pago, Facturas
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura
from .forms import Solicitud_ViaticoForm, Concepto_ViaticoForm, Pago_Viatico_Form, Viaticos_Factura_Form
from tesoreria.forms import Facturas_Viaticos_Form
from .filters import Solicitud_Viatico_Filter
from django.core.paginator import Paginator

# Create your views here.
# Create your views here.
@login_required(login_url='user-login')
def solicitud_viatico(request):
    colaborador = Profile.objects.all()
    usuario = colaborador.get(staff__id=request.user.id)
    proyectos = Proyecto.objects.filter(activo=True)
    subproyectos = Subproyecto.objects.all()
    viatico, created = Solicitud_Viatico.objects.get_or_create(complete= False)

    
    if usuario.tipo.superintendente and not usuario.tipo.nombre == "Admin":
        superintendentes = colaborador.filter(staff=request.user)
        viatico.superintendente = usuario
    else:
        superintendentes = colaborador.filter(tipo__superintendente = True, staff__is_active = True).exclude(tipo__nombre="Admin")

    form = Solicitud_ViaticoForm(instance = viatico)

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = Solicitud_ViaticoForm(request.POST, instance=viatico)
            #abrev= usuario.distrito.abreviado
            if form.is_valid():
                viatico = form.save(commit=False)
                viatico.complete = True
                viatico.created_at = date.today()
                viatico.created_at_time = datetime.now().time()
                viatico.staff =  usuario
                if not viatico.colaborador:
                    viatico.colaborador = usuario
                viatico.save()
                form.save()
                messages.success(request, f'La solicitud {viatico.id} ha sido creada')
                return redirect('solicitudes-viaticos')



    context= {
        'form':form,
        'colaborador':colaborador,
        'viatico':viatico,
        'superintendentes':superintendentes,
        'proyectos':proyectos,
        'subproyectos':subproyectos,
    }
    return render(request, 'viaticos/crear_viaticos.html', context)



def viaticos_pendientes_autorizar(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, autorizar = None).order_by('-folio')

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

def viaticos_pendientes_autorizar2(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

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
def autorizar_viaticos(request, pk):
    perfil = Profile.objects.get(staff__id=request.user.id)
    viatico = Solicitud_Viatico.objects.get(id = pk)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        viatico.autorizar = True
        viatico.approved_at = date.today()
        viatico.approved_at_time = datetime.now().time()
        viatico.save()
        messages.success(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has autorizado la solicitud {viatico.id}')
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
        messages.success(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has autorizado la solicitud {viatico.id}')
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
    perfil = Profile.objects.get(staff__id=request.user.id)
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

def solicitudes_viaticos(request):
    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

    if perfil.tipo.nombre == "Admin" or perfil.tipo.nombre == "Control" or perfil.tipo.nombre == "Gerente" or perfil.tipo.nombre == "Superintendente":
        viaticos = Solicitud_Viatico.objects.filter(complete=True).order_by('-folio')
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

def viaticos_autorizados(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, autorizar = True, montos_asignados = False).order_by('-folio')

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
    usuario = Profile.objects.get(staff__id=request.user.id)
    viatico = Solicitud_Viatico.objects.get(id = pk)
    viatico_query= Solicitud_Viatico.objects.filter(id = pk)
    concepto, created = Concepto_Viatico.objects.get_or_create(completo = False, staff=usuario)

    conceptos = Concepto_Viatico.objects.filter(viatico = viatico, completo = True)


    concepto_viatico = Inventario.objects.filter(producto__viatico = True)

    form = Concepto_ViaticoForm()
    form.fields['producto'].queryset = concepto_viatico
    form.fields['viatico'].queryset = viatico_query

    if request.method =="POST":
        if "btn_producto" in request.POST:
            form = Concepto_ViaticoForm(request.POST, instance=concepto)
            if form.is_valid():
                concepto = form.save(commit=False)
                #concepto.viatico = viatico
                concepto.completo = True
                concepto.save()
                messages.success(request,'Se ha agregado un concepto de viático con éxito')
                return redirect('asignar-montos', pk=viatico.id)
            else:
                messages.error(request,'Probablemente te falta llenar algún dato o estás repitiendo conceptos')
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

def viaticos_autorizados_pago(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    viaticos = Solicitud_Viatico.objects.filter(complete=True, autorizar = True, autorizar2 = True, pagada=False).order_by('-folio')

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
    usuario = Profile.objects.get(staff__id=request.user.id)
    viatico = Solicitud_Viatico.objects.get(id=pk)
    conceptos = Concepto_Viatico.objects.filter(viatico=viatico)
    pagos = Pago.objects.filter(viatico=viatico, hecho=True)
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
    pago, created = Pago.objects.get_or_create(tesorero = usuario, distrito = usuario.distrito, hecho=False, viatico=viatico)
    form = Pago_Viatico_Form()
    remanente = viatico.get_total - viatico.monto_pagado

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
                messages.error(request,f'{usuario.staff.first_name}, el monto introducido más los pagos anteriores superan el monto total del viático')
            else:
                if flag:
                    viatico.pagada = True
                    viatico.save()
                pago.save()
                pagos = Pago.objects.filter(viatico=viatico, hecho=True)
                email = EmailMessage(
                    f'Viatico Autorizado {viatico.id}',
                    f'Estimado(a) {viatico.staff.staff}:\n\nEstás recibiendo este correo porque ha sido pagado el viatico con folio: {viatico.id}.\n\n\nVordtec de México S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    'savia@vordtec.com',
                    ['ulises_huesc@hotmail.com'],[viatico.staff.staff.email],
                    )
                if pagos.count() > 0:
                    for pago in pagos:
                        email.attach(f'Pago_folio_{pago.id}.pdf',pago.comprobante_pago.path,'application/pdf')
                email.send()
                messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.first_name}')
                return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
        else:
            form = Pago_Viatico_Form()
            messages.error(request,f'{usuario.staff.first_name}, No se pudo subir tu documento')

    context= {
        'viatico':viatico,
        'pago':pago,
        'form':form,
        'conceptos': conceptos,
        'pagos':pagos,
        'cuentas':cuentas,
        'remanente':remanente,
    }

    return render(request,'viaticos/viaticos_pagos.html',context)

@login_required(login_url='user-login')
def facturas_viaticos(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)

    concepto = Concepto_Viatico.objects.get(id = pk)
    viatico = Solicitud_Viatico.objects.get(id = concepto.viatico.id)
    facturas = Viaticos_Factura.objects.filter(concepto_viatico =concepto, hecho=True)
    factura, created = Viaticos_Factura.objects.get_or_create(concepto_viatico=concepto, hecho=False)

    form = Viaticos_Factura_Form()

    if request.method == 'POST':
        if "btn_factura" in request.POST:
            form = Viaticos_Factura_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit = False)
                factura.fecha_subido = date.today()
                factura.hora_subido = datetime.now().time()
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


