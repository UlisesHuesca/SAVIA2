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
from solicitudes.models import Contrato
from compras.models import Moneda
from user.decorators import perfil_seleccionado_required
from .forms import Costo_Form, Solicitud_Costo_Form, Solicitud_Ingreso_Form, Ingreso_Form, Depreciacion_Form, Solicitud_Costo_Indirecto_Form, Solicitud_Costo_Indirecto_Central_Form
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta



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
def add_costo(request, tipo):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]).exclude(status=False) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    solicitud, created =  Solicitud_Costos.objects.get_or_create(created_by=usuario, complete = False)
    costos = Costos.objects.filter(solicitud = solicitud)
    if tipo == "directo":
        form = Solicitud_Costo_Form()
        tipos = Tipo_Costo.objects.filter(id__in = [2,5])
        form.fields['tipo'].queryset = tipos
        form.fields['distrito'].queryset = distritos
    elif tipo == "indirecto":
        form = Solicitud_Costo_Indirecto_Form()
        tipos = Tipo_Costo.objects.filter(id__in = [3,4])
        form.fields['tipo'].queryset = tipos
        form.fields['distrito'].queryset = distritos
    elif tipo == "central":
        form = Solicitud_Costo_Indirecto_Central_Form()
        tipos = Tipo_Costo.objects.filter(id__in = [1])
    form.fields['tipo'].queryset = tipos
    form.fields['distrito'].queryset = distritos
    costo_form = Costo_Form()

    if request.method =='POST':
        if "btn_agregar" in request.POST:
            if tipo == "directo":
                form = Solicitud_Costo_Form(request.POST, instance = solicitud)
            elif tipo == "indirecto":
                form = Solicitud_Costo_Indirecto_Form(request.POST, instance = solicitud)
            elif tipo == "central":
                form = Solicitud_Costo_Indirecto_Central_Form(request.POSt, instance = solicitud)
            print('estou aqui')
            if form.is_valid():
                
                solicitud = form.save(commit=False)
                solicitud.created_at = date.today()
                if tipo == "central":
                    solicitud.distrito.nombre = "MATRIZ"
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
                return redirect('add-costo', tipo=tipo)
                
 

    context = {
        'tipo': tipo,
        'form': form,
        'costo_form': costo_form,
        'costos':costos,
        'solicitud':solicitud,
        }

    return render(request,'rentabilidad/add_costo.html',context)

@perfil_seleccionado_required
def delete_costo(request, tipo, pk):
    costo = Costos.objects.get(id=pk)
    messages.success(request,f'El costo {costo.concepto} ha sido eliminado exitosamente')
    costo.delete()

    return redirect('add-costo', tipo=tipo)


def reporte_costos(request):
    tipo_id = request.GET.get("tipo_id")  # <- capturamos el valor del select
    distrito_id = request.GET.get("distrito_id", 1)  # puedes hacerlo dinámico también
    print(tipo_id)
    if int(tipo_id) == 1:
        distrito_id = 6
        
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

def get_tabla_ingresos_contrato(fecha_inicio=None, fecha_fin=None):
    ingresos = Ingresos.objects.all()

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m").date()
            y, m = [int(x) for x in fecha_fin.split("-")]
            last_day = monthrange(y, m)[1]
            fecha_fin = date(y, m, last_day)
            ingresos = ingresos.filter(solicitud__fecha__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass

    # Totales por contrato y mes
    data = (
        ingresos.annotate(mes=TruncMonth("solicitud__fecha"))
        .values("contrato_id", "contrato__nombre", "mes")
        .annotate(total=Sum("monto"))
        .order_by("contrato__nombre", "mes")
    )

    tabla = {}
    meses = set()
    for row in data:
        contrato_id = row["contrato_id"]
        contrato_nombre = row["contrato__nombre"]
        mes = row["mes"].strftime("%B %Y")
        meses.add(mes)

        year, month = row["mes"].year, row["mes"].month
        prorrateo = calcular_prorrateo_contrato(contrato_id, year, month)

        if contrato_nombre not in tabla:
            tabla[contrato_nombre] = {}

        tabla[contrato_nombre][mes] = {
            "monto": row["total"],
            "prorrateo": round(prorrateo * 100, 2)
        }

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

def reporte_ingresos_contrato(request):
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    tabla, meses = get_tabla_ingresos_contrato(fecha_inicio, fecha_fin)

    if request.method == "POST" and "btnReporte" in request.POST:
        return generar_ingresos_excel(tabla, meses, None, fecha_inicio, fecha_fin)

    context = {
        "tabla": tabla,
        "meses": meses,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }
    return render(request, "rentabilidad/reporte_ingresos_contrato.html", context)



def calcular_prorrateo_contrato(contrato, year, month):
    """Devuelve la participación del contrato en el total de ingresos del mes."""
    total_mes = Ingresos.objects.filter(
        fecha__year=year, fecha__month=month
    ).aggregate(total=Sum('monto'))['total'] or 0

    total_contrato = Ingresos.objects.filter(
        contrato=contrato, fecha__year=year, fecha__month=month
    ).aggregate(total=Sum('monto'))['total'] or 0

    if total_mes == 0:
        return 0

    return total_contrato / total_mes


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


def reporte_depreciaciones(request):
    distrito_id = request.GET.get("distrito_id")
    fecha_inicio = request.GET.get("fecha_inicio")   # "YYYY-MM"
    fecha_fin = request.GET.get("fecha_fin")         # "YYYY-MM"
    # fecha de "hoy" (puede ser corte contable o date.today())
    hoy = date.today()
    mes_corte = date(hoy.year, hoy.month, 1)

    # 1) Parseo de fechas como en tus otros reportes
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m").date()
            y, m = [int(x) for x in fecha_fin.split("-")]
            last_day = monthrange(y, m)[1]
            fecha_fin = date(y, m, last_day)
        except ValueError:
            fecha_inicio = fecha_fin = None

    # 2) Query de depreciaciones del distrito
    depreciaciones = Depreciaciones.objects.filter(
        distrito__id=distrito_id, complete=True
    )

    # 3) Meses (claves internas y etiquetas visibles)
    meses = []
    meses_formateados = {}
    if fecha_inicio and fecha_fin:
        actual = fecha_inicio
        while actual <= fecha_fin:
            key = actual.strftime("%Y-%m")       # clave interna (estable)
            label = actual.strftime("%b %Y")     # etiqueta visible (cabecera)
            meses.append(key)
            meses_formateados[key] = label
            # avanzar un mes completo
            days_in_month = monthrange(actual.year, actual.month)[1]
            actual += timedelta(days=days_in_month)


    # 4) Tabla: { "Contrato" : { "Concepto" : { "YYYY-MM": "$1,234.00" } } }
    tabla = defaultdict(lambda: defaultdict(dict))
    remanentes = defaultdict(dict)

    for dep in depreciaciones:
        meses_dep = dep.meses_a_depreciar or 1
        monto_mensual = dep.monto / meses_dep
        monto_total = dep.monto


        inicio = date(dep.mes_inicial.year, dep.mes_inicial.month, 1)
        # ✅ meses transcurridos INCLUYENDO el mes actual
        meses_trans = _months_inclusive(inicio, mes_corte)
        # no puede exceder los meses a depreciar
        meses_trans = min(meses_trans, meses_dep)
        remanente = monto_total - (meses_trans * monto_mensual)
        contrato_nombre = getattr(dep.contrato, "nombre", str(dep.contrato))
        concepto = dep.concepto or "Sin concepto"
        remanentes[contrato_nombre][concepto] = f"${remanente:,.2f}"

        for i in range(meses_dep):
            year = inicio.year + (inicio.month - 1 + i) // 12
            month = (inicio.month - 1 + i) % 12 + 1
            fecha_mes = date(year, month, 1)
            key = fecha_mes.strftime("%Y-%m")

            if fecha_inicio and fecha_fin and fecha_inicio <= fecha_mes <= fecha_fin:
                contrato_nombre = getattr(dep.contrato, "nombre", str(dep.contrato))
                concepto = dep.concepto or "Sin concepto"

                tabla[contrato_nombre][concepto][key] = f"${monto_mensual:,.2f}"

    # 5) Contexto
    distrito_nombre = ""
    first_dep = depreciaciones.first()
    if first_dep and first_dep.distrito:
        distrito_nombre = first_dep.distrito.nombre

    tabla_dict = {
    str(contrato): {
        str(concepto): dict(valores)         # dict() para el tercer nivel
        for concepto, valores in sorted(conceptos.items(), key=lambda x: x[0])
    }
    for contrato, conceptos in sorted(tabla.items(), key=lambda x: x[0])
    }

    totales = {mes: 0 for mes in meses}

    for contrato, conceptos in tabla_dict.items():
        for concepto, valores in conceptos.items():
            for mes in meses:
                if mes in valores:
                    # quitar $ y comas, convertir a float
                    monto = float(valores[mes].replace("$", "").replace(",", ""))
                    totales[mes] += monto

    # Convertir de nuevo a string formateado
    totales_fmt = {mes: f"${totales[mes]:,.2f}" for mes in meses}

      # 🔑 calcular remanente
    #diferencia = relativedelta(mes_actual, inicio)
    #meses_transcurridos = diferencia.years * 12 + diferencia.months
    #if meses_transcurridos > meses_dep:
    #    meses_transcurridos = meses_dep

    #remanente = monto_total - (meses_transcurridos * monto_mensual)
    #contrato_nombre = getattr(dep.contrato, "nombre", str(dep.contrato))
    #concepto = dep.concepto or "Sin concepto"
    

    if request.method == "POST" and "btnReporte" in request.POST:
        return generar_depreciaciones_excel(tabla, meses, remanentes, distrito_id, fecha_inicio, fecha_fin)
    
    context = {
        "distrito_nombre": distrito_nombre,
        "fecha_inicio": fecha_inicio.strftime("%b %Y") if fecha_inicio else "",
        "fecha_fin": fecha_fin.strftime("%b %Y") if fecha_fin else "",
        "meses": meses,
        "meses_formateados": meses_formateados,
        "tabla": tabla_dict,   # 👈 ya no uses dict(sorted(...)) sobre el defaultdict original
        "totales": totales_fmt,   # 👈 aquí van los totales
        "remanentes": dict(remanentes),
    }
    return render(request, "rentabilidad/reporte_depreciaciones.html", context)


def _months_inclusive(start_month: date, current_month: date) -> int:
    """Meses entre start y current INCLUYENDO el mes actual.
       Si current < start, regresa 0."""
    if current_month < start_month:
        return 0
    return (current_month.year - start_month.year) * 12 + (current_month.month - start_month.month) + 1

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


def generar_depreciaciones_excel(tabla, meses, remanentes, distrito_id=None, fecha_inicio=None, fecha_fin=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Depreciaciones"

    money_style = NamedStyle(name="money_style")
    money_style.number_format = u'"$"#,##0.00'   # 👈 formato moneda
    money_style.font = Font(name="Calibri", size=10)
    wb.add_named_style(money_style)

    # Logo
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

    # Estilo encabezado
    head_style = NamedStyle(name="head_style")
    head_style.font = Font(name='Arial', color='00FFFFFF', bold=True, size=11)
    head_style.fill = PatternFill("solid", fgColor='00003366')
    if "head_style" not in wb.named_styles:
        wb.add_named_style(head_style)

    # Encabezados de tabla
    ws.cell(row=fila, column=1, value="Contrato / Concepto").style = head_style
    for col_idx, mes in enumerate(meses, start=2):
        ws.cell(row=fila, column=col_idx, value=mes).style = head_style
    ws.cell(row=fila, column=len(meses)+2, value="Remanente").style = head_style
    # Filas de datos
    row_idx = fila + 1
    for contrato, conceptos in tabla.items():
        # Fila contrato
        ws.cell(row=row_idx, column=1, value=contrato).font = Font(bold=True)
        row_idx += 1

        for concepto, valores in conceptos.items():
            ws.cell(row=row_idx, column=1, value=concepto)
            for col_idx, mes in enumerate(meses, start=2):
                monto_str = valores.get(mes, 0)
                try:
                    # quitar $ y comas si es string
                    monto = float(str(monto_str).replace("$", "").replace(",", ""))
                except:
                    monto = 0
                cell = ws.cell(row=row_idx, column=col_idx, value=monto)
                cell.style = money_style   # 👈 formato moneda

            # 👉 Columna de remanente
            rem_str = remanentes.get(contrato, {}).get(concepto, 0)
            try:
                rem = float(str(rem_str).replace("$", "").replace(",", ""))
            except:
                rem = 0
            rem_cell = ws.cell(row=row_idx, column=len(meses)+2, value=rem)
            rem_cell.style = money_style
            row_idx += 1

    ws.cell(row=row_idx, column=1, value="TOTAL").font = Font(bold=True)

    for col_idx, mes in enumerate(meses, start=2):
        # Calculamos el rango desde la primera fila de datos hasta la fila anterior
        col_letter = get_column_letter(col_idx)
        start_row = fila + 1   # justo después de los encabezados
        end_row = row_idx - 1  # última fila antes del total
        formula = f"=SUM({col_letter}{start_row}:{col_letter}{end_row})"

        cell = ws.cell(row=row_idx, column=col_idx, value=formula)
        cell.style = money_style
        cell.font = Font(bold=True)

    # 👉 Columna de remanente total (puede ser suma también)
    col_letter = get_column_letter(len(meses)+2)
    start_row = fila + 1
    end_row = row_idx - 1
    formula = f"=SUM({col_letter}{start_row}:{col_letter}{end_row})"
    cell = ws.cell(row=row_idx, column=len(meses)+2, value=formula)
    cell.style = money_style
    cell.font = Font(bold=True)

     # Ajustar anchos
    for i, col in enumerate(ws.columns, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = max(
            (len(str(cell.value)) for cell in col if cell.value), default=10
        ) + 2

    # Respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_depreciaciones.xlsx"'
    wb.save(response)
    return response



def reporte_rentabilidad_mensual(request):
    distrito_id = request.GET.get("distrito_id")
    mes_anio = request.GET.get("mes_anio")  # formato YYYY-MM

    contratos_data = []
    totales = {
        "ingresos": 0,
        "depreciaciones": 0,
        "rentabilidad": 0,
    }
    tipos_costos_totales = {}  # acumulados por tipo de costo

    distrito_nombre = ""
    fecha_label = ""

    if distrito_id and mes_anio:
        try:
            y, m = [int(x) for x in mes_anio.split("-")]
            fecha_mes = date(y, m, 1)
            fecha_label = fecha_mes.strftime("%B %Y")
        except ValueError:
            fecha_mes = None

        if fecha_mes:
            try:
                distrito_nombre = Distrito.objects.get(id=distrito_id).nombre
            except Distrito.DoesNotExist:
                distrito_nombre = "?"

            # Obtener todos los contratos que tienen algo en ese mes
            contratos = (
                Contrato.objects.filter(
                    sc_contratos__distrito__id=distrito_id,
                    sc_contratos__fecha__year=y,
                    sc_contratos__fecha__month=m,
                )
                .distinct()
            )

            for contrato in contratos:
                row = {
                    "contrato": contrato.nombre or str(contrato),
                    "ingresos": 0,
                    "depreciaciones": 0,
                    "tipos_costos": {},  # cada tipo de costo → monto
                    "rentabilidad": 0,
                }

                # Ingresos
                row["ingresos"] = (
                    Ingresos.objects.filter(
                        solicitud__distrito__id=distrito_id,
                        contrato=contrato,
                        solicitud__fecha__year=y,
                        solicitud__fecha__month=m,
                    ).aggregate(total=Sum("monto"))["total"] or 0
                )

                # Costos agrupados por tipo
                costos = (
                    Costos.objects.filter(
                        solicitud__distrito__id=distrito_id,
                        solicitud__contrato=contrato,
                        solicitud__fecha__year=y,
                        solicitud__fecha__month=m,
                    )
                    .values("solicitud__tipo__nombre")
                    .annotate(total=Sum("monto"))
                )

                for c in costos:
                    tipo = c["solicitud__tipo__nombre"] or "Sin tipo"
                    monto = c["total"] or 0
                    row["tipos_costos"][tipo] = monto

                    # acumular totales globales por tipo
                    tipos_costos_totales[tipo] = (
                        tipos_costos_totales.get(tipo, 0) + monto
                    )

                # Depreciaciones
                depreciaciones_total = 0
                depreciaciones = Depreciaciones.objects.filter(
                    contrato=contrato, distrito__id=distrito_id, complete=True
                )
                for dep in depreciaciones:
                    meses_dep = dep.meses_a_depreciar or 1
                    monto_mensual = dep.monto / meses_dep
                    inicio = date(dep.mes_inicial.year, dep.mes_inicial.month, 1)
                    for i in range(meses_dep):
                        year = inicio.year + (inicio.month - 1 + i) // 12
                        month = (inicio.month - 1 + i) % 12 + 1
                        fecha_iter = date(year, month, 1)
                        if fecha_iter == fecha_mes:
                            depreciaciones_total += monto_mensual
                            break
                row["depreciaciones"] = depreciaciones_total

                # Rentabilidad
                row["rentabilidad"] = (
                    row["ingresos"]
                    - sum(row["tipos_costos"].values())
                    - row["depreciaciones"]
                )

                contratos_data.append(row)

                # Totales
                totales["ingresos"] += row["ingresos"]
                totales["depreciaciones"] += row["depreciaciones"]
                totales["rentabilidad"] += row["rentabilidad"]

    
        # 👉 Si el usuario pidió Excel
    if request.method == "POST" and "btnReporte" in request.POST:
        return generar_rentabilidad_excel(contratos_data=contratos_data, tipos_costos_totales=tipos_costos_totales, 
                                          distrito_id=distrito_id, mes_anio=mes_anio, fecha_label=fecha_label)


    context = {
        "distritos": Distrito.objects.exclude(id__in=[7, 8, 16]).exclude(status=False),
        "distrito_id": distrito_id,
        "distrito_nombre": distrito_nombre,
        "mes_anio": mes_anio,
        "fecha_label": fecha_label,
        "contratos_data": contratos_data,
        "totales": totales,
        "tipos_costos_totales": tipos_costos_totales,  # para la fila final
    }
    return render(request, "rentabilidad/rentabilidad.html", context)

def generar_rentabilidad_excel(contratos_data, tipos_costos_totales, distrito_id=None, mes_anio=None, fecha_label=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rentabilidad"

    # Estilo moneda
    money_style = NamedStyle(name="money_style")
    money_style.number_format = u'"$"#,##0.00'
    money_style.font = Font(name="Calibri", size=10)
    if "money_style" not in wb.named_styles:
        wb.add_named_style(money_style)

    # Logo
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
    if fecha_label:
        ws.cell(row=fila, column=1, value=f"Mes: {fecha_label}")
        fila += 2

    # Estilo encabezado
    head_style = NamedStyle(name="head_style")
    head_style.font = Font(name='Arial', color='00FFFFFF', bold=True, size=11)
    head_style.fill = PatternFill("solid", fgColor='00003366')
    if "head_style" not in wb.named_styles:
        wb.add_named_style(head_style)

    # 👉 Encabezados dinámicos
    col_idx = 1
    ws.cell(row=fila, column=col_idx, value="Contrato").style = head_style
    col_idx += 1
    ws.cell(row=fila, column=col_idx, value="Ingresos").style = head_style
    col_idx += 1

    # Tipos de costos en columnas
    tipos_order = list(tipos_costos_totales.keys())
    for tipo in tipos_order:
        ws.cell(row=fila, column=col_idx, value=tipo).style = head_style
        col_idx += 1

    ws.cell(row=fila, column=col_idx, value="Amortización").style = head_style
    col_idx += 1
    ws.cell(row=fila, column=col_idx, value="Rentabilidad").style = head_style

    # 👉 Filas de datos
    row_idx = fila + 1
    for row in contratos_data:
        col = 1
        ws.cell(row=row_idx, column=col, value=row["contrato"])
        col += 1

        # Ingresos
        cell = ws.cell(row=row_idx, column=col, value=row["ingresos"])
        cell.style = money_style
        col += 1

        # Costos por tipo (si no existe en contrato → 0)
        for tipo in tipos_order:
            monto = row["tipos_costos"].get(tipo, 0)
            cell = ws.cell(row=row_idx, column=col, value=monto)
            cell.style = money_style
            col += 1

        # Depreciaciones
        cell = ws.cell(row=row_idx, column=col, value=row["depreciaciones"])
        cell.style = money_style
        col += 1

        # Rentabilidad
        cell = ws.cell(row=row_idx, column=col, value=row["rentabilidad"])
        cell.style = money_style
        col += 1

        row_idx += 1

    # 👉 Totales con fórmula
    ws.cell(row=row_idx, column=1, value="TOTAL").font = Font(bold=True)
    for col in range(2, len(tipos_order) + 5):  # ingresos + tipos + amortización + rentabilidad
        col_letter = get_column_letter(col)
        start_row = fila + 1
        end_row = row_idx - 1
        formula = f"=SUM({col_letter}{start_row}:{col_letter}{end_row})"
        cell = ws.cell(row=row_idx, column=col, value=formula)
        cell.style = money_style
        cell.font = Font(bold=True)

    # Ajustar anchos
    for i, col in enumerate(ws.columns, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = max(
            (len(str(cell.value)) for cell in col if cell.value), default=10
        ) + 2

    # Respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_rentabilidad.xlsx"'
    wb.save(response)
    return response


