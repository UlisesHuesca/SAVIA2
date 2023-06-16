from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from dashboard.models import Inventario, Profile
from .models import Activo
from .forms import Activo_Form
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
#Todo para construir el código QR
import qrcode
from io import BytesIO


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


    for producto in productos:
        activo = Activo.objects.filter(activo=producto)
        activo_cont = activo.filter(completo = True).count()
        existencia_inv = producto.cantidad + producto.cantidad_apartada
        if activo_cont == existencia_inv and activo_cont > 0: #Si el numero de activos es igual a la existencia en inventario
            producto.activo_disponible = False   
            producto.save()         
            
    activo, created = Activo.objects.get_or_create(creado_por=perfil, completo=False)
    productos_activos = Inventario.objects.filter(producto__activo =True, activo_disponible =True)
    
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
            return HttpResponse(status=204)
        else:
            messages.success(request,'No está validando')



    context = {
        'form':form,
        'productos_activos':productos_activos,
    }

    return render(request,'activos/add_activos.html', context)


def generate_qr(request, pk):
    # Obtén el activo por la llave primaria
    activo = Activo.objects.get(pk=pk)
    
    # Construye la data del QR. Puedes cambiar esto para adaptarlo a tus necesidades.
    qr_data = f"""
    Eco_Unidad: {activo.eco_unidad}
    Tipo: {activo.tipo_activo}
    Serie: {activo.serie}
    Cuenta Contable: {activo.cuenta_contable}
    Factura Interna: {activo.factura_interna}
    Descripción: {activo.descripcion}
    Responsable: {activo.responsable}
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
