from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from compras.models import ArticuloComprado, Compra
from compras.forms import CompraForm
from compras.filters import CompraFilter
from compras.views import dof, attach_oc_pdf
from dashboard.models import Subproyecto
from .models import Pago, Cuenta, Facturas
from gastos.models import Solicitud_Gasto
from viaticos.models import Solicitud_Viatico
from .forms import PagoForm, Facturas_Form, Facturas_Completas_Form
from .filters import PagoFilter
from user.models import Profile
from django.contrib import messages
from django.db.models import Sum
from datetime import date, datetime
import decimal
from django.core.mail import EmailMessage



# Create your views here.
@login_required(login_url='user-login')
def compras_autorizadas(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    if usuario.tipo.tesoreria == True:
        compras = Compra.objects.filter(autorizado2=True, pagada=False).order_by('-folio')
    else:
        compras = Compra.objects.filter(flete=True,costo_fletes='1')
    compras = Compra.objects.filter(autorizado2=True, pagada=False).order_by('-folio')
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs


    context= {
        'compras':compras,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/compras_autorizadas.html',context)

@login_required(login_url='user-login')
def compras_pagos(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=pk)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    sub = Subproyecto.objects.get(id=compra.req.orden.subproyecto.id)
    pagos_alt = Pago.objects.filter(oc=compra.id, hecho=True)
    #Esta es otra forma de sacar lo que hice con los pagos, me parece mas legible
    #compra_pagos = compra.pago_set.aggregate(Sum('monto'))

    #if pagos['monto__sum'] == None:
        #    monto_anterior = 0
    #else:
        #if compra.moneda.nombre == 'PESOS':
       #     monto_anterior = pagos['monto__sum']
        #cero = Money(0, 'MXN')
       # if compra.moneda.nombre == 'DOLARES':
       #     monto_anterior = pagos['monto__sum']

    suma_pago = 0

    for pago in pagos:
        if pago.oc.moneda.nombre == "DOLARES":
            if pago.cuenta.moneda.nombre == "PESOS":
                monto_pago = pago.monto/pago.tipo_de_cambio
                suma_pago = suma_pago + monto_pago
            else:
                suma_pago = suma_pago + pago.monto
        else:
            suma_pago = suma_pago + pago.monto


    if compra.moneda.nombre == 'PESOS':
        cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
    if compra.moneda.nombre == 'DOLARES':
        cuentas = Cuenta.objects.all()


    pago, created = Pago.objects.get_or_create(tesorero = usuario, distrito = usuario.distrito, oc=compra, hecho=False)
    form = PagoForm(instance=pago)
    remanente = compra.costo_oc - suma_pago





    if request.method == 'POST':
        form = PagoForm(request.POST, request.FILES or None, instance = pago)
        if form.is_valid():
            pago = form.save(commit = False)
            pago.pagado_date = date.today()
            pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            #Traigo la cuenta que se capturo en el form
            cuenta = Cuenta.objects.get(cuenta = pago.cuenta.cuenta)
            #La utilizo para sacar la información de todos los pagos relacionados con esa cuenta y sumarlos

            #cuenta_pagos = Pago.objects.filter(cuenta = pago.cuenta).aggregate(Sum('monto'))
            #if cuenta_pagos['monto__sum'] == None:
            #    cuenta_pagos['monto__sum']=0

            # Actualizo el saldo de la cuenta
            monto_actual = pago.monto #request.POST['monto_0']
            if compra.moneda.nombre == "PESOS":
                sub.gastado = sub.gastado + monto_actual
            #    cuenta.saldo = cuenta_pagos['monto__sum'] + monto_actual
            if compra.moneda.nombre == "DOLARES":
                if pago.cuenta.moneda.nombre == "PESOS": #Si la cuenta es en pesos
                    sub.gastado = sub.gastado + monto_actual * pago.tipo_de_cambio
                    monto_actual = monto_actual/pago.tipo_de_cambio
            #        cuenta.saldo = cuenta_pagos['monto__sum'] + monto_actual * decimal.Decimal(request.POST['tipo_de_cambio'])
                if pago.cuenta.moneda.nombre == "DOLARES":
                    tipo_de_cambio = decimal.Decimal(dof())
                    sub.gastado = sub.gastado + monto_actual * tipo_de_cambio
                    #cuenta.saldo = cuenta_pagos['monto__sum'] + monto_actual
            #actualizar la cuenta de la que se paga
            monto_total= monto_actual + suma_pago
            compra.monto_pagado = monto_total
            costo_oc = compra.costo_oc
            if monto_actual <= 0:
                messages.error(request,f'El pago {monto_actual} debe ser mayor a 0')
            elif round(monto_total,2) <= round(costo_oc,2):
                if round(monto_total,2) == round(costo_oc,2):
                    compra.pagada= True
                    if compra.cond_de_pago.nombre == "CONTADO":
                        pagos = Pago.objects.filter(oc=compra, hecho=True)
                        archivo_oc = attach_oc_pdf(request, compra.id)
                        if compra.referencia:
                            email = EmailMessage(
                                f'Compra Autorizada {compra.get_folio}',
                                f'Estimado(a) {compra.proveedor.contacto} | Proveedor {compra.proveedor.nombre}:\n\nEstás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.get_folio} y referencia: {compra.referencia}.\n\n Atte. {compra.creada_por.staff.first_name} {compra.creada_por.staff.last_name} \nGrupo Vordcab S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                                'savia@vordtec.com',
                                ['ulises_huesc@hotmail.com'],[compra.proveedor.email],
                                )
                        else:
                            email = EmailMessage(
                                f'Compra Autorizada {compra.get_folio}',
                                f'Estimado(a) {compra.proveedor.contacto} | Proveedor {compra.proveedor.nombre}:\n\nEstás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.get_folio}.\n\n Atte. {compra.creada_por.staff.first_name} {compra.creada_por.staff.last_name} \nGrupo Vordcab S.A. de C.V.\n\n Este mensaje ha sido automáticamente generado por SAVIA VORDTEC',
                                'savia@vordtec.com',
                                ['ulises_huesc@hotmail.com'],[compra.proveedor.email],
                                )
                        email.attach(f'OC_folio_{compra.get_folio}.pdf',archivo_oc,'application/pdf')
                        email.attach('Pago.pdf',request.FILES['comprobante_pago'].read(),'application/pdf')
                        if pagos.count() > 0:
                            for pago in pagos:
                                email.attach(f'Pago_folio_{pago.id}.pdf',pago.comprobante_pago.path,'application/pdf')
                        email.send()
                        for producto in productos:
                            if producto.producto.producto.articulos.producto.producto.especialista == True:
                                archivo_oc = attach_oc_pdf(request, compra.id)
                                email = EmailMessage(
                                f'Compra Autorizada {compra.get_folio}',
                                f'Estimado Especialista,\n Estás recibiendo este correo porque ha sido pagada una OC que contiene el producto código:{producto.producto.producto.articulos.producto.producto.codigo} descripción:{producto.producto.producto.articulos.producto.producto.codigo} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA X',
                                'savia@vordtec.com',
                                ['ulises_huesc@hotmail.com'],
                                )
                                email.attach(f'OC_folio:{compra.get_folio}.pdf',archivo_oc,'application/pdf')
                                email.send()
                pago.save()
                compra.save()
                form.save()
                sub.save()
                cuenta.save()

                messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.first_name}')
                return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
            elif monto_total > compra.costo_oc:
                messages.error(request,'El monto total pagado es mayor que el costo de la compra')
            else:
                form = PagoForm()
                messages.error(request,f'{usuario.staff.first_name}, No se pudo subir tu documento')

    context= {
        'compra':compra,
        'pago':pago,
        'form':form,
        'monto':suma_pago,
        'suma_pagos': suma_pago,
        'pagos_alt':pagos_alt,
        'cuentas':cuentas,
        'remanente':remanente,
    }

    return render(request, 'tesoreria/compras_pagos.html',context)

# Create your views here.
@login_required(login_url='user-login')
def matriz_pagos(request):
    pagos = Pago.objects.filter(hecho=True)
    myfilter = PagoFilter(request.GET, queryset=pagos)
    pagos = myfilter.qs

    context= {
        'pagos':pagos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/matriz_pagos.html',context)


@login_required(login_url='user-login')
def matriz_facturas(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id = pk)
    facturas = Facturas.objects.filter(oc = compra, hecho=True)
    factura, created = Facturas.objects.get_or_create(oc=compra, hecho=False)

    form = Facturas_Form()

    if request.method == 'POST':
        if "btn_factura" in request.POST:
            form = Facturas_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit = False)
                factura.fecha_subido = date.today()
                factura.hora_subido = datetime.now().time()
                factura.hecho = True
                factura.subido_por = usuario
                factura.save()
                form.save()
                messages.success(request,'Haz registrado tu factura')
                return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
            else:
                messages.error(request,'No está validando')
        if "btn_editar" in request.POST:
            form

    context={
        'form':form,
        'facturas':facturas,
        'compra':compra,
        }

    return render(request, 'tesoreria/matriz_facturas.html', context)

@login_required(login_url='user-login')
def matriz_facturas_nomodal(request, pk):
    compra = Compra.objects.get(id = pk)
    facturas = Facturas.objects.filter(oc = compra, hecho=True)
    form = Facturas_Completas_Form(instance=compra)

    if request.method == 'POST':
        form = Facturas_Completas_Form(request.POST, instance=compra)
        if "btn_factura_completa" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request,'Haz cambiado el status de facturas completas')
                return redirect('matriz-pagos')
            else:
                messages.error(request,'No está validando')

    context={
        'form':form,
        'facturas':facturas,
        'compra':compra,
        }

    return render(request, 'tesoreria/matriz_factura_no_modal.html', context)

def factura_nueva(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    compra = Compra.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)
    factura, created = Facturas.objects.get_or_create(oc=compra, hecho=False)
    form = Facturas_Form()

    if request.method == 'POST':
        if 'btn_registrar' in request.POST:
            form = Facturas_Form(request.POST or None, request.FILES or None, instance = factura)
            if form.is_valid():
                factura = form.save(commit=False)
                factura.hecho=True
                factura.fecha_subido =date.today()
                factura.hora_subido = datetime.now().time()
                factura.subido_por =  usuario
                form.save()
                factura.save()
                messages.success(request,'Las factura se registró de manera exitosa')
            else:
                messages.error(request,'No se pudo subir tu documento')


    context={
        'form':form,
        }

    return render(request, 'tesoreria/registrar_nueva_factura.html', context)

def factura_compra_edicion(request, pk):
    usuario = Profile.objects.get(staff__id=request.user.id)
    factura = Facturas.objects.get(id = pk)
    #facturas = Facturas.objects.filter(pago = pago, hecho=True)
    #factura, created = Facturas.objects.get_or_create(pago=pago, hecho=False)
    form = Facturas_Form(instance= factura)

    if request.method == 'POST':
        if 'btn_edicion' in request.POST:
            form = Facturas_Form(request.POST or None, request.FILES or None, instance = factura)
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

    return render(request, 'tesoreria/factura_compra_edicion.html', context)

def factura_eliminar(request, pk):
    factura = Facturas.objects.get(id = pk)
    compra = factura.oc
    messages.success(request,f'La factura {factura.id} ha sido eliminado exitosamente')
    factura.delete()

    return redirect('matriz-facturas-nomodal',pk= compra.id)

def mis_gastos(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    gastos = Solicitud_Gasto.objects.filter(complete=True, staff = usuario)
    myfilter = PagoFilter(request.GET, queryset=gastos)
    gastos = myfilter.qs

    context= {
        'gastos':gastos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_gastos.html',context)

def mis_viaticos(request):
    usuario = Profile.objects.get(staff__id=request.user.id)
    viaticos = Solicitud_Viatico.objects.filter(complete=True, staff = usuario)
    myfilter = PagoFilter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    context= {
        'viaticos':viaticos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_viaticos.html',context)
    return render(request, 'tesoreria/mis_viaticos.html',context)