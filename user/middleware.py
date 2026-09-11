# myapp/middleware.py

from django.utils.deprecation import MiddlewareMixin
import logging

from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import redirect
from .utils import obtener_empresa_por_host
from user.models import Profile

logger = logging.getLogger(__name__)

class LogUserAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user if request.user.is_authenticated else 'Anonymous'
        message = f"{request.method} {request.get_full_path()} by {user}"
        logger.info(message)


class Handle404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            user = request.user if request.user.is_authenticated else 'Anonymous'
            logger.warning(f'404 Not Found: {request.path} by {user}')
            context = {'request_path': request.path}
            content = render_to_string('partials/404.html', context, request)
            return HttpResponseNotFound(content)
        return response



class EmpresaPerfilMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Usuario no autenticado: dejar pasar
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Evitar loops en rutas sensibles
        url_name = (
            request.resolver_match.url_name
            if request.resolver_match
            else None
        )

        rutas_exentas = {
            'user-login',
            'user-logout',
            'select-profile',
            'password-reset',
        }

        if url_name in rutas_exentas:
            return self.get_response(request)

        profile_id = request.session.get('selected_profile_id')

        # Todavía no hay perfil seleccionado
        if not profile_id:
            return self.get_response(request)

        empresa_host = obtener_empresa_por_host(request)

        # Host no reconocido: no bloquear
        if empresa_host is None:
            return self.get_response(request)

        try:
            profile = Profile.objects.select_related(
                'distritos'
            ).get(
                id=profile_id
            )

        except Profile.DoesNotExist:

            request.session.pop(
                'selected_profile_id',
                None
            )

            messages.error(
                request,
                'El perfil seleccionado ya no es válido.'
            )

            return redirect('select-profile')

        distrito = (
            profile.distritos.nombre.upper()
            if profile.distritos
            else ''
        )

        #print("=" * 60)
        #print("EMPRESA PERFIL MIDDLEWARE")
        #print("Host:", request.get_host())
        #print("Empresa host:", empresa_host)
        #print("Usuario:", request.user)
        #print("Profile ID:", profile_id)
        #print("Distrito perfil:", distrito)
        #print("=" * 60)
        es_host_yerod = empresa_host == 'YEROD'
        es_perfil_yerod = distrito == 'YEROD'

        if es_host_yerod != es_perfil_yerod:

            logger.warning(
                f"Acceso de perfil no permitido. "
                f"Usuario={request.user} "
                f"Host={request.get_host()} "
                f"Profile={profile.id} "
                f"Distrito={distrito}"
            )

            request.session.pop(
                'selected_profile_id',
                None
            )

            messages.error(
                request,
                'El perfil activo no corresponde a este portal.'
            )

            return redirect('select-profile')

        return self.get_response(request)