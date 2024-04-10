from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.mail import EmailMessage, BadHeaderError
from smtplib import SMTPException
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import Concat
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from compras.models import ArticuloComprado, Compra
from compras.forms import CompraForm
from compras.filters import CompraFilter
from compras.views import dof, attach_oc_pdf #convert_excel_matriz_compras
from dashboard.models import Subproyecto
from .models import Pago, Cuenta, Facturas, Comprobante_saldo_favor
from gastos.models import Solicitud_Gasto, Articulo_Gasto
from viaticos.models import Solicitud_Viatico
from requisiciones.views import get_image_base64
from .forms import PagoForm, Facturas_Form, Facturas_Completas_Form, Saldo_Form, ComprobanteForm, TxtForm, CompraSaldo_Form
from .filters import PagoFilter, Matriz_Pago_Filter
from viaticos.filters import Solicitud_Viatico_Filter
from gastos.filters import Solicitud_Gasto_Filter
from user.models import Profile
import pytz  # Si estás utilizando pytz para manejar zonas horarias

from datetime import date, datetime
import decimal
import os
import io
#Excel stuff
from openpyxl import Workbook
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
import datetime as dt



from user.decorators import perfil_seleccionado_required



# Create your views here.
@login_required(login_url='user-login')
@perfil_seleccionado_required
def compras_autorizadas(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    if usuario.tipo.tesoreria == True:
        compras = Compra.objects.filter(autorizado2=True, pagada=False, req__orden__distrito = usuario.distritos).order_by('-folio')
   
    
    #compras = Compra.objects.filter(autorizado2=True, pagada=False).order_by('-folio')
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs
    
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)
    
    if request.method == 'POST' and 'btnReporte' in request.POST:
        return convert_excel_matriz_compras_autorizadas(compras)
    

    context= {
        'compras':compras,
        'myfilter':myfilter,
        'compras_list':compras_list,
        }

    return render(request, 'tesoreria/compras_autorizadas.html',context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def compras_pagos(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id=pk)
    productos = ArticuloComprado.objects.filter(oc=pk)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    sub = Subproyecto.objects.get(id=compra.req.orden.subproyecto.id)
    pagos_alt = Pago.objects.filter(oc=compra.id, hecho=True)
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

    cuentas_para_select2 = [
        {'id': cuenta.id,
         'text': str(cuenta.cuenta) +' '+ str(cuenta.moneda), 
         'moneda': str(cuenta.moneda),
        } for cuenta in cuentas]


    pago, created = Pago.objects.get_or_create(tesorero = usuario, oc__req__orden__distrito = usuario.distritos, oc=compra, hecho=False)
    form = PagoForm(instance=pago)

    
    remanente = compra.costo_plus_adicionales - suma_pago
  

    if request.method == 'POST':
        form = PagoForm(request.POST, request.FILES or None, instance = pago)
        if form.is_valid():
            pago = form.save(commit = False)
            pago.pagado_date = date.today()
            pago.pagado_hora = datetime.now().time()
            pago.hecho = True
            #Traigo la cuenta que se capturo en el form
            cuenta = Cuenta.objects.get(cuenta = pago.cuenta.cuenta, moneda = pago.cuenta.moneda)
            #La utilizo para sacar la información de todos los pagos relacionados con esa cuenta y sumarlos

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
            costo_oc = compra.costo_plus_adicionales
            if monto_actual <= 0:
                messages.error(request,f'El pago {monto_actual} debe ser mayor a 0')
            elif round(monto_total,2) <= round(costo_oc,2):
                if round(monto_total,2) == round(costo_oc,2):
                    compra.pagada= True
                    if compra.cond_de_pago.nombre == "CONTADO":
                        pagos = Pago.objects.filter(oc=compra, hecho=True)
                        archivo_oc = attach_oc_pdf(request, compra.id)
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
                                <body>
                                    <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                                    <p>Estimado {compra.req.orden.staff.staff.staff.first_name} {compra.req.orden.staff.staff.staff.last_name},</p>
                                    <p>Estás recibiendo este correo porque tu OC {compra.folio} | RQ: {compra.req.folio} |Sol: {compra.req.orden.folio} ha sido pagada por {pago.tesorero.staff.staff.first_name} {pago.tesorero.staff.staff.last_name},</p>
                                    <p>El siguiente paso del sistema: Recepción por parte de Almacén</p>
                                    <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                                    <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                                </body>
                            </html>
                            """
                        try:
                            email = EmailMessage(
                            f'OC Pagada {compra.folio}|RQ: {compra.req.folio} |Sol: {compra.req.orden.folio}',
                            body=html_message,
                            from_email = settings.DEFAULT_FROM_EMAIL,
                            to= ['ulises_huesc@hotmail.com', compra.req.orden.staff.staff.staff.email],
                            headers={'Content-Type': 'text/html'}
                            )
                            email.content_subtype = "html " # Importante para que se interprete como HTML
                            email.send()
                        except (BadHeaderError, SMTPException) as e:
                            error_message = f'Correo de notificación 1: No enviado'
                        html_message2 = f"""
                            <html>
                                <head>
                                    <meta charset="UTF-8">
                                </head>
                                <body>
                                    <p>Estimado(a) {compra.proveedor.contacto}| Proveedor {compra.proveedor.nombre}:,</p>
                                    <p>Estás recibiendo este correo porque has sido seleccionado para surtirnos la OC adjunta con folio: {compra.folio}.<p>
                                    <p>&nbsp;</p>
                                    <p> Atte. {compra.creada_por.staff.staff.first_name} {compra.creada_por.staff.staff.last_name}</p> 
                                    <p>GRUPO VORDCAB S.A. de C.V.</p>
                                    <p><img src="data:image/jpeg;base64,{logo_v_base64}" alt="Imagen" style="width:100px;height:auto;"/></p>
                                    <p>Este mensaje ha sido automáticamente generado por SAVIA 2.0</p>
                                    <p><img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width:50px;height:auto;border-radius:50%"/></p>
                                </body>
                            </html>
                            """
                        try:
                            email = EmailMessage(
                            f'Compra Autorizada {compra.folio}|SAVIA',
                            body=html_message2,
                            from_email =settings.DEFAULT_FROM_EMAIL,
                            to= ['ulises_huesc@hotmail.com', compra.creada_por.staff.staff.email, compra.proveedor.email],
                            headers={'Content-Type': 'text/html'}
                            )
                            email.content_subtype = "html " # Importante para que se interprete como HTML
                            email.attach(f'OC_folio_{compra.folio}.pdf',archivo_oc,'application/pdf')
                            email.attach('Pago.pdf',request.FILES['comprobante_pago'].read(),'application/pdf')
                            if pagos.count() > 0:
                                for pago in pagos:
                                    email.attach(f'Pago_folio_{pago.id}.pdf',pago.comprobante_pago.path,'application/pdf')
                            email.send()
                            for producto in productos:
                                if producto.producto.producto.articulos.producto.producto.especialista == True:
                                    archivo_oc = attach_oc_pdf(request, compra.id)
                                    email = EmailMessage(
                                    f'Compra Autorizada {compra.folio}',
                                    f'Estimado Especialista,\n Estás recibiendo este correo porque ha sido pagada una OC que contiene el producto código:{producto.producto.producto.articulos.producto.producto.codigo} descripción:{producto.producto.producto.articulos.producto.producto.codigo} el cual requiere la liberación de calidad\n Este mensaje ha sido automáticamente generado por SAVIA X',
                                    settings.DEFAULT_FROM_EMAIL,
                                    ['ulises_huesc@hotmail.com'],
                                    )
                                    email.attach(f'folio:{compra.get_folio}.pdf',archivo_oc,'application/pdf')
                                    email.send()
                            messages.success(request,f'Gracias por registrar tu pago, {usuario.staff.staff.first_name}')
                        except (BadHeaderError, SMTPException) as e:
                            error_message = f'Gracias por registrar tu pago, {usuario.staff.staff.first_name} Atencion: el correo de notificación no ha sido enviado debido a un error: {e}'
                            messages.warning(request, error_message) 
                        
                pago.save()
                compra.save()
                form.save()
                sub.save()
                cuenta.save()
               
                return redirect('compras-autorizadas')#No content to render nothing and send a "signal" to javascript in order to close window
            elif monto_total > compra.costo_oc:
                messages.error(request,f'El monto total pagado es mayor que el costo de la compra {monto_total} > {compra.costo_oc}')
            else:
                form = PagoForm()
                messages.error(request,f'{usuario.staff.staff.first_name}, No se pudo subir tu documento')
        else:
            messages.error(request,f'{usuario.staff.staff.first_name}, No está validando')

    context= {
        'compra':compra,
        'pago':pago,
        'form':form,
        'monto':suma_pago,
        'suma_pagos': suma_pago,
        'pagos_alt':pagos_alt,
        'cuentas_para_select2': cuentas_para_select2,
        'remanente':remanente,
    }

    return render(request, 'tesoreria/compras_pagos.html',context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def edit_pago(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    pago = Pago.objects.get(id=pk)
    print('pago_id',pk)
     
    compra = Compra.objects.get(id = pago.oc.id)
    productos = ArticuloComprado.objects.filter(oc=compra.id)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    sub = Subproyecto.objects.get(id=compra.req.orden.subproyecto.id)
    pagos_alt = Pago.objects.filter(oc=compra.id, hecho=True)
    suma_pago = 0

    for item in pagos:
        if item.oc.moneda.nombre == "DOLARES":
            if item.cuenta.moneda.nombre == "PESOS":
                monto_pago = item.monto/item.tipo_de_cambio
                suma_pago = suma_pago + monto_pago
            else:
                suma_pago = suma_pago + item.monto
        else:
            suma_pago = suma_pago + item.monto


    if compra.moneda.nombre == 'PESOS':
        cuentas = Cuenta.objects.filter(moneda__nombre = 'PESOS')
    if compra.moneda.nombre == 'DOLARES':
        cuentas = Cuenta.objects.all()

    remanente = compra.costo_oc - suma_pago
    # Verificar si es un POST para guardar los cambios
    print(pago)
    if request.method == "POST":
        form = PagoForm(request.POST, request.FILES or None, instance=pago)
        if "btn_actualizar" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request,f'Has actualizado el pago {pago.id} de manera satisfactoria')
                # Redirigir al usuario a donde quieras luego de guardar los cambios
                return redirect('compras-autorizadas')
        if "btn_eliminar" in request.POST:
            print('ya estoy aquí')
            if compra.moneda.nombre == "PESOS":
                sub.gastado = sub.gastado - pago.monto
            if compra.moneda.nombre == "DOLARES":
                if pago.cuenta.moneda.nombre == "PESOS": #Si la cuenta es en pesos
                    sub.gastado = sub.gastado - pago.monto * pago.tipo_de_cambio
                if pago.cuenta.moneda.nombre == "DOLARES":
                    tipo_de_cambio = decimal.Decimal(dof())
                    sub.gastado = sub.gastado - pago.monto * tipo_de_cambio
                messages.success(request,f'Has eliminado el pago {pago.id} de manera satisfactoria')
            pago.delete()
            return redirect('compras-autorizadas')
    else:
        # Si no es un POST, simplemente carga el formulario con el objeto Pago
        form = PagoForm(instance=pago)


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
    return render(request, 'tesoreria/compras_pagos.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def edit_comprobante_pago(request, pk):
    pago = Pago.objects.get(id = pk)
    #print(pago.id)
    form = ComprobanteForm(instance = pago)

    if request.method == 'POST':
        form = ComprobanteForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'pago':pago,
        'form':form, 
    }
    
    return render(request, 'tesoreria/edit_comprobante_pago.html',context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def saldo_a_favor(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id=pk)
    pagos = Pago.objects.filter(oc=compra.id, hecho=True) #.aggregate(Sum('monto'))
    saldo, created = Comprobante_saldo_favor.objects.get_or_create(oc=compra, hecho=False)
    form2 = Saldo_Form(instance = saldo)
    form = CompraSaldo_Form(instance = compra)
    suma_pago = 0
    for item in pagos:
        if item.oc.moneda.nombre == "DOLARES":
            if item.cuenta.moneda.nombre == "PESOS":
                monto_pago = item.monto/item.tipo_de_cambio
                suma_pago = suma_pago + monto_pago
            else:
                suma_pago = suma_pago + item.monto
        else:
            suma_pago = suma_pago + item.monto

    remanente = compra.costo_oc - suma_pago


    if request.method == 'POST':
        form2 = Saldo_Form(request.POST, request.FILES, instance = saldo)
        form = CompraSaldo_Form( request.POST, instance = compra)
        if form.is_valid() and form2.is_valid():
            form.save()
            saldo = form2.save(commit=False)
            saldo.subido_por = usuario
            saldo.fecha_subido = date.today()
            saldo.hora_subido = datetime.now().time()
            saldo.hecho = True
            saldo.save()
            if remanente <= compra.saldo_a_favor:
                compra.pagada = True
            compra.save()
            messages.success(request,f'El saldo se ha registrado correctamente, {usuario.staff.staff.first_name}')
            return HttpResponse(status=204) 

    context= {
        'compra':compra,
        'monto':suma_pago,
        'remanente':remanente,
        'form':form,
        'form2':form2,
    }

    return render(request, 'tesoreria/saldo_a_favor.html',context)

# Create your views here.
@login_required(login_url='user-login')
@perfil_seleccionado_required
def matriz_pagos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    pagos = Pago.objects.filter(
        Q(oc__req__orden__distrito = usuario.distritos) & Q(oc__autorizado2=True) | 
        Q(viatico__distrito= usuario.distritos) & Q(viatico__autorizar2=True) |
        Q(gasto__distrito = usuario.distritos) & Q(gasto__autorizar2 = True), 
        hecho=True
    ).order_by('-pagado_date')
    myfilter = Matriz_Pago_Filter(request.GET, queryset=pagos)
    pagos = myfilter.qs

    #Set up pagination
    p = Paginator(pagos, 50)
    page = request.GET.get('page')
    pagos_list = p.get_page(page)

    if request.method == 'POST' and 'btnReporte' in request.POST:
        return convert_excel_matriz_pagos(pagos)

    context= {
        'pagos_list':pagos_list,
        'pagos':pagos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/matriz_pagos.html',context)


@login_required(login_url='user-login')
@perfil_seleccionado_required
def matriz_facturas(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
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
        #if "btn_editar" in request.POST:
            #form

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
    pagos = Pago.objects.filter(oc = compra)
    form = Facturas_Completas_Form(instance=compra)

    if request.method == 'POST':
        form = Facturas_Completas_Form(request.POST, instance=compra)
        if "btn_factura_completa" in request.POST:
            if form.is_valid():
                form.save()
                next_url = request.GET.get('next', 'matriz-pagos')
                messages.success(request,'Haz cambiado el status de facturas completas')
                return redirect(next_url)
            else:
                messages.error(request,'No está validando')

    context={
        'pagos':pagos,
        'form':form,
        'facturas':facturas,
        'compra':compra,
        }

    return render(request, 'tesoreria/matriz_factura_no_modal.html', context)

def factura_nueva(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
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
                factura.save()
                messages.success(request,'Las factura se registró de manera exitosa')
            else:
                messages.error(request,'No se pudo subir tu documento')


    context={
        'form':form,
        }

    return render(request, 'tesoreria/registrar_nueva_factura.html', context)

def factura_compra_edicion(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
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

@perfil_seleccionado_required
def mis_gastos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    gastos = Solicitud_Gasto.objects.filter(complete=True, staff = usuario).order_by('-folio')
    myfilter = Solicitud_Gasto_Filter(request.GET, queryset=gastos)
    gastos = myfilter.qs

    for gasto in gastos:
        articulos_gasto = Articulo_Gasto.objects.filter(gasto=gasto)

        proyectos = set()
        subproyectos = set()

        for articulo in articulos_gasto:
            if articulo.proyecto:
                proyectos.add(str(articulo.proyecto.nombre))
            if articulo.subproyecto:
                subproyectos.add(str(articulo.subproyecto.nombre))

        gasto.proyectos = ', '.join(proyectos)
        gasto.subproyectos = ', '.join(subproyectos)

    context= {
        'gastos':gastos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_gastos.html',context)

def mis_viaticos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    viaticos = Solicitud_Viatico.objects.filter(complete=True, staff = usuario).order_by('-folio')
    myfilter = Solicitud_Viatico_Filter(request.GET, queryset=viaticos)
    viaticos = myfilter.qs

    context= {
        'viaticos':viaticos,
        'myfilter':myfilter,
        }

    return render(request, 'tesoreria/mis_viaticos.html',context)


def convert_excel_matriz_compras_autorizadas(compras):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Pendientes_de_pago_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Compras Autorizadas')
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
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Folio','Fecha Autorización','Proyecto','Subproyecto','Distrito','Proveedor','C. Pago',
               'Importe', 'Moneda','Tipo de cambio','Total en Pesos','Fecha Creación','Recibida']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5: #Columna del proveedor
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 30
        if col_num == 2:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 20

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de OC's").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos Pendientes").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(J:J)").style = money_resumen_style
  

   
    
    for compra in compras:
        row_num = row_num + 1    
        
        # Manejar autorizado_at_2
        if compra.autorizado_at_2 and isinstance(compra.autorizado_at_2, datetime):
        # Si autorizado_at_2 es timezone-aware, conviértelo a timezone-naive
            autorizado_at_2_naive = compra.autorizado_at_2.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            autorizado_at_2_naive = ''
        
        # Manejar created_at
        if compra.created_at and isinstance(compra.created_at, datetime):
        # Si created_at es timezone-aware, conviértelo a timezone-naive
            created_at_naive = compra.created_at.astimezone(pytz.utc).replace(tzinfo=None)
        else:
            created_at_naive = ''

        recibida = "Recibida" if compra.entrada_completa else "No Recibida"

        row = [
            compra.folio,
            autorizado_at_2_naive,
            compra.req.orden.proyecto.nombre,
            compra.req.orden.subproyecto.nombre,
            compra.req.orden.distrito.nombre,
            compra.proveedor.nombre.razon_social,
            compra.cond_de_pago.nombre,
            compra.costo_plus_adicionales,
            compra.moneda.nombre,
            compra.tipo_de_cambio if compra.tipo_de_cambio else '',
            f'=IF(J{row_num}="",H{row_num},H{row_num}*J{row_num})',  # Calcula total en pesos usando la fórmula de Excel
            created_at_naive,
            recibida,
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 1 or col_num == 11:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 7 or col_num == 9 or col_num == 10:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

def convert_excel_matriz_pagos(pagos):
    response= HttpResponse(content_type = "application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename = Matriz_pagos_' + str(dt.date.today())+'.xlsx'
    wb = Workbook()
    ws = wb.create_sheet(title='Pagos')
    #Comenzar en la fila 1
    row_num = 1

    # Función para manejar los IDs de las compras, gastos o viáticos
    def get_transaction_id(pago):
        if pago.oc:
            return 'OC'+str(pago.oc.folio)
        elif pago.gasto:
            return 'G'+str(pago.gasto.folio)
        elif pago.viatico:
            return 'V'+str(pago.viatico.folio)
        else:
            return None

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
    percent_style = NamedStyle(name='percent_style', number_format='0.00%')
    percent_style.font = Font(name ='Calibri', size = 10)
    wb.add_named_style(percent_style)

    columns = ['Id','Compra/Gasto','Solicitado','Proyecto','Subproyecto','Proveedor/Colaborador','Factuas_Completas',
               'Importe','Fecha', 'Moneda','Tipo de cambio', 'Total en Pesos']

    for col_num in range(len(columns)):
        (ws.cell(row = row_num, column = col_num+1, value=columns[col_num])).style = head_style
        ws.column_dimensions[get_column_letter(col_num + 1)].width = 16
        if col_num == 5:
            ws.column_dimensions[get_column_letter(col_num + 1)].width = 25

    columna_max = len(columns)+2

    # Agregar los mensajes
    ws.cell(column = columna_max, row = 1, value='{Reporte Creado Automáticamente por SAVIA 2.0. UH}').style = messages_style
    ws.cell(column = columna_max, row = 2, value='{Software desarrollado por Vordcab S.A. de C.V.}').style = messages_style
    ws.column_dimensions[get_column_letter(columna_max)].width = 30

    # Agregar los encabezados de las nuevas columnas debajo de los mensajes
    ws.cell(row=3, column = columna_max, value="Total de Pagos").style = head_style
    ws.cell(row=4, column = columna_max, value="Sumatoria de Pagos").style = head_style
   

    # Asumiendo que las filas de datos comienzan en la fila 2 y terminan en row_num
    ws.cell(row=3, column=columna_max + 1, value=f"=COUNTA(A:A)-1").style = body_style
    ws.cell(row=4, column=columna_max + 1, value=f"=SUM(L:L)").style = money_resumen_style
  

   # Aquí debes extraer el conjunto completo de pagos en lugar de solo ciertos valores
    
    for pago in pagos:
        row_num = row_num + 1
        # Define los valores de las columnas basándote en el tipo de pago
        if pago.oc:
            proveedor = pago.oc.proveedor
            facturas_completas = pago.oc.facturas_completas
            cuenta_moneda = pago.cuenta.moneda.nombre if pago.cuenta else None
            if cuenta_moneda == 'PESOS':
                tipo_de_cambio = ''
            elif cuenta_moneda == 'DOLARES':
                 tipo_de_cambio = pago.tipo_de_cambio or pago.oc.tipo_de_cambio or 17
            else:
                tipo_de_cambio = ''  # default si no se cumplen las condiciones anteriores
        elif pago.gasto:
            proveedor = pago.gasto.staff.staff.staff.first_name + ' ' + pago.gasto.staff.staff.staff.last_name
            facturas_completas = pago.gasto.facturas_completas
            tipo_de_cambio = '' # Asume que no se requiere tipo de cambio para gastos
        elif pago.viatico:
            proveedor = pago.viatico.staff.staff.first_name
            facturas_completas = pago.viatico.facturas_completas
            tipo_de_cambio = '' # Asume que no se requiere tipo de cambio para viáticos
        else:
            proveedor = None
            facturas_completas = None
            tipo_de_cambio = ''

       

        row = [
            pago.id,
            get_transaction_id(pago),
            pago.oc.req.orden.staff.staff.staff.first_name + ' ' + pago.oc.req.orden.staff.staff.staff.last_name if pago.oc else '',
            pago.oc.req.orden.proyecto.nombre if pago.oc else '',
            pago.oc.req.orden.subproyecto.nombre if pago.oc else '',
            proveedor,
            facturas_completas,
            pago.monto,
            pago.pagado_date.strftime('%d/%m/%Y') if pago.pagado_date else '',
            pago.oc.moneda.nombre if pago.oc else '',  # Modificación aquí
            tipo_de_cambio,
            f'=IF(K{row_num}="",H{row_num},H{row_num}*K{row_num})'  # Calcula total en pesos usando la fórmula de Excel
        ]

    
        for col_num in range(len(row)):
            (ws.cell(row = row_num, column = col_num+1, value=str(row[col_num]))).style = body_style
            if col_num == 8:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = date_style
            if col_num == 7 or col_num == 10 or col_num == 11:
                (ws.cell(row = row_num, column = col_num+1, value=row[col_num])).style = money_style
       
    
    sheet = wb['Sheet']
    wb.remove(sheet)
    wb.save(response)

    return(response)

def mass_payment_view(request):
    if request.method == 'POST':
        request.session['compras_ids'] = request.POST.getlist('compra_id')
        return redirect('layout_pagos')  # No pasamos 'ids' porque usaremos la sesión

# Si necesitas pasar las IDs como parte del contexto a un nuevo template puedes hacerlo así:
def layout_pagos(request):
    compras_ids = request.session.get('compras_ids', [])
    #print(compras_ids)
    # Se asegura de que los IDs sean enteros
      
    
    # Se asegura de que los IDs sean enteros
    compras_ids = [int(id) for id in compras_ids if str(id).isdigit()]
    #print(compras_ids)
    compras = Compra.objects.filter(id__in=compras_ids)
    cuentas_disponibles = Cuenta.objects.filter()

    if request.method == 'POST':
        # Asumimos que este POST es para generar el archivo TXT
        # Puedes validar el formulario aquí si es necesario
        
        
            # Construyes el contenido del archivo TXT con la información de compras y el formulario
        if request.method == 'POST':
            lineas = []

            for count, compra in enumerate(compras, start=1):
                # Obtiene el ID de la cuenta de pago de la fila actual
                cuenta_pago_id = request.POST.get(f'cuenta_{count}')
                # Obtiene el monto de la fila actual, asegurándose de incluir el índice
                monto_str = request.POST.get(f'monto_{count}', '0')

                if monto_str is None or monto_str.strip() == '':
                    # Maneja el caso de un monto vacío o ausente
                    monto_formateado = "Valor requerido"
                else:
                    # Convierte el monto a float y lo formatea
                    monto = float(monto_str)
                    monto_formateado = "{:015.2f}".format(monto)

                # Aquí, obtienes la cuenta de pago usando el ID y la formateas
                cuenta_pago = cuentas_disponibles.get(id=cuenta_pago_id)
                str_cuenta = str(cuenta_pago.cuenta).zfill(18)

                divisa = 'USD' if compra.moneda.nombre == 'DOLARES' else 'MXP'

                # Construye cada línea del archivo TXT
                banco = 'PTC' if compra.proveedor.banco.nombre == "BBVA" else 'PSC'
                cuenta = str(compra.proveedor.cuenta).zfill(18)
                motivo_pago = '-' + str(compra.folio) + '-'
                titular = compra.proveedor.nombre.razon_social
                linea = f"{banco}{cuenta}{str_cuenta}{divisa}{monto_formateado}{motivo_pago}{titular}\n"
                lineas.append(linea)
            
            # Genera la respuesta HTTP con el contenido del archivo TXT
            response = HttpResponse(lineas, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="pagos.txt"'
            return response
        else:
            # Si el formulario no es válido, puedes manejar los errores aquí
            pass

    context = {
        'compras': compras,
        'cuentas_disponibles': cuentas_disponibles,
    }

    return render(request, 'tesoreria/layout_pagos.html', context)

