from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.urls import resolve
import logging
import os
from django.shortcuts import render, redirect
from functools import wraps
from .models import Profile
from django.http import HttpResponseForbidden
from user.logger_config import get_custom_logger
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied

logger = get_custom_logger(__name__)


def perfil_seleccionado_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar si el usuario ha seleccionado un perfil
        if not request.user.is_authenticated:
            return redirect('user-login')
        
        
        selected_profile_id = request.session.get('selected_profile_id')
        if not selected_profile_id:
            return redirect('select-profile')  # Redirige si no hay perfil seleccionado
        
        try:
            selected_profile = Profile.objects.get(id=selected_profile_id)
        except ObjectDoesNotExist:
            logger.warning(f"Perfil con ID {selected_profile_id} no encontrado. Redirigiendo a selección de perfil.")
            return redirect('select-profile')  # Redirige si el perfil no existe
       
        print(selected_profile.tipo.nombre)

        if selected_profile.tipo.nombre == "PROVEEDOR_EXTERNO":
            vistas_permitidas = ['dashboard-index', 'matriz-oc-proveedores','matriz-direcciones','matriz', 'matriz-facturas-nomodal',
                                  'productos-oc', 'factura-nueva', 'edit-csf','edit-acta-credencial', 'edit-comprobante-domicilio',
                                  'edit-opinion-cumplimiento','evidencias-proveedor','subir-evidencias','eliminar-evidencia',
                                  'matriz-complementos', 'complemento-nuevo','complemento-eliminar']  # Cambia por los nombres reales de las vistas

            vista_actual = resolve(request.path_info).url_name
            if vista_actual not in vistas_permitidas:
                logger.warning(f"Intento acceso no autorizado a compras autorización por usuario {request.user.first_name} {request.user.last_name}")
                return render(request,'partials/acceso_denegado.html')
       
        
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