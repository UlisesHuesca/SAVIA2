from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, JsonResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Avg, Value, ExpressionWrapper, fields, Sum, Q, DateField, Count, Case, When, Value, DecimalField
from django.db.models.functions import Concat, Coalesce
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils.timezone import now
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.utils.crypto import get_random_string
from django import forms  # por si no lo tienes ya importado
from compras.models import Compra, Proveedor, Proveedor_direcciones, Evidencia, DocumentosProveedor, InvitacionProveedor, Estatus_proveedor, Debida_Diligencia, Miembro_Alta_Direccion, Funcionario_Publico_Relacionado, Relacion_Servidor_Publico, Responsable_Interaccion
from user.models import Profile, CustomUser, Tipo_perfil, Distrito, Almacen
from compras.filters import CompraFilter
from requisiciones.models import Requis
from requisiciones.views import get_image_base64
from user.decorators import perfil_seleccionado_required
from datetime import date, datetime, timedelta
#from .forms import SubirDocumentoForm, UploadFileForm, RegistroProveedorForm
from .forms import (
    SubirDocumentoForm,
    UploadFileForm,
    RegistroProveedorForm,
    DebidaDiligenciaForm,
    AccionistaForm,
    MiembroAltaDireccionForm,
    FuncionarioPublicoRelacionadoForm,
    RelacionServidorPublicoForm,
    ResponsableInteraccionForm
)
from dashboard.forms import ProveedoresDireccionesForm, ProveedoresExistDireccionesForm
from io import BytesIO

from tesoreria.models import Pago, Facturas
import datetime as dt
import decimal
import os
import fitz  # PyMuPDF
import unicodedata

# Import Excel Stuff
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
import json
from django.core.mail import EmailMessage
# Create your views here.



#################### VISTAS PARA PROVEEDORES EXTERNOS ####################

############ LAS VISTAS PARA PROVEEDORES EXERNOS DEBENDE SER DECLARADAS ESPECIFICAMENTE EN EL USER.DECORATORS.PY ##############
############ DENTRO DE @PERFIL_SELECCIONADO_REQUIRED SI NO SE HACE DE ESA MANERA NO SE PUEDE VER ##############

@perfil_seleccionado_required
def matriz_oc_proveedores(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    almacenes_distritos = set(usuario.almacen.values_list('distrito__id', flat=True))
    proveedor = usuario.proveedor if hasattr(usuario, 'proveedor') else None
    #try:
    #    proveedor = Proveedor.objects.get(perfil_proveedor = usuario)
    #except Proveedor.DoesNotExist:
    #    proveedor = None
    #print(proveedor)
    if usuario.tipo.proveedor_externo and proveedor is not None:
        compras = Compra.objects.filter(
            Q(autorizado2 = True, cond_de_pago__nombre = "CREDITO")| Q(pagada = True, cond_de_pago__nombre = "CONTADO"),
            complete = True, 
            proveedor__nombre = proveedor,
            req__orden__distrito__id__in = almacenes_distritos, 
            created_at__gte=dt.datetime(2024, 1, 1),
            ).annotate(
            total_facturas=Count('facturas', filter=Q(facturas__hecho=True)),
            autorizadas=Count(Case(When(Q(facturas__autorizada=True, facturas__hecho=True), then=Value(1))))
            ).order_by('-created_at')
    else:
        compras = Compra.objects.none()
    
    compras_no_pagadas = compras.filter(pagada=False, entrada_completa = True)
    #suma_compras_no_pagadas = compras_no_pagadas.aggregate(total=Sum('costo_oc'))['total'] or 0
    suma_compras_no_pagadas = sum(c.costo_plus_adicionales for c in compras_no_pagadas)
    print(suma_compras_no_pagadas)
    myfilter = CompraFilter(request.GET, queryset=compras)
    compras = myfilter.qs
    print(compras)


    compras_data = list(compras.values())
    # Obtienes las fechas de inicio y finalización del filtro
    start_date = myfilter.form.cleaned_data.get('start_date')
    end_date = myfilter.form.cleaned_data.get('end_date')
   
    num_approved_requis = 0
    num_requis_atendidas = 0
    # Asegúrate de que start_date y end_date son objetos datetime "aware"
    if start_date is not None and end_date is not None:
    # Si las fechas no tienen información de la zona horaria, hazlas "aware"
        # Filtrar las requisiciones aprobadas dentro del rango de fechas
       
        approved_requis = Requis.objects.filter(approved_at__gte=start_date, approved_at__lte=end_date, autorizar = True, orden__distrito = usuario.distritos)
        approved_requis_ids = approved_requis.values_list('id', flat=True)
        num_approved_requis = approved_requis.count() 

        # Contar el número de requisiciones aprobadas
        compras_colocadas_ids = Compra.objects.filter(
            created_at__gte=start_date, 
            created_at__lte=end_date, 
            req__colocada=True,
            req_id__in=approved_requis_ids,
            req__orden__distrito = usuario.distritos
        ).values_list('req', flat=True).distinct()

        num_requis_atendidas = len(set(compras_colocadas_ids))


    # Calcular el total de órdenes de compra
    total_de_oc = compras.count()
     # Calcular el número de OC que cumplen el criterio (created_at - approved_at <= 3)
    time_difference = ExpressionWrapper(F('created_at') - F('req__approved_at'), output_field=fields.DurationField())
    compras_con_criterio = compras.annotate(time_difference=time_difference).filter(time_difference__lte=timedelta(days=3))
    oc_cumplen = compras_con_criterio.count()


     #Set up pagination
    p = Paginator(compras, 50)
    page = request.GET.get('page')
    compras_list = p.get_page(page)

    # Proceso para asignar estados y calcular la suma total de facturas
    for compra in compras_list:
        if compra.total_facturas == 0:
            compra.estado_facturas = 'sin_facturas'
        elif compra.autorizadas == compra.total_facturas:
            compra.estado_facturas = 'todas_autorizadas'
        else:
            compra.estado_facturas = 'pendientes'
        
        # Sumar totales de facturas relacionadas que cumplan con las condiciones
        compra.suma_total_facturas = sum(
            decimal.Decimal(factura.emisor['total'])
            for factura in compra.facturas.all()
            if factura.factura_xml and factura.hecho and factura.autorizada and factura.emisor is not None
        )
        
    context= {
        'usuario':usuario,
        'proveedor': proveedor,
        'compras_list':compras_list,
        'compras':compras,
        'myfilter':myfilter,
        'suma_compras_no_pagadas': suma_compras_no_pagadas,
        #'cumplimiento': cumplimiento,
        }
    
    
    #task_id = request.session.get('task_id')

    if request.method == 'POST' and 'btnExcel' in request.POST:
        return convert_excel_matriz_compras(compras, num_requis_atendidas, num_approved_requis, start_date, end_date)
        

    return render(request, 'proveedores_externos/matriz_oc_proveedores.html',context)


@perfil_seleccionado_required
def matriz_direcciones(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    almacenes_distritos = set(usuario.almacen.values_list('distrito__id', flat=True))
   
    
    if usuario.tipo.proveedor_externo:
        proveedor = Proveedor.objects.get(id = usuario.proveedor.id)
        #direcciones = Proveedor_direcciones.objects.filter(nombre= proveedor, completo = True).exclude(estatus__nombre="Rechazado")
        estatus_proveedor = ["NUEVO","APROBADO"]
        direcciones = Proveedor_direcciones.objects.filter(nombre=proveedor, completo = True, distrito__status = True, estatus__nombre__in = estatus_proveedor,  distrito__id__in = almacenes_distritos)
        tiene_servicio = proveedor.direcciones.filter(servicio=True).exists()
        tiene_arrendamiento = proveedor.direcciones.filter(arrendamiento=True).exists()

        # Obtener todos los documentos del proveedor
        documentos = DocumentosProveedor.objects.filter(proveedor=proveedor)
        
        tipos_documentos = [
            'csf',
            'comprobante_domicilio',
            'opinion_cumplimiento',
            'credencial_acta_constitutiva',
            'curriculum',
            'competencias',
            'contrato',
            'factura_predial',
            'otros',
            'carta_credito',
            'visita',
            'calificacion',
            'cotizacion',
            'repse',
            'cumplimiento_imss',
            'busqueda_mediatica',
            'calidad'
        ]

        documentos_count = {tipo: 0 for tipo in tipos_documentos}
        documentos_validados_count = {tipo: 0 for tipo in tipos_documentos}

        for documento in documentos:
            if documento.obsoleto:
                continue  # Ignorar documento marcado como obsoleto

            tipo = documento.tipo_documento
            documentos_count[tipo] += 1

            if documento.validada:
                documentos_validados_count[tipo] += 1

        print(documentos_count)
      
    else:
        raise Http404("No tienes permiso para ver esta vista")
    
    context = {
        'documentos_count': documentos_count,  # Dict con el total de documentos por tipo
        'documentos_validados_count': documentos_validados_count,  # Dict con validados por tipo
        'documentos': documentos,
        'proveedor':proveedor,
        'direcciones':direcciones,
        'tiene_servicio': tiene_servicio,
        'tiene_arrendamiento': tiene_arrendamiento,
        
        }
    return render(request,'proveedores_externos/informacion_proveedores.html', context)

@perfil_seleccionado_required
def edit_csf(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'csf'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento de Constancia de Situación Fiscal subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_acta_credencial(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'credencial_acta_constitutiva'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Credencial/Acta constitutiva subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_comprobante_domicilio(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'comprobante_domicilio'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Comprobante de domicilio subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_opinion_cumplimiento(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'opinion_cumplimiento'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento de Opinión de Cumplimiento subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_carta_credito(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'carta_credito'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Carta de Crédito subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)


@perfil_seleccionado_required
def edit_calificacion(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'calificacion'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento calificación subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_visita(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'visita'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento visita subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_calidad(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'calidad'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento de calidad subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_cotizacion(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'cotizacion'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Cotización subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)


@perfil_seleccionado_required
def edit_busqueda_mediatica(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'busqueda_mediatica'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Búsqueda mediática subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)


@perfil_seleccionado_required
def edit_repse(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'repse'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Búsqueda mediática subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_cumplimiento_imss(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'cumplimiento_imss'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Opinión de cumplimiento subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_otros(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'otros'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def edit_curriculum(request, pk):
    proveedor = get_object_or_404(Proveedor, id=pk)
    tipo_documento = 'curriculum'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Curriculum Vitae subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }
   
   
    return render(request, 'proveedores_externos/edit_documentos.html',context)

def subir_documento_competencia(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    tipo_documento = 'competencias'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento de Competencia subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }

    return render(request, 'proveedores_externos/edit_documentos.html',context)

def subir_documento_contrato(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    tipo_documento = 'contrato'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Documento de Contrato subido exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }

    return render(request, 'proveedores_externos/edit_documentos.html',context)

def subir_documento_factura_predial(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    tipo_documento = 'factura_predial'
   

    if request.method == 'POST':
        form = SubirDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)  # 🔥 Guardar sin hacer commit
            documento.proveedor = proveedor
            documento.tipo_documento = tipo_documento  # 🔥 Se asigna el tipo de documento
            documento.save()  # 🔥 Ahora se guarda el documento con los datos completos
            messages.success(request, 'Factura de Bien o Predial subida exitosamente')
            return HttpResponse(status=204)  # 
    else:
        form = SubirDocumentoForm()  

    context = {
        'proveedor':proveedor,
        'tipo_documento':tipo_documento,
        'form':form, 
    }

    return render(request, 'proveedores_externos/edit_documentos.html',context)

@perfil_seleccionado_required
def evidencias_proveedor(request, pk):
    pk_usuario = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_usuario)
    compra = Compra.objects.get(id = pk)
    evidencias = Evidencia.objects.filter(oc = compra, hecho=True)
    
    
    next_url = request.GET.get('next',)

    context={
        'next_url':next_url,
        #'form':form,
        'compra':compra,
        'evidencias':evidencias,
        'usuario':usuario,
        }

    return render(request, 'proveedores_externos/evidencias_proveedor.html', context)


@perfil_seleccionado_required
def subir_evidencias(request, pk):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    compra = Compra.objects.get(id = pk)
    form = UploadFileForm()

    if request.method == 'POST':
        if 'btn_registrar' in request.POST:
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                
                files_evidencia = request.FILES.getlist('evidencia_file')
                print(request.FILES)
                if not files_evidencia:
                    messages.error(request, 'Debes subir al menos un archivo.')
                    return HttpResponse(status=204)
                for archivo_evidencia in files_evidencia:
                    evidencia = Evidencia.objects.create(
                        oc=compra,
                        file = archivo_evidencia,
                        hecho = True,
                        uploaded = datetime.now(),
                        subido_por = usuario
                    )
                    evidencia.save()
                messages.success(request, 'Las evidencias se registraron de manera exitosa')

            else:
                messages.error(request,'No se pudo subir tu documento')


    context={
        'form': form, 
        'compra': compra,
    }

    return render(request, 'proveedores_externos/subir_evidencias.html', context)


@perfil_seleccionado_required
@csrf_exempt  # Permite evitar problemas con CSRF si se maneja en el frontend
def eliminar_evidencia(request, pk):
    if request.method != 'POST':  
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    
    pk_perfil = request.session.get('selected_profile_id')
    perfil = get_object_or_404(Profile, id=pk_perfil)
    evidencia = get_object_or_404(Evidencia, id=pk)
    compra = evidencia.oc
    
    try:
        data = json.loads(request.body)
        comentario = data.get('comentario', '')
        print("Comentario recibido", comentario)
        # Enviar correo
        email = EmailMessage(
            f'Evidencia eliminada',
            body=f'Se ha eliminado de la compra {compra.folio} la evidencia con ID {evidencia.id}. Comentario: {comentario}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[
                compra.creada_por.staff.staff.email,
                'ulises_huesc@hotmail.com'    
            ]
        )
        email.content_subtype = "html"
        email.send()
        
        # Eliminar la factura
        evidencia.delete()

        return JsonResponse({'success': True, 'evidencia_id': pk})
    
    except Exception as e:
        return JsonResponse({'error': f'Error eliminando la evidencia: {str(e)}'}, status=500)
    
def update_comentario(request):
    data = json.loads(request.body)
    pk = data["evidencia_id"]
    dato = data["dato"]
    tipo = data["tipo"]
    evidencia = Evidencia.objects.get(id=pk)
    print(evidencia.comentario)
    if tipo == "comentario": 
        evidencia.comentario = dato
    if tipo == "cantidad":
        evidencia.cantidad = dato
    evidencia.save()
    # Construye un objeto de respuesta que incluya el dato y el tipo.
    response_data = {
        'dato': dato,
        'tipo': tipo
    }

    return JsonResponse(response_data, safe=False)

def convert_excel_matriz_compras(compras, num_requis_atendidas, num_approved_requis, start_date, end_date):
    print('conteo compras:', compras.count())
    # Crea un objeto BytesIO para guardar el archivo Excel
    output = BytesIO()

    # Crea un libro de trabajo y añade una hoja
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Matriz_Compras")

     
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    # Define los estilos
    head_style = workbook.add_format({'bold': True, 'font_color': 'FFFFFF', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})
    percent_style = workbook.add_format({'num_format': '0.00%', 'font_name': 'Calibri', 'font_size': 10})
    messages_style = workbook.add_format({'font_name':'Arial Narrow', 'font_size':11})

    columns = ['Compra', 'Distrito', 'Solicitante','Comprador', 'Creado', 'Req. Autorizada', 'Proveedor',
               'Status Proveedor','Crédito/Contado', 'Costo', 'Monto Pagado', 'Status Pago','Fecha Pago', 'Status Autorización','Tipo Item', 'Días de entrega', 'Moneda',
               'Tipo de cambio', 'Entregada','Tiene Facturas', "Total en pesos"]

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA Vordcab. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Grupo Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    
    # Escribir encabezados debajo de los mensajes
    #worksheet.write(2, columna_max - 1, "Fecha Inicial", head_style)
    #worksheet.write(3, columna_max - 1, "Fecha Final", head_style)
    #worksheet.write(4, columna_max - 1, "Total de OC's", head_style)
    #worksheet.write(5, columna_max - 1, "Requisiciones Aprobadas", head_style)
    #worksheet.write(6, columna_max - 1, "Requisiciones Atendidas", head_style)
    #worksheet.write(7, columna_max - 1, "KPI Colocadas/Aprobadas", head_style)
    #worksheet.write(8, columna_max - 1, "OC Entregadas/Pagadas/Productos", head_style)
    #worksheet.write(9, columna_max - 1, "OC Pagadas/Productos", head_style)
    #worksheet.write(10, columna_max - 1, "KPI OC Entregadas/Total de OC", head_style)
    #if num_approved_requis <= 0:
    #     num_approved_requis=1
    #indicador = num_requis_atendidas/num_approved_requis
    #letra_columna = xl_col_to_name(columna_max)
    #formula = f"={letra_columna}9/{letra_columna}10"
    # Escribir datos y fórmulas
    #worksheet.write(2, columna_max, start_date, date_style)  # Ejemplo de escritura de fecha
    #worksheet.write(3, columna_max, end_date, date_style)
    #worksheet.write_formula(4, columna_max, '=COUNTA(A:A)-1', body_style)  # Ejemplo de fórmula
    #worksheet.write(5, columna_max, num_approved_requis, body_style)
    #worksheet.write(6, columna_max, num_requis_atendidas, body_style)
    #worksheet.write(7, columna_max, indicador, percent_style)  # Ajuste del índice de fila y columna para xlsxwriter
    #worksheet.write_formula(8, columna_max, '=COUNTIFS(P:P, "Pagada", W:W, "Entregada", S:S, "PRODUCTOS")', body_style)
    # Escribir otra fórmula COUNTIF, también con el estilo corporal
    #worksheet.write_formula(9, columna_max, '=COUNTIFS(P:P, "Pagada", S:S, "PRODUCTOS")', body_style)
    #worksheet.write_formula(10, columna_max, formula, percent_style)

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    worksheet.set_column('L:L', 12,  money_style)
    worksheet.set_column('M:M', 12, money_style) 
    # Asumiendo que ya tienes tus datos de compras
    row_num = 0
    for compra_list in compras:
        row_num += 1
        # Aquí asumimos que ya hiciste el procesamiento necesario de cada compra
        pagos = Pago.objects.filter(oc=compra_list, hecho = True).annotate(
            fecha_orden=Coalesce('pagado_real', 'pagado_date', output_field=DateField())
        ).order_by('pagado_date')

        if pagos.exists():
            primer_pago = pagos.first()
            primera_fecha_pago = primer_pago.pagado_real if primer_pago.pagado_real else primer_pago.pagado_date
            primera_fecha_pago = primera_fecha_pago.strftime('%Y-%m-%d')
        else:
            primera_fecha_pago = " "


        tipo_de_cambio_promedio_pagos = pagos.aggregate(Avg('tipo_de_cambio'))['tipo_de_cambio__avg']
        articulos = compra_list.articulocomprado_set.all()
         # Determinar el tipo de producto para la columna de tipo_producto
        todos_servicios = all(articulo.producto.producto.articulos.producto.producto.servicio for articulo in articulos)
        ningun_servicio = all(not articulo.producto.producto.articulos.producto.producto.servicio for articulo in articulos)

        if todos_servicios:
            tipo_producto = "SERVICIOS"
        elif ningun_servicio:
            tipo_producto = "PRODUCTOS"
        else:
            tipo_producto = "PRODUCTO/SERVICIOS"
    

        # Usar el tipo de cambio de los pagos, si existe. De lo contrario, usar el tipo de cambio de la compra
        tipo = tipo_de_cambio_promedio_pagos or compra_list.tipo_de_cambio
        tipo_de_cambio = '' if tipo == 0 else tipo
        created_at = compra_list.created_at.replace(tzinfo=None)
        approved_at = compra_list.req.approved_at

        row = [
            compra_list.folio,
            compra_list.req.orden.distrito.nombre,
            f"{compra_list.req.orden.staff.staff.staff.first_name} {compra_list.req.orden.staff.staff.staff.last_name}",
            f"{compra_list.creada_por.staff.staff.first_name} {compra_list.creada_por.staff.staff.last_name}",
            created_at,
            approved_at,
            compra_list.proveedor.nombre.razon_social,
            compra_list.estatus_original,
            compra_list.cond_de_pago.nombre,
            compra_list.costo_oc,
            compra_list.monto_pagado,
            'Pagada' if compra_list.pagada else 'No Pagada',
            primera_fecha_pago,
            'Autorizado' if compra_list.autorizado2 else 'Cancelado' if compra_list.autorizado2 == False or compra_list.autorizado1 == False else 'Pendiente Autorización',
            tipo_producto,
            compra_list.dias_de_entrega,
            compra_list.moneda.nombre,
            tipo_de_cambio,  # Asegúrate de que tipo_de_cambio sea un valor que pueda ser escrito directamente
            'Entregada' if compra_list.entrada_completa else 'No Entregada',
            'Sí' if compra_list.facturas.exists() else 'No',
        ]
        
        for col_num, cell_value in enumerate(row):
        # Define el formato por defecto
            cell_format = body_style

            # Aplica el formato de fecha para las columnas con fechas
            if col_num in [4, 5]:  # Asume que estas son tus columnas de fechas
                cell_format = date_style
        
            # Aplica el formato de dinero para las columnas con valores monetarios
            elif col_num in [9, 10]:  # Asume que estas son tus columnas de dinero
                cell_format = money_style

            # Finalmente, escribe la celda con el valor y el formato correspondiente
            worksheet.write(row_num, col_num, cell_value, cell_format)

      
        worksheet.write_formula(row_num, 20, f'=IF(ISBLANK(R{row_num+1}), K{row_num+1}, K{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Matriz_compras_{dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=3)  # La cookie expira en 20 segundos
    output.close()
    return response

@csrf_exempt
#@login_required
def aceptar_politica(request):
    perfil_id = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id=perfil_id)
    proveedor = Proveedor.objects.get(id=perfil.proveedor.id)
    if request.method == 'POST':
        data = json.loads(request.body)
        clave = data.get('clave')
        print('clave:',clave)
        if proveedor and clave:
            now = timezone.now()

            if clave == 'antisoborno':
                proveedor.acepto_politica = True
            elif clave == 'proveedores':
                proveedor.acepto_politica_proveedor = True
            elif clave == 'privacidad':
                proveedor.acepto_aviso_privacidad = True
            elif clave == 'etica':
                proveedor.acepto_codigo_etica = True
                proveedor.fecha_aceptacion_politica = now
            # puedes seguir agregando aquí más claves/políticas
            
            else:
                return JsonResponse({'error': 'Política no reconocida'}, status=400)

            proveedor.save()
            return JsonResponse({'success': True})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@perfil_seleccionado_required
def invitar_proveedor(request):
    print('invitar_proveedor')
    pk_perfil = request.session.get('selected_profile_id')
    perfil = get_object_or_404(Profile, id=pk_perfil)

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        rfc   = (request.POST.get('rfc') or '').strip().upper()
        tipo  = (request.POST.get('tipo') or '').strip()
        # Convertir checkboxes a booleanos
        producto = bool(request.POST.get('producto'))
        servicio = bool(request.POST.get('servicio'))
        arrendamiento = bool(request.POST.get('arrendamiento'))
        
        
        if InvitacionProveedor.objects.filter(email=email, usado=False).exists():
            messages.error(request, 'Ya existe una invitación pendiente para este correo.')
            return redirect('invitar-proveedor')

        if tipo not in ('NUEVO_PROVEEDOR', 'NUEVA_DIRECCION', 'NUEVO_USUARIO'):
            messages.error(request, 'Tipo de invitación inválido.')
            return redirect('invitar-proveedor')
        
        # 2) Validaciones según el tipo de invitación
        distrito = perfil.distritos  # distrito del usuario que invita
        ESTATUS_VALIDOS = ['NUEVO', 'APROBADO']
        print('tipo:',tipo)
        if tipo in ("NUEVA_DIRECCION", "NUEVO_USUARIO"):
            # En estos casos, el proveedor DEBE existir
            proveedor = Proveedor.objects.filter(rfc=rfc).first()
            if not proveedor:
                messages.error(
                    request,
                    'No se encontró un proveedor con ese RFC. '
                    'Debes registrarlo como nuevo proveedor primero.'
                )
                return redirect('invitar-proveedor')
            
             # No puedes invitar si ya tiene dirección ACTIVA en ese distrito
            existe_dir = Proveedor_direcciones.objects.filter(
                nombre=proveedor,
                distrito=distrito,
                completo=True,
                estatus__nombre__in=ESTATUS_VALIDOS,
            ).exists()
            
            if existe_dir:
                messages.error(
                    request,
                    f'El proveedor ya tiene una dirección activa en el distrito {distrito}. '
                    'No puedes enviar invitación para este distrito.'
                )
                return redirect('invitar-proveedor')
            else:
                
                #print('sí, esta pasando1')
                if tipo == "NUEVO_USUARIO" and User.objects.filter(email = email).exists():
                    messages.error(request, 'Este correo ya está registrado como usuario en SAVIA.')
                    return redirect('invitar-proveedor')


             

                invitacion = InvitacionProveedor.objects.create(
                    proveedor = proveedor,
                    email=email,
                    rfc=rfc,
                    creado_por=perfil,
                    tipo=tipo,
                     # <<< Los 3 booleanos guardados correctamente >>>
                    producto=producto,
                    servicio=servicio,
                    arrendamiento=arrendamiento,
                )

                if tipo == "NUEVA_DIRECCION":
                    link = request.build_absolute_uri(reverse('user-login'))
                else:
                    link = request.build_absolute_uri(reverse('registro-proveedor', args=[invitacion.token]))
                
                enviar_correo_invitacion(
                    email, rfc, link,
                    f"{perfil.staff.staff.first_name} {perfil.staff.staff.last_name}", tipo
                )

                return render(request, 'proveedores_externos/invitacion_enviada.html', {'link': link})
                
        else:
            print('sí, esta pasando')
            invitacion = InvitacionProveedor.objects.create(
                email=email,
                rfc=rfc,
                creado_por=perfil,
                tipo=tipo,
                 # <<< Los 3 booleanos guardados correctamente >>>
                producto=producto,
                servicio=servicio,
                arrendamiento=arrendamiento,
            )

            link = request.build_absolute_uri(
                reverse('registro-proveedor', args=[invitacion.token])
            )
            enviar_correo_invitacion(
                email, rfc, link,
                f"{perfil.staff.staff.first_name} {perfil.staff.staff.last_name}", tipo
            )

            return render(request, 'proveedores_externos/invitacion_enviada.html', {'link': link})

    return render(request, 'proveedores_externos/formulario_invitacion.html')


def check_proveedor_ajax(request):
    rfc   = (request.GET.get('rfc') or '').strip().upper()
    email = (request.GET.get('email') or '').strip()
    exists_rfc = Proveedor.objects.filter(rfc=rfc).exists()
    exists_email_or_invite = (
        User.objects.filter(email=email).exists() or
        InvitacionProveedor.objects.filter(email=email, usado=False).exists()
    )
    print(exists_rfc)
    print(exists_email_or_invite)
    proveedor_razon = ''
    proveedor_id = None
    direcciones_data = []
    estatus_set = set()
   

    ESTATUS_VALIDOS = ['NUEVO', 'APROBADO']

    if exists_rfc:
        proveedor = Proveedor.objects.filter(rfc=rfc).first()
        print('proveedor:',proveedor)
        if proveedor:

            proveedor_razon = proveedor.razon_social
            proveedor_id = proveedor.id
            print('proveedor_razon:', proveedor_razon)
            # FILTRAR SOLO DIRECCIONES ACTIVAS CON ESTATUS PERMITIDO
            direcciones_filtradas = Proveedor_direcciones.objects.filter(
                nombre = proveedor,
                distrito__status=True,
                estatus__nombre__in=ESTATUS_VALIDOS
            )
            print('direcciones_filtradas:', direcciones_filtradas)

            for d in direcciones_filtradas:
                distrito_nombre = getattr(getattr(d, 'distrito', None), 'nombre', '')
                estatus_nombre = getattr(getattr(d, 'estatus', None), 'nombre', '')

                if estatus_nombre:
                    estatus_set.add(estatus_nombre)

                direcciones_data.append({
                    'id': d.id,
                    'distrito': distrito_nombre,
                    'estatus': estatus_nombre,
                })
        
   
    return JsonResponse({
        'exists_rfc': exists_rfc,
        'exists_email_or_invite': exists_email_or_invite,
        'proveedor_id': proveedor_id,
        'proveedor_razon': proveedor_razon,
        'direcciones': direcciones_data,
        'estatus_lista': list(estatus_set),
    })

def enviar_correo_invitacion(email_destino, rfc, link, creado_por_nombre, tipo):
    print(tipo)
    static_path = settings.STATIC_ROOT
    img_path1 = os.path.join(static_path, 'images', 'SAVIA_Logo.png')
    img_path2 = os.path.join(static_path, 'images', 'logo_vordcab.jpg')
    image_base64 = get_image_base64(img_path1)
    logo_v_base64 = get_image_base64(img_path2)
    link = link
    if tipo == 'NUEVA_DIRECCION':
        titulo = "Agregar nueva dirección de facturación/servicio"
        cuerpo = f"""
            Has recibido una invitación para agregar una <strong>nueva dirección</strong>
            asociada al RFC <strong>{rfc}</strong> en el portal de proveedores.
        """
        pasos = """
            <ol style="font-size: 15px; padding-left: 20px; color: #333;">
                <li>Accede al portal con tus credenciales habituales.</li>
                <li>Da clic en el botón "Agregar dirección"</li>
                <li>Llena la información de domicilio, contacto y condiciones de pago.</li>
            </ol>
        """
        texto_boton = "Ir al portal"
    if tipo == 'NUEVO_USUARIO':
        titulo = "Agregar un nuevo usuario + dirección de proveedor existente"
        cuerpo = f"""
            Has recibido una invitación para darte de alta como <strong> usuario nuevo </strong> dentro de nuestra plataforma.
            Esta nueva cuenta está asociada con el RFC de proveedor existente <strong>{rfc}</strong>        
        """
        pasos = """
            <ul style="font-size: 15px; padding-left: 20px; color: #333;">
                <li><strong>Completar tu registro inicial</strong> dando clic en el botón que aparece a continuación.</li>
                <li>Acceder al portal de proveedores con los datos de acceso generados.</li>
            </ul>
            <ol style="font-size: 15px; padding-left: 20px; color: #333;">
                <li>Aceptar las políticas y códigos de Grupo Vordcab.</li>
                <li>Subir los documentos requeridos.</li>
                <li>Contestar el cuestionario de Debida Diligencia.</li>
            </ol>
        """
        texto_boton = "Completar registro"
    else:
        titulo = "Invitación a registrarte como proveedor"
        cuerpo = f"""
            Has sido invitado a registrarte como proveedor en nuestra plataforma.
            Tu RFC registrado es <strong>{rfc}</strong>.
        """
        pasos = """
            <ul style="font-size: 15px; padding-left: 20px; color: #333;">
                <li><strong>Completar tu registro inicial</strong> dando clic en el botón que aparece a continuación.</li>
                <li>Acceder al portal de proveedores con los datos de acceso generados.</li>
            </ul>
            <ol style="font-size: 15px; padding-left: 20px; color: #333;">
                <li>Aceptar las políticas y códigos de Grupo Vordcab.</li>
                <li>Subir los documentos requeridos.</li>
                <li>Contestar el cuestionario de Debida Diligencia.</li>
            </ol>
        """
        texto_boton = "Completar registro"

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
                                        <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 120px;" />
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="font-size: 18px;">Hola,</p>
                                        <p style="font-size: 16px;">
                                            {cuerpo}
                                        </p>
                                        <h3 style="margin-top: 30px; font-size: 16px;">{pasos}</h3>
                                        

                                        <button style="text-align: center; margin: 30px 0;">
                                            <a href="{link}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                                                {texto_boton}
                                            </a>
                                        </button>
                                        <p style="font-size: 14px;">Si no esperabas este correo, puedes ignorarlo.</p>
                                        <p style="margin-top: 40px; font-size: 14px;">Atentamente,<br><strong>{creado_por_nombre}</strong></p>
                                        <div style="text-align: center; margin-top: 30px;">
                                            <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                            <p style="font-size: 12px; color: #999;">Este mensaje fue generado por SAVIA 2.0</p>
                                        </div>
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
            subject='Invitación para registro de proveedor',
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino, "proveedores.sur@grupovordcab.com"],
        )
        email.content_subtype = "html"
        email.send()
    except Exception as e:
        print(f"Error al enviar el correo: {e}")


def enviar_correo_registro_exitoso(usuario_email, creado_por_nombre, savia_url):
    static_path = settings.STATIC_ROOT
    img_path1 = os.path.join(static_path, 'images', 'SAVIA_Logo.png')
    img_path2 = os.path.join(static_path, 'images', 'logo_vordcab.jpg')
    image_base64 = get_image_base64(img_path1)
    logo_v_base64 = get_image_base64(img_path2)

    html_success_message = f"""
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
                                <img src="data:image/jpeg;base64,{logo_v_base64}" alt="Logo" style="width: 120px;" />
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px;">
                                <p style="font-size: 18px;">¡Registro exitoso!</p>
                                <p style="font-size: 16px;">
                                    Has completado tu registro correctamente como proveedor en nuestra plataforma.
                                </p>
                                <p style="font-size: 16px;">
                                    Tu usuario registrado es: <strong>{usuario_email}</strong>
                                </p>

                                <p style="text-align: center; margin: 30px 0;">
                                    <a href="{savia_url}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                                        Acceder al portal
                                    </a>
                                </p>

                                <h3 style="margin-top: 30px; font-size: 16px;">Siguientes pasos:</h3>
                                <ul style="font-size: 15px; padding-left: 20px; color: #333;">
                                    <li>Inicia sesión con tu usuario y contraseña.</li>
                                </ul>
                                <ol style="font-size: 15px; padding-left: 20px; color: #333;">
                                    <li>Acepta las políticas y códigos de Grupo Vordcab.</li>
                                    <li>Sube los documentos requeridos.</li>
                                    <li>Contesta el cuestionario de Debida Diligencia.</li>
                                </ol>

                                <p style="font-size: 14px;">Si no esperabas este correo, puedes ignorarlo.</p>
                                <p style="margin-top: 40px; font-size: 14px;">Atentamente,<br><strong>{creado_por_nombre}</strong></p>

                                <div style="text-align: center; margin-top: 30px;">
                                    <img src="data:image/png;base64,{image_base64}" alt="Imagen" style="width: 50px; height: auto; border-radius: 50%;" />
                                    <p style="font-size: 12px; color: #999;">Este mensaje fue generado por SAVIA 2.0</p>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    email = EmailMessage(
        subject="Registro exitoso en SAVIA 2.0",
        body=html_success_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario_email],
    )
    email.content_subtype = "html"
    email.send()

def registro_proveedor(request, token):
    invitacion = get_object_or_404(InvitacionProveedor, token=token, usado=False)
    tipo_invitacion = invitacion.tipo or 'NUEVO_PROVEEDOR'

    # =======================================
    # 1) SOLO NUEVA DIRECCIÓN (tu form nuevo)
    # =======================================
    if tipo_invitacion == 'NUEVA_DIRECCION':
        return registro_solo_direccion(request, invitacion)

    # =======================================
    # 2) FLUJO ORIGINAL (NUEVO_PROVEEDOR)
    #    aquí dejas exactamente tu código actual
    # =======================================

    
    if request.method == 'POST':
        #print(invitacion.email)
        form = RegistroProveedorForm(request.POST)
        # 🔹 Si la invitación YA tiene proveedor, ocultamos y hacemos opcional razon_social
        if invitacion.tipo =="NUEVO_USUARIO":
            form.fields['razon_social'].required = False
            form.fields['razon_social'].widget = forms.HiddenInput()
        if form.is_valid():
            print("El formulario es válido")
            # 1 Objeto user
            user = User.objects.create(
                username=invitacion.email,
                email=invitacion.email,
                first_name = form.cleaned_data['contacto'],
                password=make_password(form.cleaned_data['password'])
            )
                
            # 2 Objeto proveedor
            if invitacion.proveedor:
                proveedor = invitacion.proveedor
            else:
                proveedor = Proveedor.objects.create(
                    rfc=invitacion.rfc,
                    razon_social=form.cleaned_data['razon_social'],
                    creado_por=invitacion.creado_por,
                    completo = True,
                )

                #3 Objeto CustomUser
            customuser = CustomUser.objects.create(
                staff = user,
                banco = form.cleaned_data['banco'],
                cuenta_bancaria = form.cleaned_data['cuenta'],
                clabe = form.cleaned_data['clabe'],
                phone = form.cleaned_data['telefono'],
                puesto = "Proveedor Externo",
                nivel = 5,
                apoyo_renta = 0,
                apoyo_mantto = 0,
            )
            #4 Objeto tipo
            tipo = Tipo_perfil.objects.get(nombre="PROVEEDOR_EXTERNO")
            distrito = invitacion.creado_por.distritos
            #5 Objeto perfil
            profile = Profile.objects.create(
                staff=customuser,
                tipo=tipo,
                proveedor=proveedor,
                distritos= distrito,
                st_activo =True,

            )
           
            almacenes = Almacen.objects.filter(nombre = distrito.nombre)
            profile.almacen.set(almacenes)
            condicion_seleccionada = form.cleaned_data['condiciones']
            if condicion_seleccionada == 'CREDITO':
                financiamiento = True
            else:
                financiamiento = False

            producto_inv = invitacion.producto
            servicio_inv = invitacion.servicio
            arrendamiento_inv = invitacion.arrendamiento
            #5.5
            status = Estatus_proveedor.objects.get(nombre="PREALTA")
                #6 Objeto Proveedor_direcciones
            direccion, creada = Proveedor_direcciones.objects.update_or_create(
                nombre=proveedor,
                distrito = invitacion.creado_por.distritos,
                defaults = {
                'creado_por' : profile,
                'domicilio':form.cleaned_data['domicilio'],
                'telefono':form.cleaned_data['telefono'],
                'contacto':form.cleaned_data['contacto'],
                'email':invitacion.email,
                'banco':form.cleaned_data['banco'],
                'clabe':form.cleaned_data['clabe'],
                #distrito=invitacion.creado_por.distritos,
                'cuenta': form.cleaned_data['cuenta'],
                'email_opt': form.cleaned_data['email_opt'],
                'estatus' : status,
                 # Aquí capturas los booleanos:
                'producto': producto_inv,
                'servicio': servicio_inv,
                'arrendamiento': arrendamiento_inv,
                'moneda':form.cleaned_data['moneda'],
                'financiamiento':financiamiento,
                'dias_credito':form.cleaned_data['dias_credito'],
                'completo': True,
                }
            )
            #Deshabilitación de la invitación por medio del usado = True
            invitacion.usado = True
            invitacion.fecha_uso = now()
            invitacion.proveedor = proveedor
            invitacion.save()
           
            # Datos del correo
            savia_url = "https://grupovordcab.cloud"
            correo_destino = invitacion.email
            enviar_correo_registro_exitoso(
                usuario_email = correo_destino, 
                creado_por_nombre = f"{invitacion.creado_por.staff.staff.first_name} {invitacion.creado_por.staff.staff.last_name}", 
                savia_url = savia_url
                )
            messages.success(request, 'Registro exitoso. Espera correo de confirmación')    
            return redirect('user-login')  # O alguna página de éxito        
        else:
            print("El formulario NO es válido")
            print(form.errors)
            messages.error(request, f'Error al registrar el proveedor. Por favor, revisa los datos ingresados.{form.errors}')
            
    else:
        form = RegistroProveedorForm(initial={'email': invitacion.email, 'rfc': invitacion.rfc})

        if tipo_invitacion == 'NUEVO_USUARIO':
            form.fields['razon_social'].required = False
            form.fields['razon_social'].widget = forms.HiddenInput()

    context = {
        'form': form,
        'tipo_invitacion': tipo_invitacion,
    }

    return render(request, 'proveedores_externos/registro_proveedor.html', context)

#@login_required
def cuestionario_debida_diligencia(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    hecho = Debida_Diligencia.objects.filter(proveedor=proveedor, terminada=True)
    if hecho.exists():
        messages.info(request, 'El cuestionario de Debida Diligencia ya ha sido completado para este proveedor.')
        return redirect('dashboard-index')
    else:
        debida_diligencia, created = Debida_Diligencia.objects.get_or_create(proveedor=proveedor, terminada=False)
        miembros = Miembro_Alta_Direccion.objects.filter(cuestionario=debida_diligencia)
        empleados_funcionarios = Funcionario_Publico_Relacionado.objects.filter(cuestionario=debida_diligencia)
        accionistas_funcionarios = Relacion_Servidor_Publico.objects.filter(cuestionario=debida_diligencia)
        responsables_interaccion = Responsable_Interaccion.objects.filter(cuestionario=debida_diligencia)

        diligencia_form = DebidaDiligenciaForm(instance=debida_diligencia)

        accionista_form = AccionistaForm()
        funcionario_form = FuncionarioPublicoRelacionadoForm()
        relacion_form = RelacionServidorPublicoForm()
        responsable_form = ResponsableInteraccionForm()
        direccion_form = MiembroAltaDireccionForm() 

        try:
            documento_csf = DocumentosProveedor.objects.get(
                proveedor_id=proveedor_id,
                tipo_documento="csf",
                activo=True,
                obsoleto=False,
            ) 
        except DocumentosProveedor.DoesNotExist:
            documento_csf = None

        if documento_csf == None:
            print("No se ha subido el documento CSF.")
            tipo = None
        else:  
            tipo = extraer_tipo_contribuyente(documento_csf.archivo.path)
            print(f"El contribuyente es: {tipo}")
        
        error_messages = []

        if request.method == 'POST':
            if 'submit_diligencia' in request.POST:
                print('Estoy entrando aquí al diligencia. POST')
                form = DebidaDiligenciaForm(request.POST, instance = debida_diligencia)
                if form.is_valid():
                    debida_diligencia_form = form.save(commit =False)
                    debida_diligencia.terminada = True
                    debida_diligencia.fecha = date.today()
                    debida_diligencia_form.save() 
                    messages.success(request, f"El cuestionario de Debida Diligencia ha sido llenado exitosamente.")
                    return redirect('dashboard-index') 
                else:
                    print('Estoy entrando aquí a los errores')
                    # Errores por campo
                    for field, errors in form.errors.items():
                        label = form.fields.get(field).label if field in form.fields else field
                        for err in errors:
                            error_messages.append(f"{label}: {err}")

                    # Errores generales (non_field_errors)
                    for err in form.non_field_errors():
                        error_messages.append(str(err))

            elif 'submit_accionista' in request.POST:
                form = AccionistaForm(request.POST)
                if form.is_valid():
                    accionista_form = form.save(commit=False)
                    accionista_form.cuestionario = debida_diligencia
                    accionista_form.save()
                    
                return redirect('cuestionario', proveedor_id=proveedor.id)

            elif 'submit_direccion' in request.POST:
                form = MiembroAltaDireccionForm(request.POST)
                if form.is_valid():
                    direccion_form = form.save(commit=False)
                    direccion_form.cuestionario = debida_diligencia
                    direccion_form.save()
                    debida_diligencia.tiene_alta_direccion = True
                    debida_diligencia.save()

                return redirect('cuestionario', proveedor_id=proveedor.id)

            elif 'submit_funcionario' in request.POST:
                form = FuncionarioPublicoRelacionadoForm(request.POST)
                if form.is_valid():
                    funcionario_form = form.save(commit=False)
                    funcionario_form.cuestionario = debida_diligencia
                    funcionario_form.save()
                    #form.save()
                    debida_diligencia.empleado_funcionarios_publicos = True
                    debida_diligencia.save()
                return redirect('cuestionario', proveedor_id=proveedor.id)

            elif 'submit_relacion' in request.POST:
                form = RelacionServidorPublicoForm(request.POST)
                if form.is_valid():
                    relacion_form = form.save(commit=False)
                    relacion_form.cuestionario = debida_diligencia
                    relacion_form.save()
                    debida_diligencia.pertenece_funcionario_publico = True
                    debida_diligencia.save()
                return redirect('cuestionario', proveedor_id=proveedor.id)

            elif 'submit_responsable' in request.POST:
                form = ResponsableInteraccionForm(request.POST)
                if form.is_valid():
                    responsable_form = form.save(commit=False)
                    responsable_form.cuestionario = debida_diligencia
                    responsable_form.save() 
                return redirect('cuestionario', proveedor_id=proveedor.id)
            else:
                messages.error(request, 'Formulario no reconocido.')
    
        context = {
            'proveedor': proveedor,
            'tipo': tipo,
            'miembros': miembros,
            'empleados_funcionarios': empleados_funcionarios,
            'accionistas_funcionarios': accionistas_funcionarios,
            'responsables_interaccion': responsables_interaccion,
            'diligencia_form': diligencia_form,
            'accionista_form' : accionista_form,
            'funcionario_form' : funcionario_form,
            'relacion_form' : relacion_form,
            'responsable_form' : responsable_form,
            'direccion_form' :  direccion_form, 
            'error_messages': error_messages,
        }

        return render(request, 'proveedores_externos/cuestionario.html', context)
    
def registro_solo_direccion(request, pk):
    """
    Usado cuando InvitacionProveedor.tipo == 'NUEVA_DIRECCION'
    Solo crea un Proveedor_direcciones adicional.
    """
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    # El proveedor ya debe existir (el flujo de invitación ya validó el RFC)
    proveedor = Proveedor.objects.get(id=pk)
    invitacion = InvitacionProveedor.objects.get(proveedor = proveedor,tipo= "NUEVA_DIRECCION", usado = False)
    form = ProveedoresExistDireccionesForm()
    if not invitacion:
         # Si NO hay invitación válida, lo regresas al index (o donde prefieras)
        messages.error(
            request,
            'No tienes una invitación válida para registrar una nueva dirección.'
        )
        return redirect('index')   # <-- cambia 'index' si tu URL se llama distinto

    if request.method == 'POST':
        item, created = Proveedor_direcciones.objects.get_or_create(nombre = proveedor, distrito = invitacion.creado_por.distritos)
        form = ProveedoresExistDireccionesForm(request.POST, instance = item)
        if form.is_valid():
            direccion = form.save(commit=False)
            direccion.nombre = proveedor
            direccion.creado_por = usuario
            actualizado_por = usuario
            status = Estatus_proveedor.objects.get(nombre = "NUEVO")
            direccion.estatus = status
            # si quieres asegurar distrito por defecto:
            
            #direccion.distrito = invitacion.creado_por.distritos
            direccion.created_at = datetime.now()
            direccion.completo = True
            direccion.save()

            invitacion.usado = True
            invitacion.fecha_uso = datetime.now()
            #invitacion.proveedor = proveedor
            invitacion.save()

            messages.success(request, 'Nueva dirección registrada correctamente.')
            # aquí ya podrías mandarlo a su dashboard de proveedor
            return redirect('dashboard-index')  # o 'dashboard-proveedor'
        else:
            print(form.errors)
            messages.error(request, f'Error al registrar la dirección: {form.errors}')
   
        

      

    context = {
        'form': form, 
        'invitacion': invitacion, 
        'proveedor': proveedor
    }

    return render(request,'proveedores_externos/registro_direccion.html', context)
    
def eliminar_miembro(request, pk):
    miembro = get_object_or_404(Miembro_Alta_Direccion, id=pk)
    proveedor_id = miembro.cuestionario.proveedor.id
    nombre = miembro.nombre
    miembro.delete()
    messages.success(request, f"Se eliminó {nombre} de la alta dirección.")
    return redirect("cuestionario", proveedor_id=proveedor_id)

def eliminar_empleado_funcionario(request, pk):
    funcionario_empleado = get_object_or_404(Funcionario_Publico_Relacionado, id=pk)
    proveedor_id = funcionario_empleado.cuestionario.proveedor.id
    nombre = funcionario_empleado.nombre
    funcionario_empleado.delete()
    messages.success(request, f"Se eliminó {nombre} de la sección de empleados que son funcionaríos.")
    return redirect("cuestionario", proveedor_id=proveedor_id)

def eliminar_accionista_funcionario(request, pk):
    funcionario_accionista = get_object_or_404(Relacion_Servidor_Publico, id=pk)
    proveedor_id = funcionario_accionista.cuestionario.proveedor.id
    nombre = funcionario_accionista.nombre_servidor
    funcionario_accionista.delete()
    messages.success(request, f"Se eliminó {nombre} de la sección de accionistas que son funcionarios.")
    return redirect("cuestionario", proveedor_id=proveedor_id)

def eliminar_responsable_interaccion(request, pk):
    responsable = get_object_or_404(Responsable_Interaccion, id=pk)
    proveedor_id = responsable.cuestionario.proveedor.id
    nombre = responsable.nombre
    responsable.delete()
    messages.success(request, f"Se eliminó {nombre} de la sección de responsables de interacción con el gobierno.")
    return redirect("cuestionario", proveedor_id=proveedor_id)


def extraer_tipo_contribuyente(pdf_path):
    # Abrir el PDF
    doc = fitz.open(pdf_path)
    texto = []
    for pagina in doc:
        texto.append(pagina.get_text() or "")
    doc.close()

    texto_plano = _normalize(" ".join(texto))

    if "regimen capital" in texto_plano:
        return "Persona Moral"
    else:
        return "Persona Física"
    

def _normalize(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))




