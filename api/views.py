from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from dashboard.models import Inventario 
from compras.models import Compra, Proveedor_direcciones
from .serializers import InventarioSerializer, CompraSerializer, ProveedorDireccionesSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
import requests
from django.contrib.auth.models import User
from user.models import CustomUser
from django.contrib.auth.decorators import login_required

# Create your views here.


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getData(request):
    inventario = Inventario.objects.all()
    serializer = InventarioSerializer(inventario, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def CompraAPI(request):
    compras = Compra.objects.filter(complete = True)
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        compras = compras.order_by(ordering)
        
    paginator = Paginator(compras, per_page=per_page)
    try: 
        compras = paginator.page(number=page)
    except EmptyPage:
        compras = []
    serialized_compras = CompraSerializer(compras, many=True)
        
    return Response(serialized_compras.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def proveedores_api(request):
    proveedores = Proveedor_direcciones.objects.filter(completo = True)
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        proveedores = Proveedor_direcciones.order_by(ordering)
        
    paginator = Paginator(proveedores, per_page=per_page)
    try: 
        proveedores = paginator.page(number=page)
    except EmptyPage:
        proveedores = []
    serialized_proveedores = ProveedorDireccionesSerializer(proveedores, many=True)
        
    return Response(serialized_proveedores.data)

@login_required(login_url='user-login')
def obtener_perfiles(request):
    actualizado = False
    empleados_actualizados = []  # Lista para almacenar los usuarios actualizados

    if request.method == 'POST':
        actualizado = True  # Actualizar de mensaje en template
        #url = 'http://127.0.0.1:9000/apiapp/perfiles/'
        #token = 'f36cf2df116c3aeab68b9ee948331f382f5edcc0'
        url = 'https://vordcab.cloud/apiapp/perfiles/'
        token = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
        headers = {
            'Authorization': f'Token {token}'
        }

        # Hacer la solicitud a la API con los encabezados
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Procesar el JSON de la respuesta
            data = response.json()

            # Iterar sobre cada perfil recibido en el JSON
            for perfil in data:
                correo_vordcab = perfil.get('correo_vordcab')
                baja = perfil.get('baja', False)  # Por defecto, es False si no existe
                nivel_data = perfil.get('nivel')  # Obtener datos del nivel
                # Extraer el nivel del JSON, si existe
                if nivel_data and nivel_data.get('nivel') and nivel_data['nivel'].get('nivel'):
                    nivel = nivel_data['nivel']['nivel']
                else:
                    nivel = None

                try:
                    # Buscar al usuario por su correo electrónico
                    usuario = User.objects.get(email=correo_vordcab)
                    custom_user = CustomUser.objects.get(staff=usuario)  # Obtener el CustomUser relacionado

                    # Determinar si se necesita una actualización
                    estado_anterior = usuario.is_active
                    nivel_anterior = custom_user.nivel
                    if baja:
                        usuario.is_active = False
                    else:
                        usuario.is_active = True

                    # Convertir nivel a float si no es None
                    if nivel is not None and custom_user.nivel != float(nivel):
                        custom_user.nivel = float(nivel)

                    # Si hubo un cambio, guardar el usuario y agregarlo a la lista de actualizados
                    if usuario.is_active != estado_anterior or nivel_anterior != custom_user.nivel:
                        usuario.save()
                        custom_user.save()
                        empleados_actualizados.append({
                            'nombre': usuario.get_full_name(),
                            'correo': usuario.email,
                            'activo': usuario.is_active,
                            'activo_anterior':estado_anterior,
                            'nivel': custom_user.nivel,
                            'nivel_anterior': nivel_anterior,
                        })
                
                except User.DoesNotExist:
                    # Si no existe el usuario con ese correo
                    print(f"Usuario con correo {correo_vordcab} no encontrado.")
    
    # Renderizar la página con la tabla actualizada después de procesar la solicitud
    return render(request, 'api/perfiles_lista.html', {'empleados_actualizados': empleados_actualizados,'actualizado': actualizado})