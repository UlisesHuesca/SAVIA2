from django.shortcuts import render, redirect
from user.decorators import perfil_seleccionado_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView
from django.conf import settings
from .models import Profile, CustomUser
from .forms import CustomUser_Form
from requisiciones.views import get_image_base64
from .forms import UserForm
import os

# Create your views here.
@perfil_seleccionado_required
def register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user-login')
    else:
        form = UserForm()
    ctx = {
       
        }
    return render(request, 'user/register.html',ctx)

@perfil_seleccionado_required
def profile(request):
    pk = request.session.get('selected_profile_id')
    perfil = Profile.objects.get(id = pk)

    context = {
        'perfil':perfil,
    }

    return render(request, 'user/profile.html', context)

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

class CustomPasswordResetView(PasswordResetView):
    def get_email_context(self, **kwargs):
        context = super().get_email_context(**kwargs)
        # Aquí es donde agregarías tus imágenes en base64
        static_path = settings.STATIC_ROOT
        img_path = os.path.join(static_path,'images','SAVIA_Logo.png')
        img_path2 = os.path.join(static_path,'images','logo_vordcab.jpg')
       
        image_base64 = get_image_base64(img_path)
        logo_v_base64 = get_image_base64(img_path2)

       
        context['logo_v_base64'] = logo_v_base64
        context['image_base64'] = image_base64
        return context
