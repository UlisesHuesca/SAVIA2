from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import Inventario, Profile, Marca
from django.core import serializers
from .models import Activo
from requisiciones.models import Salidas 
from .forms import Activo_Form, Edit_Activo_Form, UpdateResponsableForm, SalidasActivoForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
#Todo para construir el código QR
import qrcode
from io import BytesIO
import json


# Create your views here.
@login_required(login_url='user-login')
def activos(request):
    
    activos = Activo.objects.filter(completo=True)

    context = {
        'activos':activos,
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
    perfil = personal.get(staff__id=request.user.id)
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
    perfil = Profile.objects.get(staff__id=request.user.id)
    producto = Salidas.objects.get(id=pk)
    activo = Activo.objects.filter(activo = producto.producto.articulos.producto)
    personal = Profile.objects.all()
    marcas = Marca.objects.all() 
    
    form = Edit_Activo_Form()

    
    if request.method =='POST':
        form = Edit_Activo_Form(request.POST, instance = activo)
        if form.is_valid():
            activo = form.save(commit=False)
            activo.completo = True
            activo.save()
            messages.success(request,f'Has modificado correctamente el activo {activo.eco_unidad}')
            return redirect('activos')
        else:
            print(form.errors) 
            messages.success(request,'No está validando')



    context = {
        'activo':activo,
        'personal':personal,
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
    Eco_Unidad: {activo.eco_unidad}
    Tipo: {activo.tipo_activo}
    Descripción: {activo.descripcion}
    Marca: {activo.marca}
    Modelo: {activo.modelo}
    Responsable: {activo.responsable.staff.first_name}{activo.responsable.staff.last_name}
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
