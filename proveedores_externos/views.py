from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.db.models import F, Avg, Value, ExpressionWrapper, fields, Sum, Q, DateField, Count, Case, When, Value, DecimalField
from django.core.paginator import Paginator
from compras.models import Compra, Proveedor, Proveedor_direcciones, Evidencia
from user.models import Profile
from compras.filters import CompraFilter
from requisiciones.models import Requis
from user.decorators import perfil_seleccionado_required
from datetime import date, datetime, timedelta
from .forms import CSFForm, ActaForm, ComprobanteForm, OpinionForm, UploadFileForm
from django.contrib import messages
from io import BytesIO
from django.db.models.functions import Concat, Coalesce
from tesoreria.models import Pago, Facturas
import datetime as dt
import decimal
# Import Excel Stuff
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
# Create your views here.

@perfil_seleccionado_required
def matriz_oc_proveedores(request):
    pk_perfil = request.session.get('selected_profile_id')
    colaborador_sel = Profile.objects.all()
    usuario = colaborador_sel.get(id = pk_perfil)
    print(usuario)
    try:
        proveedor = Proveedor.objects.get(perfil_proveedor = usuario)
        print('que')
    except Proveedor.DoesNotExist:
        proveedor = None
    print(proveedor)
    if usuario.tipo.proveedor_externo == True and proveedor is not None:
        compras = Compra.objects.filter(
            complete = True, 
            proveedor__nombre = proveedor, 
            autorizado2 = True).annotate(
            total_facturas=Count('facturas', filter=Q(facturas__hecho=True)),
            autorizadas=Count(Case(When(Q(facturas__autorizada=True, facturas__hecho=True), then=Value(1))))
            ).order_by('-folio')
    else:
        compras = Compra.objects.none()
    
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
        if usuario.tipo.nombre == "PROVEEDORES" or usuario.tipo.nombre == "VIS_ADQ":
            approved_requis = Requis.objects.filter(approved_at__gte=start_date, approved_at__lte=end_date, autorizar = True)
        else:
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
    
    if usuario.tipo.proveedor_externo:
        proveedor = Proveedor.objects.get(perfil_proveedor = usuario)
        direcciones = Proveedor_direcciones.objects.filter(nombre= proveedor, completo = True)
      
    else:
        raise Http404("No tienes permiso para ver esta vista")
    context = {
        'proveedor':proveedor,
        'direcciones':direcciones,
        }
    return render(request,'proveedores_externos/informacion_proveedores.html', context)

@perfil_seleccionado_required
def edit_csf(request, pk):
    proveedor = Proveedor.objects.get(id = pk)
    print(proveedor.id)
    form = CSFForm(instance = proveedor)

    if request.method == 'POST':
        form = CSFForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'proveedor':proveedor,
        'form':form, 
    }
    
    return render(request, 'proveedores_externos/edit_csf.html',context)

@perfil_seleccionado_required
def edit_acta_credencial(request, pk):
    proveedor = Proveedor.objects.get(id = pk)
    print(proveedor.id)
    form = ActaForm(instance = proveedor)

    if request.method == 'POST':
        form = ActaForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'proveedor':proveedor,
        'form':form, 
    }
    
    return render(request, 'proveedores_externos/edit_acta_credencial.html',context)

@perfil_seleccionado_required
def edit_comprobante_domicilio(request, pk):
    proveedor = Proveedor.objects.get(id = pk)
    print(proveedor.id)
    form = ComprobanteForm(instance = proveedor)

    if request.method == 'POST':
        form = ComprobanteForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'proveedor':proveedor,
        'form':form, 
    }
    
    return render(request, 'proveedores_externos/edit_comprobante_domicilio.html',context)

@perfil_seleccionado_required
def edit_opinion_cumplimiento(request, pk):
    proveedor = Proveedor.objects.get(id = pk)
    print(proveedor.id)
    form = OpinionForm(instance = proveedor)

    if request.method == 'POST':
        form = OpinionForm(request.POST, request.FILES, instance=proveedor)
        if form.is_valid():
            form.save()
            return HttpResponse(status=204) #No content to render nothing and send a "signal" to javascript in order to close window
    
    context = {
        'proveedor':proveedor,
        'form':form, 
    }
    
    return render(request, 'proveedores_externos/edit_opinion_cumplimiento.html',context)

@perfil_seleccionado_required
def evidencias_proveedor(request, pk):
    pk_usuario = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_usuario)
    compra = Compra.objects.get(id = pk)
    evidencias = Evidencia.objects.filter(oc = compra, hecho=True)
    
    
    next_url = request.GET.get('next',)

    #evidencia_form = EvidenciaForm()
    #next_url = request.GET.get('next', 'mis-gastos') 
    #print(next_url)

    #if request.method == 'POST':
     #   if "btn_enviar_evidencia" in request.POST:
      #      fecha_hora = datetime.today()
      #      for evidencia in evidencias:
                #checkbox_name = f'autorizar_factura_{factura.id}'
                #print("Nombre del checkbox esperado:", checkbox_name)  # Imprimir el nombre esperado
                #if checkbox_name in request.POST:
                #    print('PASO 1')
                #    factura.autorizada = True
                #    factura.autorizada_por = usuario
                #    factura.autorizada_el = fecha_hora
      #          else:
      #              print('No paso')
      #              factura.autorizada = False
      #          factura.save()
      #      if form.is_valid():
      #          gasto = form.save(commit=False)
      #          gasto.verificacion_facturas = usuario
      #          gasto.save()
      #         messages.success(request,'Haz cambiado el status de facturas completas')
      #          return redirect(next_url) 
      #      else:
      #          messages.error(request,'No está validando')
      #  elif "btn_descargar_todo" in request.POST:
      #      in_memory_zip, zip_filename = generar_archivo_zip(facturas, gasto)
      #      response = HttpResponse(in_memory_zip, content_type='application/zip')
      #      response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
      #      return response
      #  elif 'salir' in request.POST:
      #      return redirect(next_url)
    
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
            form = UploadFileForm(request.POST, request.FILES or None)
            if form.is_valid():
                files_evidencia = request.FILES.getlist('evidencia_file')
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