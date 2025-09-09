from django.shortcuts import render, redirect
from .models import Costos
from user.models import Profile, Distrito
from user.decorators import perfil_seleccionado_required
from .forms import Costo_Form
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
    #usuario = Profile.objects.get(staff=request.user
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id = pk_perfil)
    distritos = Distrito.objects.exclude(id__in = [7,8,16]) #7 MATRIZ ALTERNATIVO, 8 ALTAMIRA ALTERNATIVO,16 BRASIL
    print(distritos)
    form = Costo_Form()
    form.fields['distrito'].queryset = distritos

    if request.method =='POST':
        costo, created = Costos.objects.get_or_create(complete = False)
        form = Costo_Form(request.POST, instance = costo)
        if form.is_valid():
            costo = form.save(commit=False)
            costo.created_at = date.today()
            costo.created_by = usuario
            costo.complete = True
            costo.save()
            messages.success(request,'Has agregado correctamente el Costo')
            return redirect('rentabilidad-costos')
 

    context = {
        'form': form,
        }

    return render(request,'rentabilidad/add_costo.html',context)