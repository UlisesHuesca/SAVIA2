from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import Inventario, Profile, Marca
from django.core import serializers
from django.db.models import Value, F, Q
from django.db.models.functions import Concat
from dashboard.models import Activo
from requisiciones.models import Salidas 
from .forms import Activo_Form, Edit_Activo_Form, UpdateResponsableForm, SalidasActivoForm
from django.contrib import messages
from activos.filters import ActivoFilter
from django.http import JsonResponse, HttpResponse, FileResponse
#Todo para construir el código QR
import qrcode
from io import BytesIO
import datetime as dt
from datetime import date, datetime, timedelta
import json
#Excel
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

# Create your views here.
@login_required(login_url='user-login')
def activos(request):
    pk_perfil = request.session.get('selected_profile_id') 
    usuario = Profile.objects.get(id = pk_perfil)
    activos = Activo.objects.filter(completo=True, responsable__distritos = usuario.distritos)
    myfilter = ActivoFilter(request.GET, queryset=activos)
    activos = myfilter.qs 

    if request.method == "POST" and 'btnExcel' in request.POST:
        return convert_activos_to_xls(activos)

    context = {
        'activos':activos,
        'myfilter': myfilter,
    }

    return render(request,'activos/activos.html',context)

@login_required(login_url='user-login')
def add_activo(request):
    perfil = Profile.objects.get(staff__id=request.user.id)
    #activos = Activo.objects.filter(completo=True)
    productos = Inventario.objects.filter(producto__activo=True)
    personal = Profile.objects.all()
    marcas = Marca.objects.all() 
    #print(productos)


    for producto in productos:
        producto.activo_disponible = True
        activo = Activo.objects.filter(activo=producto)
        activo_cont = activo.filter(completo = True).count()
        salidas = Salidas.objects.filter(producto__articulos__producto = producto).count()
        
        existencia_inv = producto.cantidad + producto.apartada + salidas
        print( activo, activo_cont, existencia_inv, salidas)
        if activo_cont == existencia_inv and activo_cont > 0 or existencia_inv == 0: #Si el numero de activos es igual a la existencia en inventario #Si el numero de activos es igual a la existencia en inventario
            producto.activo_disponible = False   
        producto.save()         
            
    activo, created = Activo.objects.get_or_create(creado_por=perfil, completo=False)
    productos_activos = productos.filter(activo_disponible =True)
    #print(productos_activos)
    form = Activo_Form()

    form.fields['activo'].queryset = productos_activos

    if request.method =='POST':
        form = Activo_Form(request.POST, instance = activo)
        messages.success(request,f'Has agregado incorrectamente el activo')
        if form.is_valid():
            activo = form.save(commit=False)
            activo.completo = True
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
        'personal':personal,
        'marcas': marcas,
        'form':form,
        'productos_activos':productos_activos,
    }

    return render(request,'activos/add_activos.html', context)

@login_required(login_url='user-login')
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


    productos = inventarios.filter(producto = producto_salida.producto.articulos.producto.producto)
    producto.activo_disponible = True
    activos_completos = Activo.objects.filter(activo=producto, completo = True)
    #ecos = activos_completos.values_list('eco_unidad', flat=True)
       
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
        }

    return render(request,'activos/add_activos.html', context)

@login_required(login_url='user-login')
def edit_activo(request, pk):
    pk_perfil = request.session.get('selected_profile_id') 
    empleados = Profile.objects.all()
    perfil = empleados.get(id = pk_perfil)
    #producto = Salidas.objects.get(id=pk)
    activo = Activo.objects.get(id=pk)
    responsable = empleados.get(id=activo.responsable.id )
    responsables = empleados.filter(distritos = perfil.distritos, st_activo = True)
    marcas = Marca.objects.all() 
    if activo.marca:
        marca_p = marcas.get(id = activo.marca.id)
    else:
        marca_p = None


    form = Edit_Activo_Form(instance = activo)

    responsables_para_select2 = [
        {
            'id': responsable.id, 
            'text': str(responsable.staff.staff.first_name) + (' ') + str(responsable.staff.staff.last_name)
        } for responsable in responsables
    ]

    responsable_predeterminado = {
        'id': activo.responsable.id,
        'text': f"{activo.responsable.staff.staff.first_name} {activo.responsable.staff.staff.last_name}"
    }
    
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

    error_messages = {}    

    if request.method =='POST':
        form = Edit_Activo_Form(request.POST, instance = activo)
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
        'marcas_para_select2':marcas_para_select2,
        'marca_predeterminada':marca_predeterminada,
        'activo':activo,
        #'personal':personal,
        'marcas':marcas,
        'form':form,
    }

    return render(request,'activos/edit_activos.html', context)


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

    columns = ['Eco', 'Responsable', 'Tipo Activo', 'Serie', 'Marca', 'Modelo', 'Descripción', 'Status']

    columna_max = len(columns)+2

    worksheet.write(0, columna_max - 1, 'Reporte Creado Automáticamente por SAVIA 2.0. UH', messages_style)
    worksheet.write(1, columna_max - 1, 'Software desarrollado por Vordcab S.A. de C.V.', messages_style)
    worksheet.set_column(columna_max - 1, columna_max, 30)  # Ajusta el ancho de las columnas nuevas
    
    # Escribir encabezados debajo de los mensajes
    #worksheet.write(2, columna_max - 1, "Fecha Inicial", head_style)
    #worksheet.write(3, columna_max - 1, "Fecha Final", head_style)
    #worksheet.write(4, columna_max - 1, "Total de OC's", head_style)
    #worksheet.write(5, columna_max - 1, "Requisiciones Aprobadas", head_style)
    #worksheet.write(6, columna_max - 1, "Requisiciones Atendidas", head_style)
    #worksheet.write(7, columna_max - 1, "KPI Colocadas/Aprobadas", head_style)
    #worksheet.write(8, columna_max - 1, "OC Entregadas", head_style)
    #worksheet.write(9, columna_max - 1, "OC Autorizadas", head_style)
    #worksheet.write(10, columna_max - 1, "KPI OC Entregadas/Total de OC", head_style)
    
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
    #worksheet.write_formula(8, columna_max, '=COUNTIF(S:S, "Entregada")', body_style)
    # Escribir otra fórmula COUNTIF, también con el estilo corporal
    #worksheet.write_formula(9, columna_max, '=COUNTIF(O:O, "Autorizado")', body_style)
    #worksheet.write_formula(10, columna_max, formula, percent_style)

    for i, column in enumerate(columns):
        worksheet.write(0, i, column, head_style)
        worksheet.set_column(i, i, 15)  # Ajusta el ancho de las columnas

    #worksheet.set_column('L:L', 12,  money_style)
    #worksheet.set_column('M:M', 12, money_style) 
    
    row_num = 0
    for activo in activos:
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
            f"{activo.responsable.staff.staff.first_name} {activo.responsable.staff.staff.last_name}",
            activo.tipo_activo.nombre,
            activo.serie,
            activo.marca,
            activo.modelo,
            activo.descripcion,
            activo.estatus
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