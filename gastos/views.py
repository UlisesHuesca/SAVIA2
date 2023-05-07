from django.shortcuts import render, redirect
from datetime import date, datetime
from django.contrib import messages
from django.core.mail import EmailMessage
from dashboard.models import Inventario
from solicitudes.models import Proyecto, Subproyecto, Operacion
from tesoreria.models import Pago, Cuenta
from .models import Solicitud_Gasto, Articulo_Gasto
from .forms import Solicitud_GastoForm, Articulo_GastoForm, Articulo_Gasto_Edit_Form, Pago_Gasto_Form, Articulo_Gasto_Factura_Form
from compras.views import attach_oc_pdf
from .filters import Solicitud_Gasto_Filter
from user.models import Profile
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Sum
import json
import decimal

# Create your views here.
@login_required(login_url='user-login')
def crear_gasto(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    superintendentes = Profile.objects.filter(tipo__superintendente=True)
    proyectos = Proyecto.objects.filter(activo=True)
    subproyectos = Subproyecto.objects.all()
    colaborador = Profile.objects.all()
    #Tengo que revisar primero si ya existe una orden pendiente del usuario
    gasto, created = Solicitud_Gasto.objects.get_or_create(complete= False)
    articulo, created = Articulo_Gasto.objects.get_or_create(completo = False, staff=usuario)

    productos = Articulo_Gasto.objects.filter(gasto=gasto, completo = True)

    articulos_gasto = Inventario.objects.filter(producto__gasto = True)
    articulos = Inventario.objects.filter(producto__gasto = False)
    form_product = Articulo_GastoForm()
    form = Solicitud_GastoForm()

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = Solicitud_GastoForm(request.POST, instance=gasto)
            #abrev= usuario.distrito.abreviado
            if form.is_valid():
                gasto = form.save(commit=False)
                gasto.complete = True
                gasto.created_at = date.today()
                gasto.created_at_time = datetime.now().time()
                gasto.staff =  usuario
                gasto.save()
                form.save()
                messages.success(request, f'La solicitud {gasto.id} ha sido creada')
                return redirect('solicitudes-gasto')
        if "btn_producto" in request.POST:
            form_product = Articulo_GastoForm(request.POST, request.FILES or None, instance=articulo)
            if form_product.is_valid():
                articulo = form_product.save(commit=False)
                articulo.gasto = gasto
                articulo.completo = True
                articulo.save()
                messages.success(request, 'La solicitud de creacion de articulo funciona')
                return redirect('crear-gasto')


    context= {
        'productos':productos,
        'colaborador':colaborador,
        'form':form,
        'form_product': form_product,
        'articulos':articulos,
        'articulos_gasto':articulos_gasto,
        'gasto':gasto,
        'superintendentes':superintendentes,
        'proyectos':proyectos,
        'subproyectos':subproyectos,
    }
    return render(request, 'gasto/crear_gasto.html', context)

def delete_gasto(request, pk):
    articulo = Articulo_Gasto.objects.get(id=pk)
    messages.success(request,f'El articulo {articulo.producto} ha sido eliminado exitosamente')
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

@login_required(login_url='user-login')
def solicitudes_gasto(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)


    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff = perfil).order_by('-folio')

    myfilter=Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

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

    context= {
        'productos':productos,
        }

    return render(request, 'gasto/detalle_gasto.html', context)

@login_required(login_url='user-login')
def gastos_pendientes_autorizar(request):

    #obtengo el id de usuario, lo paso como argumento a id de profiles para obtener el objeto profile que coindice con ese usuario_id
    perfil = Profile.objects.get(staff__id=request.user.id)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    solicitudes = Solicitud_Gasto.objects.filter(complete=True, autorizar = None, superintendente = perfil).order_by('-folio')

    myfilter=Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

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
    perfil = Profile.objects.get(staff__id=request.user.id)

    #Este es un filtro por perfil supervisor o superintendente, es decir puede ver todo lo del distrito
    #if perfil.tipo.superintendente == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito).order_by('-folio')
    #elif perfil.tipo.supervisor == True:
    #    solicitudes = Solicitud_Gasto.objects.filter(complete=True, staff__distrito=perfil.distrito, supervisor=perfil).order_by('-folio')
    #else:
    solicitudes = Solicitud_Gasto.objects.filter(complete=True, autorizar = True, autorizar2 = None).order_by('-folio')

    myfilter=Solicitud_Gasto_Filter(request.GET, queryset=solicitudes)
    solicitudes = myfilter.qs

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
    perfil = Profile.objects.get(staff__id=request.user.id)
    gasto = Solicitud_Gasto.objects.get(id = pk)
    productos = Articulo_Gasto.objects.filter(gasto = gasto)

    if request.method =='POST' and 'btn_autorizar' in request.POST:
        gasto.autorizar = True
        gasto.approved_at = date.today()
        gasto.approved_at_time = datetime.now().time()
        gasto.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)
        gasto.save()
        messages.success(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has autorizado la solicitud {gasto.id}')
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
        gasto.approved_at = date.today()
        gasto.approved_at_time = datetime.now().time()
        gasto.sol_autorizada_por = Profile.objects.get(staff__id=request.user.id)
        gasto.save()
        messages.info(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has cancelado la solicitud {gasto.id}')
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
        gasto.approbado_fecha2 = date.today()
        gasto.approved_at_time2 = datetime.now().time()
        gasto.save()
        messages.success(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has autorizado el gasto {gasto.id}')
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
        gasto.approbado_fecha2 = date.today()
        gasto.approved_at_time2 = datetime.now().time()
        gasto.save()
        messages.info(request, f'{perfil.staff.first_name} {perfil.staff.last_name} has cancelado la solicitud {gasto.id}')
        return redirect ('gastos-pendientes-autorizar2')

    context = {
        'gasto': gasto,
        'productos': productos,
    }

    return render(request,'gasto/cancelar_gasto2.html', context)




# Create your views here.
@login_required(login_url='user-login')
def pago_gastos_autorizados(request):
    usuario = Profile.objects.get(staff__id=request.user.id)

    if usuario.tipo.tesoreria == True:
        gastos = Solicitud_Gasto.objects.filter(autorizar=True, pagada=False, autorizar2=True).order_by('-folio')


    myfilter = Solicitud_Gasto_Filter(request.GET, queryset=gastos)
    gastos = myfilter.qs


    context= {
        'gastos':gastos,
        'myfilter':myfilter,
        }

    return render(request, 'gasto/pago_gastos_autorizados.html',context)

@login_required(login_url='user-login')
def pago_gasto(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    gasto = Solicitud_Gasto.objects.get(id=pk)
    pagos_alt = Pago.objects.filter(gasto=gasto, hecho=True)
    cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')

    pago, created = Pago.objects.get_or_create(tesorero = usuario, distrito = usuario.distrito, hecho=False, gasto=gasto)
    form = Pago_Gasto_Form()
    remanente = gasto.get_total_solicitud - gasto.monto_pagado


    if request.method == 'POST':
        form = Pago_Gasto_Form(request.POST or None, request.FILES or None, instance = pago)
        if form.is_valid():
            pago = form.save(commit = False)
            #pago.gasto = gasto
            pago.pagado_date = date.today()
            pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            total_pagado = gasto.monto_pagado  + pago.monto
            if total_pagado > gasto.get_total_solicitud:
                messages.error(request,f'{usuario.staff.first_name}, el monto introducido más los pagos anteriores superan el monto total del viático')
            else:
                if round(gasto.monto_pagado,1) == round(gasto.get_total_solicitud,1):
                    gasto.pagada = True
                    gasto.save()
                pago.save()
                pagos = Pago.objects.filter(gasto=gasto, hecho=True)
                #archivo_oc = attach_oc_pdf(request, gasto.id)
                email = EmailMessage(
                    f'Gasto Autorizado {gasto.id}',
                    f'Estimado(a) {gasto.staff.staff}:\n\nEstás recibiendo este correo porque ha sido pagada el gasto con folio: {gasto.id}.\n\n\nVordtec de México S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                    'savia@vordtec.com',
                    ['ulises_huesc@hotmail.com'],[gasto.staff.staff.email],
                    )
                #email.attach(f'OC_folio_{gasto.id}.pdf',archivo_oc,'application/pdf')
                email.attach('Pago.pdf',request.FILES['comprobante_pago'].read(),'application/pdf')
                if pagos.count() > 0:
                    for item in pagos:
                        email.attach(f'Gasto{gasto.id}_P{item.id}.pdf',item.comprobante_pago.read(),'application/pdf')
                email.send()

                messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.first_name}')
                return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
        else:
            form = Pago_Gasto_Form()
            messages.error(request,f'{usuario.staff.first_name}, No se pudo subir tu documento')

    context= {
        'gasto':gasto,
        'pago':pago,
        'form':form,
        'pagos_alt':pagos_alt,
        'cuentas':cuentas,
        'remanente':remanente,
    }

    return render(request,'gasto/pago_gasto.html',context)

@login_required(login_url='user-login')
def matriz_facturas_gasto(request, pk):
    gasto = Solicitud_Gasto.objects.get(id = pk)
    articulos_gasto = Articulo_Gasto.objects.filter(gasto = gasto)

    context={
        'articulos_gasto':articulos_gasto,
        'gasto':gasto,
        }

    return render(request, 'gasto/matriz_factura_gasto.html', context)

def facturas_gasto(request, pk):
    articulo = Articulo_Gasto.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)
    #factura, created = Facturas.objects.get_or_create(pago=pago, hecho=False)
    form = Articulo_Gasto_Factura_Form(instance= articulo)

    if request.method == 'POST':
        form = Articulo_Gasto_Factura_Form(request.POST or None, request.FILES or None, instance = articulo)
        if form.is_valid():
            form.save()
            messages.success(request,'Las facturas se subieron de manera exitosa')
            return redirect('matriz-compras')
        else:
            form = Articulo_Gasto_Factura_Form()
            messages.error(request,'No se pudo subir tu documento')

    context={
        'articulo':articulo,
        'form':form,
        }

    return render(request, 'gasto/facturas_gasto.html', context)


