from django.shortcuts import render, redirect
from .models import Cobranza
from solicitudes.models import Proyecto
from .forms import Cobranza_Form, Cobranza_Edit_Form
from .filters import PagosFilter
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
# Create your views here.

@login_required(login_url='user-login')
def pagos_cobranza(request):
    pagos = Cobranza.objects.all()

    myfilter=PagosFilter(request.GET, queryset=pagos)
    pagos = myfilter.qs

    #Set up pagination
    p = Paginator(pagos, 50)
    page = request.GET.get('page')
    pagos_list = p.get_page(page)

    context = {
        'pagos':pagos,
        'pagos_list':pagos_list,
        'myfilter':myfilter,
        }

    return render(request,'cobranza/cobranza.html',context)

def add_pago_cliente(request):
    #usuario = request.user.id
    form = Cobranza_Form()
    proyectos = Proyecto.objects.filter(activo=True)

    if request.method =='POST':
        form = Cobranza_Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'Has agregado correctamente el pago al proyecto')
            return redirect('cobranza-pagos')
    else:
        form = Cobranza_Form()

    context = {
        'form': form,
        'proyectos':proyectos,
        }

    return render(request,'cobranza/add_pago_cliente.html',context)

@login_required(login_url='user-login')
def pagos_edit(request, pk):
#def product_update_modal(request, pk):

    pago = Cobranza.objects.get(id=pk)

    if request.method =='POST':
        form = Cobranza_Edit_Form(request.POST, instance=pago)
        if form.is_valid():
            form.save()
            messages.success(request,f'Has actualizado correctamente el proyecto {pago.id}')
            return redirect('cobranza-pagos')
        else:
            messages.success(request,f'{form.errors}')
    else:
        form = Cobranza_Edit_Form(instance=pago)


    context = {
        'form': form,
        'pago':pago,
        }
    return render(request,'cobranza/edit_pago_cliente.html', context)
