from django.shortcuts import render, redirect
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from calendar import month_name,  monthrange
from collections import defaultdict

from .models import Costos, Solicitud_Costos, Tipo_Costo, Solicitud_Ingresos, Ingresos, Depreciaciones
from user.models import Profile, Distrito
from compras.models import Moneda
from user.decorators import perfil_seleccionado_required
from .forms import Costo_Form, Solicitud_Costo_Form, Solicitud_Ingreso_Form, Ingreso_Form, Depreciacion_Form
from datetime import date, datetime, timedelta



import openpyxl
from openpyxl.styles import NamedStyle, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image


# Create your views here.
@perfil_seleccionado_required
def costos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    costos = Solicitud_Costos.objects.filter(complete = True)
    tipos = Tipo_Costo.objects.all()
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False)
    #myfilter= ContratoFilter(request.GET, queryset=contratos)

    #Set up pagination
    #p = Paginator(contratos, 10)
    #page = request.GET.get('page')
    #contratos_list = p.get_page(page)

    context = {
        'costos':costos,
        #'myfilter': myfilter,
        'tipos': tipos,
        'distritos':distritos,
         }

    return render(request,'rentabilidad/costos.html', context)

@perfil_seleccionado_required
def add_costo(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    solicitud, created =  Solicitud_Costos.objects.get_or_create(created_by=usuario, complete = False)
    costos = Costos.objects.filter(solicitud = solicitud)
    form = Solicitud_Costo_Form()
    form.fields['distrito'].queryset = distritos
    costo_form = Costo_Form()

    if request.method =='POST':
        
       
        if "btn_agregar" in request.POST:
            form = Solicitud_Costo_Form(request.POST, instance = solicitud)
            print('estou aqui')
            if form.is_valid():
                solicitud = form.save(commit=False)
                solicitud.created_at = date.today()
                solicitud.complete = True
                solicitud.save()
                messages.success(request,'Has agregado correctamente la Solicitud')
                return redirect('rentabilidad-costos')  
            else:
                print('Nao é valido')
                print(form.errors)  
        if "btn_costo" in request.POST:
            costo, created = Costos.objects.get_or_create(complete = False, solicitud = solicitud)
            form = Costo_Form(request.POST, instance = costo)
            if form.is_valid():
                costo = form.save(commit=False)
                costo.complete = True
                costo.save()
                messages.success(request,'Has agregado correctamente un costo')
                return redirect('add-costo')
                
 

    context = {
        'form': form,
        'costo_form': costo_form,
        'costos':costos,
        'solicitud':solicitud,
        }

    return render(request,'rentabilidad/add_costo.html',context)

@perfil_seleccionado_required
def delete_costo(request, pk):
    costo = Costos.objects.get(id=pk)
    messages.success(request,f'El costo {costo.concepto} ha sido eliminado exitosamente')
    costo.delete()

    return redirect('add-costo')


def reporte_costos(request):
    tipo_id = request.GET.get("tipo_id")  # <- capturamos el valor del select
    distrito_id = request.GET.get("distrito_id", 1)  # puedes hacerlo dinámico también
    costos = Costos.objects.filter(solicitud__distrito_id=distrito_id, solicitud__tipo_id=tipo_id)
    fecha_inicio = request.GET.get("fecha_inicio")  # viene como YYYY-MM
    fecha_fin = request.GET.get("fecha_fin")        # viene como YYYY-MM

    tabla, meses = get_tabla_costos(tipo_id, distrito_id, fecha_inicio, fecha_fin)
    distrito_nombre = Distrito.objects.get(id=distrito_id).nombre
    tipo_nombre = Tipo_Costo.objects.get(id=tipo_id).nombre
    

    # 🚩 Si el usuario presiona el botón de Excel
    if request.method == "POST" and "btnReporte" in request.POST:
        return generar_costos_excel(tabla, meses, distrito_id, tipo_id, fecha_inicio, fecha_fin)

    context = { 
        "tabla": tabla,
        "meses": meses,
        "tipo_id": tipo_id,
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "tipo_nombre": tipo_nombre,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }

    return render(request, "rentabilidad/reportes_costos.html", context)

def get_tabla_costos(tipo_id=None, distrito_id=None, fecha_inicio=None, fecha_fin=None):
    costos = Costos.objects.all()

    if distrito_id:
        costos = costos.filter(solicitud__distrito_id=distrito_id)

    if tipo_id:
        costos = costos.filter(solicitud__tipo_id=tipo_id)

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m").date()
            y, m = [int(x) for x in fecha_fin.split("-")]
            last_day = monthrange(y, m)[1]
            fecha_fin = date(y, m, last_day)
            costos = costos.filter(solicitud__fecha__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass

    # Agrupamos por concepto y mes
    data = (
        costos.annotate(mes=TruncMonth("solicitud__fecha"))
        .values("concepto__nombre", "mes")
        .annotate(total=Sum("monto"))
        .order_by("concepto__nombre", "mes")
    )

    tabla = {}
    meses = set()
    for row in data:
        concepto = row["concepto__nombre"]
        mes = row["mes"].strftime("%B %Y")
        meses.add(mes)
        if concepto not in tabla:
            tabla[concepto] = {}
        tabla[concepto][mes] = row["total"]

    meses = sorted(meses, key=lambda m: (m.split()[1], list(month_name).index(m.split()[0])))

    return tabla, meses

def generar_costos_excel(tabla, meses, distrito_id=None, tipo_id=None, fecha_inicio=None, fecha_fin=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Costos"

     # Logo en A1
    img_path = "static/images/logo_vordcab.jpg"  # cambia según tu ruta real
    try:
        img = Image(img_path)
        img.width = img.width * 1
        img.height = img.height * 1
        ws.add_image(img, "A1")
        ws.row_dimensions[1].height = 70  # ajustar alto de fila 1
    except FileNotFoundError:
        pass  # si no hay logo, no truena

    # Encabezado de filtros
    fila = 2
    
    distrito_nombre = Distrito.objects.get(id=distrito_id).nombre
    tipo_nombre = Tipo_Costo.objects.get(id=tipo_id).nombre
    ws.cell(row=fila, column=1, value=f"Distrito: {distrito_nombre}")
    fila += 1
    ws.cell(row=fila,column=1, value=f"Tipo de Costo: {tipo_nombre}")
    fila += 1
    if fecha_inicio and fecha_fin:
        ws.cell(row=fila, column=1, value=f"Rango de meses: {fecha_inicio} → {fecha_fin}")
        fila += 2  # dejar espacio antes de la tabla

    #Create heading style and adding to workbook | Crear el estilo del encabezado y agregarlo al Workbook
    head_style = NamedStyle(name = "head_style")
    head_style.font = Font(name = 'Arial', color = '00FFFFFF', bold = True, size = 11)
    head_style.fill = PatternFill("solid", fgColor = '00003366')
    wb.add_named_style(head_style)

    # Encabezados
    cell = ws.cell(row=fila, column=1, value="Concepto")
    cell.style = head_style
    for col_idx, mes in enumerate(meses, start=2):
        cell = ws.cell(row=fila, column=col_idx, value=mes)
        cell.style = head_style

    # Filas
    for row_idx, (concepto, valores) in enumerate(tabla.items(), start=fila+1):
        ws.cell(row=row_idx, column=1, value=concepto)
        for col_idx, mes in enumerate(meses, start=2):
            ws.cell(row=row_idx, column=col_idx, value=valores.get(mes, 0))

    # Ajustar ancho columnas
    for i, col in enumerate(ws.columns, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = max(
            (len(str(cell.value)) for cell in col if cell.value), default=10
        ) + 2

    # Response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_costos.xlsx"'
    wb.save(response)
    return response

@perfil_seleccionado_required
def ingresos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    ingresos = Solicitud_Ingresos.objects.filter(complete = True)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False)
    #myfilter= ContratoFilter(request.GET, queryset=contratos)

    #Set up pagination
    #p = Paginator(contratos, 10)
    #page = request.GET.get('page')
    #contratos_list = p.get_page(page)

    context = {
        'ingresos':ingresos,
        #'myfilter': myfilter,
        'distritos':distritos,
         }

    return render(request,'rentabilidad/ingresos.html', context)

@perfil_seleccionado_required
def add_ingresos(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    monedas = Moneda.objects.exclude(id__in = [3] )
    solicitud, created =  Solicitud_Ingresos.objects.get_or_create(created_by=usuario, complete = False)
    ingresos = Ingresos.objects.filter(solicitud = solicitud)
    form = Solicitud_Ingreso_Form()
    form.fields['distrito'].queryset = distritos
    ingreso_form = Ingreso_Form()
    ingreso_form.fields['moneda'].queryset = monedas

    if request.method =='POST':
        
       
        if "btn_agregar" in request.POST:
            form = Solicitud_Ingreso_Form(request.POST, instance = solicitud)
            print('estou aqui')
            if form.is_valid():
                solicitud = form.save(commit=False)
                solicitud.created_at = date.today()
                solicitud.complete = True
                solicitud.save()
                messages.success(request,'Has agregado correctamente la Solicitud')
                return redirect('rentabilidad-ingresos')  
            else:
                print('Nao é valido')
                print(form.errors)  
        if "btn_ingreso" in request.POST:
            ingreso, created = Ingresos.objects.get_or_create(complete = False, solicitud = solicitud)
            form = Ingreso_Form(request.POST, instance = ingreso)
            if form.is_valid():
                ingreso = form.save(commit=False)
                ingreso.complete = True
                ingreso.save()
                messages.success(request,'Has agregado correctamente un ingreso')
                return redirect('add-ingreso')
                
 

    context = {
        'form': form,
        'ingreso_form': ingreso_form,
        'ingresos':ingresos,
        'solicitud':solicitud,
        }

    return render(request,'rentabilidad/add_ingreso.html',context)

@perfil_seleccionado_required
def delete_ingreso(request, pk):
    ingreso = Ingresos.objects.get(id=pk)
    messages.success(request,f'El ingreso {ingreso.concepto} ha sido eliminado exitosamente')
    ingreso.delete()

    return redirect('add-ingreso')

def get_tabla_ingresos(distrito_id=None, fecha_inicio=None, fecha_fin=None):
    ingresos = Ingresos.objects.all()

    if distrito_id:
        ingresos = ingresos.filter(solicitud__distrito_id=distrito_id)

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m").date()
            y, m = [int(x) for x in fecha_fin.split("-")]
            last_day = monthrange(y, m)[1]
            fecha_fin = date(y, m, last_day)
            ingresos = ingresos.filter(solicitud__fecha__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass

    data = (
        ingresos.annotate(mes=TruncMonth("solicitud__fecha"))
        .values("contrato_id", "contrato__nombre", "mes")  # 👈 usa el campo visible de Contrato
        .annotate(total=Sum("monto"))
        .order_by("contrato__nombre", "mes")
    )


    tabla = {}
    meses = set()
    for row in data:
        contrato_nombre = row["contrato__nombre"]
        mes = row["mes"].strftime("%B %Y")
        meses.add(mes)
        if contrato_nombre not in tabla:
            tabla[contrato_nombre] = {}
        tabla[contrato_nombre][mes] = row["total"]

    meses = sorted(meses, key=lambda m: (m.split()[1], list(month_name).index(m.split()[0])))

    return tabla, meses

def reporte_ingresos(request):
    distrito_id = request.GET.get("distrito_id")
    #print(distrito_id)
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    tabla, meses = get_tabla_ingresos(distrito_id, fecha_inicio, fecha_fin)
    distrito_nombre = Distrito.objects.get(id=distrito_id).nombre

    if request.method == "POST" and "btnReporte" in request.POST:
        return generar_ingresos_excel(tabla, meses, distrito_id, fecha_inicio, fecha_fin)

    context = {
        "tabla": tabla,
        "meses": meses,
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }
    return render(request, "rentabilidad/reporte_ingresos.html", context)

def generar_ingresos_excel(tabla, meses, distrito_id=None, fecha_inicio=None, fecha_fin=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ingresos"
    img_path = "static/images/logo_vordcab.jpg"
    img = Image(img_path)
    img.width = img.width * 1
    img.height = img.height * 1
    ws.add_image(img, "A1")
    ws.row_dimensions[1].height = 70 
    # Encabezado de filtros
    fila = 2
    if distrito_id:
        try:
            distrito_nombre = Distrito.objects.get(id=distrito_id).nombre
        except Distrito.DoesNotExist:
            distrito_nombre = distrito_id
        ws.cell(row=fila, column=1, value=f"Distrito: {distrito_nombre}")
        fila += 1
    if fecha_inicio and fecha_fin:
        ws.cell(row=fila, column=1, value=f"Rango de meses: {fecha_inicio} → {fecha_fin}")
        fila += 2  # dejar un espacio antes de la tabla

    # Crear estilo del encabezado
    head_style = NamedStyle(name="head_style")
    head_style.font = Font(name='Arial', color='00FFFFFF', bold=True, size=11)
    head_style.fill = PatternFill("solid", fgColor='00003366')
    if "head_style" not in wb.named_styles:
        wb.add_named_style(head_style)

    # Encabezados de tabla
    cell = ws.cell(row=fila, column=1, value="Contrato")
    cell.style = head_style
    for col_idx, mes in enumerate(meses, start=2):
        cell = ws.cell(row=fila, column=col_idx, value=mes)
        cell.style = head_style

    # Filas de datos
    for row_idx, (contrato, valores) in enumerate(tabla.items(), start=fila+1):
        ws.cell(row=row_idx, column=1, value=contrato)
        for col_idx, mes in enumerate(meses, start=2):
            ws.cell(row=row_idx, column=col_idx, value=valores.get(mes, 0))

    # Ajustar ancho columnas
    for i, col in enumerate(ws.columns, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = max(
            (len(str(cell.value)) for cell in col if cell.value), default=10
        ) + 2

    # Respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_ingresos.xlsx"'
    wb.save(response)
    return response

# Create your views here.
@perfil_seleccionado_required
def depreciaciones(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    depreciaciones = Depreciaciones.objects.filter(complete = True)
    #tipos = Tipo_Costo.objects.all()
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False)
    #myfilter= ContratoFilter(request.GET, queryset=contratos)

    #Set up pagination
    #p = Paginator(contratos, 10)
    #page = request.GET.get('page')
    #contratos_list = p.get_page(page)

    context = {
        'depreciaciones': depreciaciones,
        #'myfilter': myfilter,
        #'tipos': tipos,
        'distritos':distritos,
         }

    return render(request,'rentabilidad/depreciaciones.html', context)

def reporte_depreciacion(request, distrito_id):
    # Obtén todas las depreciaciones del distrito
    distrito_id = request.GET.get("distrito_id")
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    depreciaciones = Depreciaciones.objects.get(distrito__id = distrito_id, complete = True)
    # Genera la lista de meses en texto
    meses = []
    actual = fecha_inicio
    while actual <= fecha_fin:
        meses.append(actual.strftime("%b %Y"))  # Ejemplo: Ene 2025
        # avanzar un mes
        days_in_month = monthrange(actual.year, actual.month)[1]
        actual += timedelta(days=days_in_month)

    # Diccionario: { contrato: {mes: monto} }
    tabla = defaultdict(dict)

    for dep in depreciaciones:
        monto_mensual = dep.monto / dep.meses_a_depreciar
        inicio = date(dep.mes_inicial.year, dep.mes_inicial.month, 1)

        for i in range(dep.meses_a_depreciar):
            # Calcular el mes correspondiente
            year = inicio.year + (inicio.month - 1 + i) // 12
            month = (inicio.month - 1 + i) % 12 + 1
            fecha_mes = date(year, month, 1)

            mes_str = fecha_mes.strftime("%b %Y")

            if fecha_inicio <= fecha_mes <= fecha_fin:
                tabla[dep.contrato][mes_str] = f"${monto_mensual:,.2f}"

    context = {
        "distrito_nombre": depreciaciones.first().distrito.nombre if depreciaciones.exists() else "",
        "fecha_inicio": fecha_inicio.strftime("%b %Y"),
        "fecha_fin": fecha_fin.strftime("%b %Y"),
        "meses": meses,
        "tabla": tabla,
    }
    return render(request, "rentabilidad/reporte_depreciacion.html", context)

@perfil_seleccionado_required
def add_depreciacion(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    #monedas = Moneda.objects.exclude(id__in = [3] )
    depreciacion, created =  Depreciaciones.objects.get_or_create(created_by=usuario, complete = False)
    #depreciaciones = Ingresos.objects.filter(solicitud = solicitud)
    form = Depreciacion_Form()
    form.fields['distrito'].queryset = distritos
    #ingreso_form = Ingreso_Form()
    #ingreso_form.fields['moneda'].queryset = monedas

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            form = Depreciacion_Form(request.POST, instance = depreciacion)
            print('estou aqui')
            if form.is_valid():
                depreciacion = form.save(commit=False)
                depreciacion.created_at = date.today()
                depreciacion.complete = True
                depreciacion.save()
                messages.success(request,'Has agregado correctamente la Solicitud')
                return redirect('rentabilidad-depreciaciones')  
            else:
                print('Nao é valido')
                print(form.errors)  
        
                
 

    context = {
        'form': form,
        }

    return render(request,'rentabilidad/add_depreciaciones.html',context)