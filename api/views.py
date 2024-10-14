from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from dashboard.models import Inventario 
from compras.models import Compra, Proveedor_direcciones, Moneda
from solicitudes.models import Proyecto, Subproyecto
from user.models import Profile 
from .serializers import InventarioSerializer, CompraSerializer, ProveedorDireccionesSerializer, ProyectoSerializer, SubProyectoSerializer, MonedaSerializer, ProfileSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
import requests
from django.contrib.auth.models import User
from user.models import CustomUser, Empresa
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from compras.views import generar_pdf
from rest_framework import status

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def monedas_api(request):
    monedas = Moneda.objects.all()
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        monedas = monedas.order_by(ordering)
        
    
    serialized_monedas = MonedaSerializer(monedas, many=True)

    paginator = Paginator(monedas, per_page=per_page)
    try: 
        monedas = paginator.page(number=page)
    except EmptyPage:
        monedas = []
        
    return Response(serialized_monedas.data)

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def profiles_api(request):
    profiles = Profile.objects.all()
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        profiles = profiles.order_by(ordering)
        
    
    serialized_profiles = ProfileSerializer(profiles, many=True)

    paginator = Paginator(profiles, per_page=per_page)
    try: 
        profiles = paginator.page(number=page)
    except EmptyPage:
        profiles = []
        
    return Response(serialized_profiles.data)

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def proyectos_api(request):
    proyectos = Proyecto.objects.filter(activo = True)
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        proyectos = Proyecto.order_by(ordering)
        
    
    serialized_proyectos = ProyectoSerializer(proyectos, many=True)

    paginator = Paginator(proyectos, per_page=per_page)
    try: 
        proyectos = paginator.page(number=page)
    except EmptyPage:
        proyectos = []
        
    return Response(serialized_proyectos.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def subproyectos_api(request):
    subproyectos = Subproyecto.objects.filter(activo = True)
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 20)
    #
    ordering = request.query_params.get('ordering')

    if ordering:
        subproyectos = Subproyecto.order_by(ordering)
        
    
    serialized_subproyectos = SubProyectoSerializer(subproyectos, many=True)

    paginator = Paginator(subproyectos, per_page=per_page)
    try: 
        subproyectos = paginator.page(number=page)
    except EmptyPage:
        subproyectos = []
        
    return Response(serialized_subproyectos.data)



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

#url = 'https://vordcab.cloud/apiapp/perfiles/'
#token = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
@login_required(login_url='user-login')
def obtener_perfiles(request):
    actualizado = False
    empleados_actualizados = []  # Lista para almacenar los usuarios actualizados

    if request.method == 'POST':
        actualizado = True  # Actualizar mensaje en template
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
                empresa = perfil.get('empresa', {}).get('empresa')

                if empresa == 'VORDCAB':
                    empresa = 'Grupo Vordcab S.A. de C.V.'

                # Extraer el nivel del JSON, si existe
                nivel = nivel_data['nivel']['nivel'] if nivel_data and nivel_data.get('nivel') else None

                try:
                    # Buscar al usuario por su correo electrónico
                    usuario = User.objects.get(email=correo_vordcab)
                    custom_user = CustomUser.objects.get(staff=usuario)  # Obtener el CustomUser relacionado

                    # Determinar si se necesita una actualización
                    estado_anterior = usuario.is_active
                    nivel_anterior = custom_user.nivel
                    empresa_anterior = custom_user.empresa.nombre if custom_user.empresa else None

                    cambio = False  # variable que indica si hubo un cambio

                    # Actualizar el estado si ha cambiado
                    if baja:
                        if usuario.is_active:
                            usuario.is_active = False
                            cambio = True
                    else:
                        if not usuario.is_active:
                            usuario.is_active = True
                            cambio = True

                    # Convertir nivel a float si no es None y ha cambiado
                    if nivel is not None and custom_user.nivel != float(nivel):
                        custom_user.nivel = float(nivel)
                        cambio = True

                    # Compara la empresa actual con la empresa del JSON
                    if empresa and (empresa_anterior is None or empresa_anterior.strip().lower() != empresa.strip().lower()):
                        try:
                            nueva_empresa = Empresa.objects.get(nombre=empresa)
                            custom_user.empresa = nueva_empresa
                            cambio = True
                        except Empresa.DoesNotExist:
                            print(f"Empresa con nombre {empresa} no encontrada.")

                    # Si hubo un cambio, guardar el usuario y agregarlo a la lista de actualizados
                    if cambio:
                        usuario.save()
                        custom_user.save()
                        empleados_actualizados.append({
                            'nombre': usuario.get_full_name(),
                            'correo': usuario.email,
                            'activo': usuario.is_active,
                            'activo_anterior': estado_anterior,
                            'nivel': custom_user.nivel,
                            'nivel_anterior': nivel_anterior,
                            'empresa': custom_user.empresa.nombre if custom_user.empresa else None,
                            'empresa_anterior': empresa_anterior,
                        })
                
                except User.DoesNotExist:
                    # Si no existe el usuario con ese correo
                    print(f"Usuario con correo {correo_vordcab} no encontrado.")

    return render(request, 'api/perfiles_lista.html', {'empleados_actualizados': empleados_actualizados, 'actualizado': actualizado})

@api_view(['GET'])
@authentication_classes([TokenAuthentication]) #Si quieres decargar el pdf desde el nodo desabilita este decorador de token
@permission_classes([IsAuthenticated])
def descargar_pdf_oc(request, pk):
    try:
        # Intentar obtener la orden de compra por su id
        compra = Compra.objects.get(id=pk)
    except Compra.DoesNotExist:
        # Si no existe la OC, devolver un mensaje de éxito con estado 200 ya que si uso 404 me manda al middleware
        return Response(
            {"detail": "La OC que intenta traer no existe, pero la solicitud fue procesada correctamente."},
            status=status.HTTP_200_OK
        )

    # Generar el PDF si la OC existe
    buf = generar_pdf(compra)

    # Devolver el PDF como respuesta
    return FileResponse(buf, as_attachment=True, filename='oc_' + str(compra.folio) + '.pdf')