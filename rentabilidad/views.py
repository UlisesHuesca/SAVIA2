from django.shortcuts import render, redirect
from .models import Costos, Solicitud_Costos
from user.models import Profile, Distrito
from user.decorators import perfil_seleccionado_required
from .forms import Costo_Form, Solicitud_Costo_Form
from datetime import date, datetime
from django.contrib import messages

# Create your views here.
@perfil_seleccionado_required
def costos(request):
    pk_profile = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_profile)
    costos = Costos.objects.all()

    #myfilter= ContratoFilter(request.GET, queryset=contratos)

    #Set up pagination
    #p = Paginator(contratos, 10)
    #page = request.GET.get('page')
    #contratos_list = p.get_page(page)

    context = {
        'costos':costos,
        #'myfilter': myfilter,
        #'contratos_list': contratos_list,
         }

    return render(request,'rentabilidad/costos.html', context)

@perfil_seleccionado_required
def add_costo(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    solicitud, created =  Solicitud_Costos.objects.get_or_create(created_by=usuario, complete = False)
    costos = Costos.objects.filter(solicitud = solicitud)
    form = Solicitud_Costo_Form()
    form.fields['distrito'].queryset = distritos
    costo_form = Costo_Form()

    if request.method =='POST':
        
        form = Costo_Form(request.POST, instance = solicitud)
        if "seguir" in request.POST:
            if form.is_valid():
                solicitud = form.save(commit=False)
                solicitud.created_at = date.today()
                solicitud.complete = True
                solicitud.save()
                messages.success(request,'Has agregado correctamente el Costo')
                return redirect('add-costo')

        if "btn_costo" in request.POST:
            costo, created = Costos.objects.get_or_create(complete = False, solicitud = solicitud)
            if form.is_valid():
                costo = form.save(commit=False)
                costo.complete = True
                costo.save()
                messages.success(request,'Has agregado correctamente un costo')
                return redirect('rentabilidad-costos')
 

    context = {
        'form': form,
        'costo_form': costo_form,
        'costos':costos,
        }

    return render(request,'rentabilidad/add_costo.html',context)

@perfil_seleccionado_required
def delete_costo(request, pk):
    costo = Costos.objects.get(id=pk)
    messages.success(request,f'El costo {costo.concepto} ha sido eliminado exitosamente')
    costo.delete()

    return redirect('rentabilidad-costos')