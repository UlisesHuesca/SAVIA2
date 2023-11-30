from django.shortcuts import render, redirect
from user.decorators import perfil_seleccionado_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile, CustomUser
from .forms import CustomUser_Form
#Estamos importando la "Form" de default de Django para crear usuarios
#from django.contrib.auth.forms import UserCreationForm
from .forms import UserForm

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user-login')
    else:
        form = UserForm()
    ctx = {
        'form':form,
        }
    return render(request, 'user/register.html',ctx)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def profile(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)

    context = {
        'perfil':perfil,
    }

    return render(request, 'user/profile.html', context)

@login_required(login_url='user-login')
@perfil_seleccionado_required
def edit_profile(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)
    custom_user = CustomUser.objects.get(staff = perfil.staff.staff)
    form = CustomUser_Form(instance=custom_user)
    error_messages = {}

    if request.method == "POST":
        form = CustomUser_Form(request.POST, request.FILES, instance=custom_user)
        if form.is_valid():
            custom_user = form.save()
            messages.success(request,f'Tu perfil se ha actualizado correctamente, {custom_user.staff.first_name}')
            return redirect('user-profile')
        else:
            for field, errors in form.errors.items():
                error_messages[field] = errors.as_text()


    context = {
        'error_messages': error_messages,
        'form':form,
        'custom_user':custom_user,
    }

    return render(request, 'user/edit_profile.html', context)
