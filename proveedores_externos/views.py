from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.db.models import F, Avg, Value, ExpressionWrapper, fields, Sum, Q, DateField, Count, Case, When, Value, DecimalField
from django.core.paginator import Paginator
from compras.models import Compra, Proveedor, Proveedor_direcciones
from user.models import Profile
from compras.filters import CompraFilter
from requisiciones.models import Requis
from user.decorators import perfil_seleccionado_required
from datetime import date, datetime, timedelta
from .forms import CSFForm
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
        #if compras.count() > 2400:
        #    if not task_id:
        #        task = convert_excel_matriz_compras_task.delay(compras_data, num_requis_atendidas, num_approved_requis, start_date, end_date)
        #        task_id = task.id
        #        request.session['task_id'] = task_id
        #        context['task_id'] = task_id
        #        cantidad = compras.count()
        #        context['cantidad'] = cantidad
        #        messages.success(request, f'Tu reporte se está generando {task_id}')
        #else:
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