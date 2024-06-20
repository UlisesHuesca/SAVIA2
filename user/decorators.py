from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
import logging
import os
from django.shortcuts import render, redirect
from functools import wraps
from .models import Profile
from django.http import HttpResponseForbidden
from user.logger_config import get_custom_logger

logger = get_custom_logger(__name__)


def perfil_seleccionado_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar si el usuario ha seleccionado un perfil
        if not request.user.is_authenticated:
            return redirect('user-login')
        
        selected_profile_id = request.session.get('selected_profile_id')
        if not selected_profile_id:
            return redirect('select-profile')  # Redirige al usuario a la selección de perfil si no lo ha seleccionado
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

def tipo_usuario_requerido(*tipos_requeridos):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            pk_perfil = request.session.get('selected_profile_id')
            if pk_perfil is None:
                return HttpResponseForbidden("No se ha seleccionado un perfil.")
            try:
                perfil_usuario = Profile.objects.get(id=pk_perfil)
            except Profile.DoesNotExist:
                return HttpResponseForbidden("Perfil no encontrado.")
            
            # Verificando si el tipo de perfil cumple alguno de los requeridos
            if not any(getattr(perfil_usuario.tipo, tipo, False) for tipo in tipos_requeridos):
                logger.warning(f"Intento acceso no autorizado a compras autorización por usuario {request.user.first_name} {request.user.last_name}")
                return render(request,'partials/acceso_denegado.html')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator 