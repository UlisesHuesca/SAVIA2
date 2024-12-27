from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import Inventario, Profile, Marca 
from django.core import serializers
from django.db.models import Value, F, Q
from django.db.models.functions import Concat
from dashboard.models import Activo, Marca, Tipo_Activo
from requisiciones.models import Salidas 
from .forms import Activo_Form, Edit_Activo_Form, UpdateResponsableForm, SalidasActivoForm, MarcaForm, Tipo_ActivoForm
from django.contrib import messages
from activos.filters import ActivoFilter
from django.http import JsonResponse, HttpResponse, FileResponse
from django.http import Http404
from dashboard.models import Product
from django.core.paginator import Paginator
from solicitudes.filters import InventarioFilter
from django.db.models import Count
from django.db.models import Count, Sum


#Todo para construir el código QR
import qrcode
import io
from io import BytesIO
import datetime as dt
from datetime import date, datetime, timedelta
import json
#Excel
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

#PDF generator
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import Color, black, blue, red, white
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import letter, portrait
from reportlab.rl_config import defaultPageSize 
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from bs4 import BeautifulSoup
from user.decorators import perfil_seleccionado_required

# Create your views here.
@login_required(login_url='user-login')
@perfil_seleccionado_required
def activos(request):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    if usuario.tipo.nombre == "ADMIN_ACTIVOS":
        activos = Activo.objects.filter(completo=True).exclude(responsable__distritos__id__in=[7, 8])
    else:    
        activos = Activo.objects.filter(Q(responsable__distritos = usuario.distritos)|Q(activo__distrito = usuario.distritos), completo=True)
    myfilter = ActivoFilter(request.GET, queryset=activos)
    activos = myfilter.qs 

    if request.method == "POST" and 'btnExcel' in request.POST:
        return convert_activos_to_xls(activos)

    context = {
        'activos':activos,
        'myfilter': myfilter,
        'usuario': usuario,
    }

    return render(request,'activos/activos.html',context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def add_activo(request):
    #perfil = Profile.objects.get(staff__id=request.user.id)
    pk_perfil = request.session.get('selected_profile_id') 
    perfil = Profile.objects.get(id = pk_perfil)
    #activos = Activo.objects.filter(completo=True)
    #productos = Inventario.objects.filter(producto__activo=True, distrito = perfil.distritos, cantidad__gte=1)  # Filtra por cantidad mayor o igual a 1
    productos = Inventario.objects.filter(producto__activo=True, distrito = perfil.distritos)
    personal = Profile.objects.all()
    marcas = Marca.objects.all()
    tipo_activo = Tipo_Activo.objects.all() 
    #print(productos)
    if perfil.tipo.nombre == "ADMIN_ACTIVOS":
        responsables = personal.filter(st_activo = True)
    else:
        responsables = personal.filter(distritos = perfil.distritos, st_activo = True)

    responsables_para_select2 = [
        {
            'id': responsable.id, 
            'text': str(responsable.staff.staff.first_name) + (' ') + str(responsable.staff.staff.last_name)
        } for responsable in responsables
    ]
    tipo_activo_para_select2 = [
        {'id': tipo.id, 'text': tipo.nombre}
        for tipo in tipo_activo
    ]

    marca_para_select2 = [
        {'id': marca.id, 'text': marca.nombre}
        for marca in marcas
    ]

    for producto in productos: #Asignar al producto que es un activo disponible si tiene más de 1
        if producto.cantidad >= 1:
            producto.activo_disponible = True
        else:
            producto.activo_disponible = False
        producto.save()         
            
    activo, created = Activo.objects.get_or_create(creado_por=perfil, completo=False)
    productos_activos = productos.filter(activo_disponible =True) #Filtrar a aquellos productos activo disponibles
    #print(productos_activos)
    form = Activo_Form(instance = activo)

    form.fields['activo'].queryset = productos_activos

    if request.method =='POST':
        form = Activo_Form(request.POST, request.FILES, instance = activo)
        messages.success(request,f'Has agregado incorrectamente el activo')
        if form.is_valid():
            activo = form.save(commit=False)
            activo.completo = True
            activo.estatus.nombre = "ALTA"
            activo.activo.cantidad -= 1 #Restar uno al inventario
            activo.activo.cantidad_entradas -= 1 
            activo.activo.save()  # Guarda el cambio en el inventario
            activo.save()
            messages.success(request,f'Has agregado correctamente el activo {activo.eco_unidad}')
            return redirect('activos')
        else:
            messages.error(request, 'Hubo un error al agregar el activo.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            #messages.success(request,'No está validando')
    
    context = {
        'responsables_para_select2':responsables_para_select2,
        'tipo_activo_para_select2': tipo_activo_para_select2,
        'marca_para_select2': marca_para_select2,
        'marcas': marcas,
        'form':form,
        'productos_activos':productos_activos,
    }

    return render(request,'activos/add_activos.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def add_activo2(request, pk):
    personal = Profile.objects.all()
    pk_perfil = request.session.get('selected_profile_id') 
    perfil = Profile.objects.get(id = pk_perfil)
    producto_salida = Salidas.objects.get(id=pk)
    perfil_salida = producto_salida.vale_salida.material_recibido_por
    inventarios = Inventario.objects.all()
    producto = inventarios.get(producto = producto_salida.producto.articulos.producto.producto)
    
    marcas = Marca.objects.all() 
    #print(producto)


    productos = inventarios.filter(producto = producto_salida.producto.articulos.producto.producto, distrito = perfil.distritos)
    producto.activo_disponible = True
    activos_completos = Activo.objects.filter(activo=producto, completo = True)
    #ecos = activos_completos.values_list('eco_unidad', flat=True)
    if perfil.tipo.nombre == "ADMIN_ACTIVOS":
        responsables = personal.filter(st_activo = True)
    else:
        responsables = personal.filter(distritos = perfil.distritos, st_activo = True)
    responsables_para_select2 = [
        {
            'id': responsable.id, 
            'text': str(responsable.staff.staff.first_name) + (' ') + str(responsable.staff.staff.last_name)
        } for responsable in responsables
    ]
       
    #eco_choices = [(eco, eco) for eco in ecos]
    activo_cont = activos_completos.count()
    existencia = producto.cantidad + producto.cantidad_apartada + producto_salida.cantidad 
    #print(ecos)
    #print(existencia)
    if activo_cont == existencia and activo_cont > 0: # Si el número de activos es igual a la existencia en inventario
        producto.activo_disponible = False
        # Obtén los activos que son completos
        #activos_completos = Activo.objects.filter(completo=True, activo=producto)
        
        
        # Crear una lista para almacenar los diccionarios
        activos_completos_list = []

        # Recorrer la queryset
        for activo in activos_completos:
            # Crear un diccionario para este activo
            activo_dict = {
                'id': activo.id,
                'fields':{
                    'activo': str(activo.activo),
                    'tipo_activo': str(activo.tipo_activo),
                    'responsable': str(activo.responsable.staff.first_name) + ' ' + str(activo.responsable.staff.last_name),
                    'creado_por': str(activo.creado_por.staff.first_name) + ' ' + str(activo.creado_por.staff.last_name),
                    'eco_unidad': activo.eco_unidad,
                    'serie': activo.serie,
                    'cuenta_contable': activo.cuenta_contable,
                    'factura_interna': activo.factura_interna,
                    'descripcion': activo.descripcion,
                    'marca': str(activo.marca),
                    'modelo': activo.modelo,
                    'comentario': activo.comentario,
                    'completo': activo.completo
                }
            }
            # Agregar el diccionario a la lista
            activos_completos_list.append(activo_dict)
        # Convertir la lista a JSON
        activos_completos_json = json.dumps(activos_completos_list)
        #print(activos_completos_json)

        form = UpdateResponsableForm()
        #form.fields['responsable'].queryset = perfil_salida
    
        if request.method == 'POST':
            id = int(request.POST['hidden_activo'])
            # Ahora puedes usar activo_id para obtener el objeto Activo
            activo = Activo.objects.get(id=id)
            form = UpdateResponsableForm(request.POST,instance=activo)
            if form.is_valid():
                producto_salida.validacion_activos = True
                activo = form.save(commit=False)
                activo.responsable = perfil_salida
                activo.save()
                producto_salida.save()
                messages.success(request,'Responsable actualizado con éxito')
                return redirect('matriz-salida-activos')
            else:
                messages.error(request,'Es necesario cambiar el comentario, favor de dar doble click en el recuadro azul')

        context = {
            'perfil_salida':perfil_salida,
            'personal': personal,
            'activos':activos_completos,
            'marcas': marcas,
            'form': form,
            'activos_completos_json': activos_completos_json,
            'responsables_para_select2': responsables_para_select2,
        }

    else:
        activo, created = Activo.objects.get_or_create(creado_por=perfil, completo=False, activo = producto)

        form = Activo_Form(instance = activo)
        form.fields['activo'].queryset = productos

        if request.method =='POST':
            form = Activo_Form(request.POST, instance = activo)
            if form.is_valid():
                activo = form.save(commit=False)
                producto_salida.validacion_activos = True
                activo.completo = True
                activo.save()
                producto_salida.save()
                messages.success(request,f'Has agregado correctamente el activo {activo.eco_unidad}')
                return redirect('matriz-salida-activos')
            else:
                print(form.errors) 
                messages.success(request,'No está validando')

        context = {
            'personal':personal,
            'marcas':marcas,
            'form':form,
            'responsables_para_select2': responsables_para_select2,
        }

    return render(request,'activos/add_activos.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def edit_activo(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    empleados = Profile.objects.all()
    perfil = empleados.get(id = pk_perfil)
    productos = Inventario.objects.filter(producto__activo=True, distrito = perfil.distritos)

    for producto in productos: #Asignar al producto que es un activo disponible si tiene más de 1
        if producto.cantidad >= 1:
            producto.activo_disponible = True
        else:
            producto.activo_disponible = False
        producto.save()  

    #producto = Salidas.objects.get(id=pk)
    activo = Activo.objects.get(id=pk)
    if activo.activo is None:
        familia = 'Sin producto asociado'
        subfamilia = ''
    else:
        familia = activo.activo.producto.familia.nombre
        if activo.activo.producto.subfamilia:
            subfamilia = activo.activo.producto.subfamilia.nombre
        else:
            subfamilia = ''
    tipo_activo = Tipo_Activo.objects.all()
    if activo.responsable:
        responsable = empleados.get(id=activo.responsable.id )
    if perfil.tipo.nombre == "ADMIN_ACTIVOS":
        responsables = empleados.filter(st_activo = True)
    else:
        responsables = empleados.filter(distritos = perfil.distritos, st_activo = True)
    marcas = Marca.objects.all() 
    if activo.marca:
        marca_p = marcas.get(id = activo.marca.id)
    else:
        marca_p = None

    productos_activos = productos.filter(activo_disponible =True) #Filtrar a aquellos productos activo disponibles
    form = Edit_Activo_Form(instance = activo)
    form.fields['activo'].queryset = productos_activos

    productos_para_select2 = [
        {
            'id': producto.id, 
            'text': str(producto.producto.nombre)
        } for producto in productos_activos
    ]
    if activo.activo:
        producto_predeterminado = {
            'id': activo.activo.id, 
            'text': str(activo.activo.producto.nombre)
        }
    else:
        producto_predeterminado = None



    responsables_para_select2 = [
        {
            'id': responsable.id, 
            'text': str(responsable.staff.staff.first_name) + (' ') + str(responsable.staff.staff.last_name)
        } for responsable in responsables
    ]

    if activo.responsable:
        responsable_predeterminado = {
            'id': activo.responsable.id,
            'text': f"{activo.responsable.staff.staff.first_name} {activo.responsable.staff.staff.last_name}"
        }
    else:
        responsable_predeterminado = None
    
    if marca_p != None:
        marca_predeterminada = {
            'id': marca_p.id,
            'text': marca_p.nombre
        }
    else:
        marca_predeterminada = 'null'
    
    marcas_para_select2 = [
        {
            'id': marca.id, 
            'text': marca.nombre if marca.nombre is not None else "",
        } for marca in marcas
    ]
    # Obtiene los tipos de activo para select2
    tipo_activo_para_select2 = [
        {'id': tipo.id, 'text': tipo.nombre}
        for tipo in tipo_activo
    ]

    # Obtiene el tipo de activo predeterminado
    if activo.tipo_activo:
        tipo_activo_predeterminado = {
            'id': activo.tipo_activo.id,
            'text': activo.tipo_activo.nombre
        }
    else:
        tipo_activo_predeterminado = None

    error_messages = {}    

    if request.method =='POST':
        form = Edit_Activo_Form(request.POST, request.FILES, instance = activo)
        if form.is_valid():
            activo = form.save(commit=False)
            activo.completo = True
            activo.modified_at = date.today()
            activo.modified_by = perfil
            activo.save()
            messages.success(request,f'Has modificado correctamente el activo {activo.eco_unidad}')
            return redirect('activos')
        else:
            for field, errors in form.errors.items():
                error_messages[field] = errors.as_text()



    context = {
        'error_messages': error_messages,
        'responsable_predeterminado':responsable_predeterminado,
        'responsables_para_select2':responsables_para_select2,
        'productos_para_select2':productos_para_select2,
        'producto_predeterminado':producto_predeterminado,
        'marcas_para_select2':marcas_para_select2,
        'marca_predeterminada':marca_predeterminada,
        'tipo_activo_predeterminado': tipo_activo_predeterminado,
        'tipo_activo_para_select2': tipo_activo_para_select2,
        'activo':activo,
        #'personal':personal,
        'marcas':marcas,
        'form':form,
        'familia':familia,
        'subfamilia':subfamilia,
    }

    return render(request,'activos/edit_activos.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def asignar_activo(request, pk):
    salida = Salidas.objects.get(id=pk)
    activos = Activo.objects.filter(activo = salida.producto.articulos.producto, completo=True)

    activos_completos_list = []

    for activo in activos:
        # Crear un diccionario para este activo
        activo_dict = {
            'id': activo.id,
            'fields':{
                'activo': str(activo.activo),
                'tipo_activo': str(activo.tipo_activo.nombre),
                'creado_por': str(activo.creado_por.staff.first_name) + ' ' + str(activo.creado_por.staff.last_name),
                'eco_unidad': activo.eco_unidad,
                'serie': activo.serie,
                'cuenta_contable': activo.cuenta_contable,
                'factura_interna': activo.factura_interna,
                'descripcion': activo.descripcion,
                'marca': str(activo.marca),
                'modelo': activo.modelo,
                'comentario': activo.comentario,
                'completo': activo.completo
            }
        }

        
        # Agregar el diccionario a la lista
        activos_completos_list.append(activo_dict)
        # Convertir la lista a JSON
    activos_completos_json = json.dumps(activos_completos_list)

    form = SalidasActivoForm(instance=salida)

    if request.method =='POST':
            form = SalidasActivoForm(request.POST, instance=salida)
            if form.is_valid():
                salida = form.save(commit=False)
                salida.validacion_activos = True
                salida = form.save()
                activo = Activo.objects.get(id = salida.activo.id)
                activo.responsable = salida.vale_salida.material_recibido_por
                activo.save()
                messages.success(request,f'El activo {activo.eco_unidad} ha sido asignado')
                return redirect('activos')
            else:
                print(form.errors) 
                messages.success(request,'No está validando')


    context = {
        'form':form,
        'activos':activos,
        'salida':salida,
        'activos_completos_json':activos_completos_json,
    }

    return render(request, 'activos/asignar_activo.html',context)




def generate_qr(request, pk):
    # Obtén el activo por la llave primaria
    activo = Activo.objects.get(pk=pk)
    
    # Construye la data del QR. Puedes cambiar esto para adaptarlo a tus necesidades.
    qr_data = f"""
    Eco_Unidad: {activo.nombre}
    Tipo: {activo.tipo_activo}
    Descripción: {activo.descripcion}
    Marca: {activo.marca}
    Modelo: {activo.modelo}
    Responsable: {activo.responsable.staff.staff.first_name} {activo.responsable.staff.staff.last_name}
    Serie: {activo.serie}
    Comentario: {activo.comentario}
    """

    # Genera el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    response = BytesIO()
    img.save(response, 'PNG')
    response.seek(0)
    
    return FileResponse(response, as_attachment=True, filename='qr.png')

def convert_activos_to_xls(activos):
      #print('si entra a la función')
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

    columns = ['Eco','Producto','Familia','Subfamilia', 'Responsable', 'Tipo Activo', 'Serie', 'Marca', 'Modelo', 'Descripción', 'Status']

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA 2.0. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    #worksheet.set_column('L:L', 12,  money_style)
    #worksheet.set_column('M:M', 12, money_style) 
    
    row_num = 0
    for activo in activos:
        if activo.activo is None:
            familia = 'Sin producto asociado'
            subfamilia = ''
        else:
            familia = activo.activo.producto.familia.nombre
            if activo.activo.producto.subfamilia:
                subfamilia = activo.activo.producto.subfamilia.nombre
            else:
                subfamilia = ''
        row_num += 1
        # Aquí asumimos que ya hiciste el procesamiento necesario de cada compra
        #pagos = Pago.objects.filter(oc=compra_list)
        #tipo_de_cambio_promedio_pagos = pagos.aggregate(Avg('tipo_de_cambio'))['tipo_de_cambio__avg']

        # Usar el tipo de cambio de los pagos, si existe. De lo contrario, usar el tipo de cambio de la compra
        #tipo = tipo_de_cambio_promedio_pagos or compra_list.tipo_de_cambio
        #tipo_de_cambio = '' if tipo == 0 else tipo
        #created_at = compra_list.created_at.replace(tzinfo=None)
        #approved_at = compra_list.req.approved_at

        row = [
            activo.eco_unidad,
            activo.activo.producto.nombre if activo.activo else " ",
            familia,
            subfamilia,
            f"{activo.responsable.staff.staff.first_name} {activo.responsable.staff.staff.last_name}",
            activo.tipo_activo.nombre,
            activo.serie,
            activo.marca.nombre if activo.marca else " ",
            activo.modelo,
            activo.descripcion,
            activo.estatus.nombre
        ]
        
        for col_num, cell_value in enumerate(row):
        # Define el formato por defecto
            cell_format = body_style

            # Aplica el formato de fecha para las columnas con fechas
            #if col_num in [7, 8]:  # Asume que estas son tus columnas de fechas
            #    cell_format = date_style
        
            # Aplica el formato de dinero para las columnas con valores monetarios
            #elif col_num in [11, 12]:  # Asume que estas son tus columnas de dinero
            #    cell_format = money_style

            # Finalmente, escribe la celda con el valor y el formato correspondiente
            worksheet.write(row_num, col_num, cell_value, cell_format)

      
        #worksheet.write_formula(row_num, 19, f'=IF(ISBLANK(R{row_num+1}), L{row_num+1}, L{row_num+1}*R{row_num+1})', money_style)
    
   
    workbook.close()

    # Construye la respuesta
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename=Matriz_compras_{dt.date.today()}.xlsx'
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('descarga_iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    output.close()
    return response



def render_pdf_responsiva_activos(request, pk):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    todos_activos = Activo.objects.all()
    activo = todos_activos.get(id=pk)
    activos = todos_activos.filter(responsable=activo.responsable, estatus__nombre = "ALTA")

   #Azul Vordcab
    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    rojo = Color(0.59375, 0.05859375, 0.05859375)
    #Encabezado
    c.setFillColor(black)
    c.setLineWidth(.2)
    c.setFont('Helvetica',8)
    caja_iso = 760
    ##Elaborar caja
    c.line(caja_iso,500,caja_iso,720)

     #Encabezado
    c.drawString(420,caja_iso,'Preparado por:')
    c.drawString(420,caja_iso-10,'SUP. ADMON')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(520,caja_iso-10,'SUB ADM')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'SEOV-AFI-N4-01.08')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'10/07/2024')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Solicitud
    #c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    #c.rect(20,575,565,2, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    #c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,755,'Responsiva General')
    #c.setLineWidth(.3) #Grosor
    #c.line(20,caja_proveedor-8,20,575) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    #c.line(585,caja_proveedor-8,585,575) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec


    #c.setFillColor(white)
    #c.setFont('Helvetica-Bold',11)
    #c.drawString(120,caja_proveedor,'Infor')
    #c.drawString(300,caja_proveedor, 'Detalles')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawCentredString(200,170,'Responsable')
    #c.drawString(30,caja_proveedor-40,'Distrito:')
    #c.drawString(30,caja_proveedor-60,'Firma:')
    #c.drawString(30,caja_proveedor-100,'Fecha:')
    # Segunda columna del encabezado
    c.drawCentredString(400,170,'Encargado de Activos')
    c.drawCentredString(300,140,'Distrito - Fecha de impresión')
    #c.drawString(280,caja_proveedor-40,'Distrito:')
    #c.drawString(280,caja_proveedor-60,'Firma:')
    if activo.responsable:
        c.drawCentredString(200,180, activo.responsable.staff.staff.first_name +' '+activo.responsable.staff.staff.last_name )
        activo_resp = Profile.objects.get(Q(tipo__nombre = "ADMIN_ACTIVOS")|Q(tipo__nombre = "ACTIVOS"), distritos = activo.responsable.distritos, tipo__activos = True, st_activo = True)
        c.drawCentredString(400,180, activo_resp.staff.staff.first_name +' '+ activo_resp.staff.staff.last_name)
        # Obtener la fecha actual
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        texto_central = f"{activo_resp.distritos.nombre} - {fecha_actual}"
        c.drawCentredString(300,150, texto_central)
    else:
        c.drawCentredString(200,180, " " )
        c.drawCentredString(400,180, " ")
    

    #Create blank list
    data =[]

    data.append(['''Eco''', '''Descripción''', '''Tipo Activo''', '''Serie''','''Marca''', '''Modelo''', '''Fecha'''])

    high = 700
    cont = 0

    styles = getSampleStyleSheet()
    custom_paragraph_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['BodyText'],
        fontSize=6,  # Tamaño de fuente ajustado
        leading=6,
        alignment=TA_JUSTIFY,
    )

    for activo in activos:
        data.append([
            Paragraph(activo.eco_unidad, custom_paragraph_style), 
            Paragraph(activo.descripcion, custom_paragraph_style),
            activo.tipo_activo, 
            activo.serie,
            activo.marca.nombre if activo.marca else "NR", 
            activo.modelo,
            activo.fecha_asignacion if activo.fecha_asignacion else "NR"
            ])
        cont = cont + 1
        if cont < 26:
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
    c.drawCentredString(240,34,'SEOV-AFI-N4-01.08')
    c.drawCentredString(350,34,'SUB ADM')
    c.drawCentredString(450,34,'10/07/2024')
    c.drawCentredString(550,34,'001')

    c.setFillColor(black)
    width, height = letter
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]

    
    texto_responsiva = """
    RESPONSIVA: A partir de la emisión de la presente, queda asignado a mi cargo y bajo mi responsabilidad el equipo arriba descrito, 
    comprometiéndome a darle buen uso, solicitar oportunamente su mantenimiento preventivo y en los casos necesarios el mantenimiento 
    correctivo para el continuo uso del equipo, vigilar la operación correcta de quienes lo operen, y dar aviso inmediato de cualquier 
    anomalía al departamento correspondiente.
    """

    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)
    # Personalizar el estilo de los párrafos
    custom_style = ParagraphStyle(
    'CustomStyle',
        parent=styles['BodyText'],
        fontSize=10,  # Reducir el tamaño de la fuente a 6
        leading=10,   # Aumentar el espacio entre líneas para asegurar que el texto no se superponga
        alignment=TA_JUSTIFY,  # Alineación del texto
        # Puedes añadir más ajustes si es necesario
    )

    parrafo_responsiva = Paragraph(texto_responsiva, custom_style)
    ancho_disponible = width - 40  # Asumiendo un margen de 20 por cada lado

    # Calcula el espacio que el párrafo necesita (ancho, alto)
    w, h = parrafo_responsiva.wrap(ancho_disponible, height)

    # La posición inicial del párrafo en Y, ajusta según necesites
    posicion_inicio_parrafo = 100  # Ajusta este valor según el espacio necesario para los elementos anteriores

    # Dibuja el párrafo en la posición calculada
    parrafo_responsiva.drawOn(c, 20, posicion_inicio_parrafo)

    table = Table(data, colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2* cm, 2*cm])
    table_style = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 8),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table_style2 = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), colors.black),
        ('FONTSIZE',(0,0),(-1,0), 6),
        #('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table.setStyle(table_style)

    rows_per_page = 25
    rows_per_additional_page = 33
    total_rows = len(data) - 1
    remaining_rows = total_rows - rows_per_page

    if remaining_rows <= 0:
        # Si no hay suficientes filas para una segunda página, dibujar la tabla completa en la primera página
        table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        table.drawOn(c, 20, high)  # Posición en la primera página
    else:
        # Dibujar las primeras 15 filas en la primera página
        first_page_data = data[:rows_per_page + 1]  # Incluye el encabezado
        first_page_table = Table(first_page_data,  colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2* cm, 2 * cm])
        first_page_table.setStyle(table_style)
        first_page_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        first_page_table.drawOn(c, 20, high)  # Posición en la primera página

        # Procesar las filas restantes
        remaining_data = data[rows_per_page + 1:]
        while remaining_data:
            c.showPage()
            c.setFont('Helvetica', 8)
            c.drawString(420, caja_iso, 'Preparado por:')
            c.drawString(420, caja_iso - 10, 'SUP. ADMON')
            c.drawString(520, caja_iso, 'Aprobación')
            c.drawString(520, caja_iso - 10, 'SUB ADM')
            c.drawString(150, caja_iso - 20, 'Número de documento')
            c.drawString(160, caja_iso - 30, 'SEOV-AFI-N4-01.08')
            c.drawString(245, caja_iso - 20, 'Clasificación del documento')
            c.drawString(275, caja_iso - 30, 'Controlado')
            c.drawString(355, caja_iso - 20, 'Nivel del documento')
            c.drawString(380, caja_iso - 30, 'N5')
            c.drawString(440, caja_iso - 20, 'Revisión No.')
            c.drawString(452, caja_iso - 30, '000')
            c.drawString(510, caja_iso - 20, 'Fecha de Emisión')
            c.drawString(525, caja_iso - 30, '10/07/2024')

           
            c.setFont('Helvetica', 12)
            c.setFillColor(prussian_blue)
            c.rect(150, 750, 250, 20, fill=True, stroke=False)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 14)
            c.drawCentredString(280, 755, 'Responsiva General')
            c.drawInlineImage('static/images/logo_vordcab.jpg', 45, 730, 3 * cm, 1.5 * cm)
            parrafo_responsiva.drawOn(c, 20, 50)

            page_data = remaining_data[:rows_per_additional_page]
            
            remaining_data = remaining_data[rows_per_additional_page:]

             # Calcular la posición Y dinámica
            num_rows = len(page_data)
            table_height = num_rows * 18  # Suponiendo que cada fila tiene 18 unidades de altura
            remaining_table_y = height - table_height - 100  # Ajustar según tus márgenes y contenido

            remaining_table = Table(page_data,  colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2 * cm, 2 * cm])
            remaining_table.setStyle(table_style2)
            remaining_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
            remaining_table.drawOn(c, 20, remaining_table_y)  # Ajustar la posición según sea necesario

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='Responsiva_' + str(activo.responsable) +'.pdf')


def render_pdf_responsiva_activos_gerente(request):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    #Here ends conf.
    todos_activos = Activo.objects.all()
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    activos = todos_activos.filter(responsable__distritos= usuario.distritos, estatus__nombre = "ALTA")

   #Azul Vordcab
    prussian_blue = Color(0.0859375,0.1953125,0.30859375)
    rojo = Color(0.59375, 0.05859375, 0.05859375)
    #Encabezado
    c.setFillColor(black)
    c.setLineWidth(.2)
    c.setFont('Helvetica',8)
    caja_iso = 760
    ##Elaborar caja
    c.line(caja_iso,500,caja_iso,720)

     #Encabezado
    c.drawString(420,caja_iso,'Preparado por:')
    c.drawString(420,caja_iso-10,'SUP. ADMON')
    c.drawString(520,caja_iso,'Aprobación')
    c.drawString(520,caja_iso-10,'SUB ADM')
    c.drawString(150,caja_iso-20,'Número de documento')
    c.drawString(160,caja_iso-30,'SEOV-AFI-N4-01.06')
    c.drawString(245,caja_iso-20,'Clasificación del documento')
    c.drawString(275,caja_iso-30,'Controlado')
    c.drawString(355,caja_iso-20,'Nivel del documento')
    c.drawString(380,caja_iso-30, 'N5')
    c.drawString(440,caja_iso-20,'Revisión No.')
    c.drawString(452,caja_iso-30,'000')
    c.drawString(510,caja_iso-20,'Fecha de Emisión')
    c.drawString(525,caja_iso-30,'10/07/2024')

    caja_proveedor = caja_iso - 65
    c.setFont('Helvetica',12)
    c.setFillColor(prussian_blue)
    # REC (Dist del eje Y, Dist del eje X, LARGO DEL RECT, ANCHO DEL RECT)
    c.rect(150,750,250,20, fill=True, stroke=False) #Barra azul superior Solicitud
    #c.rect(20,caja_proveedor - 8,565,20, fill=True, stroke=False) #Barra azul superior Proveedor | Detalle
    #c.rect(20,575,565,2, fill=True, stroke=False) #Linea posterior horizontal
    c.setFillColor(white)
    #c.setLineWidth(.2)
    c.setFont('Helvetica-Bold',14)
    c.drawCentredString(280,755,'Responsiva de Gerente')
    #c.setLineWidth(.3) #Grosor
    #c.line(20,caja_proveedor-8,20,575) #Eje Y donde empieza, Eje X donde empieza, donde termina eje y,donde termina eje x (LINEA 1 contorno)
    #c.line(585,caja_proveedor-8,585,575) #Linea 2 contorno
    c.drawInlineImage('static/images/logo_vordcab.jpg',45,730, 3 * cm, 1.5 * cm) #Imagen vortec


    #c.setFillColor(white)
    #c.setFont('Helvetica-Bold',11)
    #c.drawString(120,caja_proveedor,'Infor')
    #c.drawString(300,caja_proveedor, 'Detalles')
    inicio_central = 300
    #c.line(inicio_central,caja_proveedor-25,inicio_central,520) #Linea Central de caja Proveedor | Detalle
    c.setFillColor(black)
    c.setFont('Helvetica',9)
    c.drawCentredString(200,160,'Gerente')
    #c.drawString(30,caja_proveedor-40,'Distrito:')
    #c.drawString(30,caja_proveedor-60,'Firma:')
    # Segunda columna del encabezado
    c.drawCentredString(400,160,'Encargado de Activos')
    c.drawCentredString(300,140,'Distrito - Fecha de impresión:')
    #c.drawString(280,caja_proveedor-40,'Distrito:')
    #c.drawString(280,caja_proveedor-60,'Firma:')
    if usuario.distritos.nombre == "MATRIZ":
        gerente = Profile.objects.get(id = 16) #1070/Heriberto
    else:
        gerente = Profile.objects.filter(tipo__nombre = "GERENCIA", distritos = usuario.distritos, st_activo = True).first()
    c.drawCentredString(200,170, gerente.staff.staff.first_name +' '+ gerente.staff.staff.last_name )
    activo_resp = Profile.objects.get(Q(tipo__nombre = "ADMIN_ACTIVOS")|Q(tipo__nombre = "ACTIVOS"), distritos = usuario.distritos, tipo__activos = True, st_activo = True)
    c.drawCentredString(400,170, activo_resp.staff.staff.first_name +' '+ activo_resp.staff.staff.last_name)
    # Obtener la fecha actual
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    texto_central = f"{activo_resp.distritos.nombre} - {fecha_actual}"
    c.drawCentredString(300,150, texto_central)
   
    

    #Create blank list
    data =[]

    data.append(['''Eco''', '''Descripción''', '''Tipo Activo''', '''Serie''','''Marca''', '''Modelo''', '''Fecha'''])

    high = 700
    cont = 0

    styles = getSampleStyleSheet()
    custom_paragraph_style = ParagraphStyle(
        'CustomStyle',
        parent=styles['BodyText'],
        fontSize=6,  # Tamaño de fuente ajustado
        leading=6,
        alignment=TA_JUSTIFY,
    )

    for activo in activos:
        #if activo.activo is None:
        #    menor = 'NA'
        #elif activo.activo.producto.subfamilia and  activo.activo.producto.subfamilia.nombre == 'ACTIVO MENOR':
        #    menor = 'Si'
        #else:
        #    menor = 'No'
        data.append([
            Paragraph(activo.eco_unidad, custom_paragraph_style), 
            Paragraph(activo.descripcion, custom_paragraph_style),
            activo.tipo_activo, 
            activo.serie,
            activo.marca.nombre if activo.marca else "NR", 
            activo.modelo,
            #menor,
            ])
        cont = cont + 1
        if cont < 26:
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
    c.drawCentredString(240,34,'SEOV-AFI-N4-01.06')
    c.drawCentredString(350,34,'SUB ADM')
    c.drawCentredString(450,34,'10/07/2024')
    c.drawCentredString(550,34,'001')

    c.setFillColor(black)
    width, height = letter
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]

    
    texto_responsiva = """
    RESPONSIVA: A partir de la emisión de la presente, queda asignado a mi cargo y bajo mi responsabilidad el equipo arriba descrito, 
    comprometiéndome a darle buen uso, solicitar oportunamente su mantenimiento preventivo y en los casos necesarios el mantenimiento 
    correctivo para el continuo uso del equipo, vigilar la operación correcta de quienes lo operen, y dar aviso inmediato de cualquier 
    anomalía al departamento correspondiente.
    """

    c.setFillColor(prussian_blue)
    c.rect(20,30,565,30, fill=True, stroke=False)
    c.setFillColor(white)
    # Personalizar el estilo de los párrafos
    custom_style = ParagraphStyle(
    'CustomStyle',
        parent=styles['BodyText'],
        fontSize=10,  # Reducir el tamaño de la fuente a 6
        leading=10,   # Aumentar el espacio entre líneas para asegurar que el texto no se superponga
        alignment=TA_JUSTIFY,  # Alineación del texto
        # Puedes añadir más ajustes si es necesario
    )

    parrafo_responsiva = Paragraph(texto_responsiva, custom_style)
    ancho_disponible = width - 40  # Asumiendo un margen de 20 por cada lado

    # Calcula el espacio que el párrafo necesita (ancho, alto)
    w, h = parrafo_responsiva.wrap(ancho_disponible, height)

    # La posición inicial del párrafo en Y, ajusta según necesites
    posicion_inicio_parrafo = 100  # Ajusta este valor según el espacio necesario para los elementos anteriores

    # Dibuja el párrafo en la posición calculada
    parrafo_responsiva.drawOn(c, 20, posicion_inicio_parrafo)

    table = Table(data, colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2* cm, 2*cm])
    table_style = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), white),
        ('FONTSIZE',(0,0),(-1,0), 8),
        ('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table_style2 = TableStyle([ #estilos de la tabla
        ('INNERGRID',(0,0),(-1,-1), 0.25, colors.white),
        ('BOX',(0,0),(-1,-1), 0.25, colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        #ENCABEZADO
        ('TEXTCOLOR',(0,0),(-1,0), colors.black),
        ('FONTSIZE',(0,0),(-1,0), 6),
        #('BACKGROUND',(0,0),(-1,0), prussian_blue),
        #CUERPO
        ('TEXTCOLOR',(0,1),(-1,-1), colors.black),
        ('FONTSIZE',(0,1),(-1,-1), 6),
        ])
    table.setStyle(table_style)

    rows_per_page = 25
    rows_per_additional_page = 33
    total_rows = len(data) - 1
    remaining_rows = total_rows - rows_per_page

    if remaining_rows <= 0:
        # Si no hay suficientes filas para una segunda página, dibujar la tabla completa en la primera página
        table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        table.drawOn(c, 20, high)  # Posición en la primera página
    else:
        # Dibujar las primeras 15 filas en la primera página
        first_page_data = data[:rows_per_page + 1]  # Incluye el encabezado
        first_page_table = Table(first_page_data,  colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2* cm, 2*cm])
        first_page_table.setStyle(table_style)
        first_page_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
        first_page_table.drawOn(c, 20, high)  # Posición en la primera página

        # Procesar las filas restantes
        remaining_data = data[rows_per_page + 1:]
        while remaining_data:
            c.showPage()
            c.setFont('Helvetica', 8)
            c.drawString(420, caja_iso, 'Preparado por:')
            c.drawString(420, caja_iso - 10, 'SUP. ADMON')
            c.drawString(520, caja_iso, 'Aprobación')
            c.drawString(520, caja_iso - 10, 'SUB ADM')
            c.drawString(150, caja_iso - 20, 'Número de documento')
            c.drawString(160, caja_iso - 30, 'SEOV-AFI-N4-01.06')
            c.drawString(245, caja_iso - 20, 'Clasificación del documento')
            c.drawString(275, caja_iso - 30, 'Controlado')
            c.drawString(355, caja_iso - 20, 'Nivel del documento')
            c.drawString(380, caja_iso - 30, 'N5')
            c.drawString(440, caja_iso - 20, 'Revisión No.')
            c.drawString(452, caja_iso - 30, '000')
            c.drawString(510, caja_iso - 20, 'Fecha de Emisión')
            c.drawString(525, caja_iso - 30, '10/07/2024')

           
            c.setFont('Helvetica', 12)
            c.setFillColor(prussian_blue)
            c.rect(150, 750, 250, 20, fill=True, stroke=False)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 14)
            c.drawCentredString(280, 755, 'Responsiva de Gerente')
            c.drawInlineImage('static/images/logo_vordcab.jpg', 45, 730, 3 * cm, 1.5 * cm)
            parrafo_responsiva.drawOn(c, 20, 50)

            page_data = remaining_data[:rows_per_additional_page]
            
            remaining_data = remaining_data[rows_per_additional_page:]

             # Calcular la posición Y dinámica
            num_rows = len(page_data)
            table_height = num_rows * 18  # Suponiendo que cada fila tiene 18 unidades de altura
            remaining_table_y = height - table_height - 100  # Ajustar según tus márgenes y contenido

            remaining_table = Table(page_data,  colWidths=[2.5 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm, 2* cm, 2*cm], splitByRow=True)
            remaining_table.setStyle(table_style2)
            remaining_table.wrapOn(c, c._pagesize[0], c._pagesize[1])
            remaining_table.drawOn(c, 20, remaining_table_y)  # Ajustar la posición según sea necesario

    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename='Responsiva_Gerencia' + '.pdf')

@login_required(login_url='user-login')
@perfil_seleccionado_required
def gestionar_tipo_activo(request):
    pk_perfil = request.session.get('selected_profile_id') 
    perfil = Profile.objects.get(id = pk_perfil)
    if perfil.tipo.activos == True:   
        if request.method == "POST":
            tipo_activo_form = Tipo_ActivoForm(request.POST)
            if tipo_activo_form.is_valid():
                nuevo_tipo_activo = tipo_activo_form.save()  # Guarda y obtiene el objeto
                messages.success(request, f'Has agregado el tipo de activo: {nuevo_tipo_activo.nombre}')  # Muestra el nombre del nuevo tipo
                return redirect('activos')  # Redirigir después de guardar
        else:
            tipo_activo_form = Tipo_ActivoForm()

        tipos_activos = Tipo_Activo.objects.all().order_by('nombre')

        context = {
            'tipo_activo_form': tipo_activo_form,
            'tipos_activos': tipos_activos,
        }

        return render(request, 'activos/gestionar_tipo_activo.html', context)
    else:
        raise Http404("No tienes permiso para agregar activos.")
    
@login_required(login_url='user-login')
@perfil_seleccionado_required
def gestionar_marca(request):
    pk_perfil = request.session.get('selected_profile_id') 
    perfil = Profile.objects.get(id = pk_perfil)
    if perfil.tipo.activos == True:  
        if request.method == "POST":
            marca_form = MarcaForm(request.POST)
            if marca_form.is_valid():
                nueva_marca = marca_form.save()
                messages.success(request,f'Has agregado la marca {nueva_marca.nombre}')
                return redirect('activos')  # Redirigir después de guardar
        else:
            marca_form = MarcaForm()

        marcas = Marca.objects.all().order_by('nombre')

        context = {
            'marca_form': marca_form,
            'marcas': marcas,
        }

        return render(request, 'activos/gestionar_marca.html', context)
    else:
        raise Http404("No tienes permiso para agregar activos.")
    

@login_required(login_url='user-login')
@perfil_seleccionado_required
def activos_producto(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    if usuario.tipo.nombre == "ADMIN_ACTIVOS" or usuario.tipo.nombre == "Admin":
        items = Inventario.objects.filter(complete = True, producto__activo = True).annotate(activo_count=Count('activo')).order_by('producto__codigo')
    elif usuario.tipo.nombre == "ACTIVOS": 
        items = Inventario.objects.filter(complete = True, producto__activo = True, distrito = usuario.distritos).annotate(activo_count=Count('activo')).order_by('producto__codigo')
    else:
        items = Inventario.objects.none()
    

    myfilter=InventarioFilter(request.GET, queryset=items)
    items = myfilter.qs

    #Set up pagination
    p = Paginator(items, 50)
    page = request.GET.get('page')
    items_list = p.get_page(page)
    cantidad = items_list.paginator.count  # Total de elementos filtrados
    if request.method =='POST' and 'btnExcel' in request.POST:
        #return convert_excel_inventario(existencia, valor_inv, dict_entradas, dict_resultados)
        return convert_excel_inventario_xlsxwriter(items_list,)
    # Sumar el total de todos los activo_count
    total_activo_count = items.aggregate(total=Sum('activo_count'))['total']

    context = {
        'usuario':usuario,
        'items': items,
        'myfilter':myfilter,
        'items_list':items_list,
        'cantidad': cantidad,
        'total_activo_count':total_activo_count,
        }


    return render(request,'activos/activos_producto.html', context)

def convert_excel_inventario_xlsxwriter(existencia):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Inventario')

    # Definir los estilos antes de usarlos
    head_style = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '333366', 'font_name': 'Arial', 'font_size': 11})
    body_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 10})
    money_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 10})
    money_resumen_style = workbook.add_format({'num_format': '$ #,##0.00', 'font_name': 'Calibri', 'font_size': 14, 'bold': True})
    date_style = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Calibri', 'font_size': 10})

    # Definir las columnas antes de utilizar la variable `columns`
    columns = ['Código', 'Producto', 'Distrito', 'Unidad', 'Cantidad', 'Cantidad Apartada', 'Minimos', 'Ubicación', 'Estante','Familia','Subfamilia']
    
    # Escribir el encabezado con los estilos definidos
    #worksheet.write_row('A1', columns, head_style)

    # Establecer los anchos de las columnas después de definir `columns`
    worksheet.set_column('A:A', 10)
    worksheet.set_column('B:B', 30)
    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    # Escribir los datos
    row_num = 0
    for inventario in existencia:
        if inventario.producto is None:
            familia = 'Sin producto asociado'
            subfamilia = ''
        else:
            familia = inventario.producto.familia.nombre
            if inventario.producto.subfamilia:
                subfamilia = inventario.producto.subfamilia.nombre
            else:
                subfamilia = ''
        row_num += 1
    
        row = [
            inventario.producto.codigo,
            inventario.producto.nombre,
            inventario.distrito.nombre,
            inventario.producto.unidad.nombre,
            inventario.cantidad,
            inventario.cantidad_apartada,
            inventario.minimo,
            inventario.ubicacion,
            inventario.estante,
            familia,
            subfamilia,
        ]
    
        for col_num, item in enumerate(row, start=1):  # Enumerate empieza con 1 para A1, ajusta según sea necesario
            worksheet.write(row_num, col_num - 1, item, body_style)
    

    # Escribir el total del inventario
    worksheet.set_column('N:N', 30)
    worksheet.set_column('O:O', 30)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
      # Establecer una cookie para indicar que la descarga ha iniciado
    response.set_cookie('iniciada', 'true', max_age=20)  # La cookie expira en 20 segundos
    

    
    response['Content-Disposition'] = f'attachment; filename=Inventario_{dt.date.today()}.xlsx'
    output.close()
    return response

