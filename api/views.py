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

def obtener_perfiles(request):
    url = 'https://vordcab.cloud/apiapp/perfiles/'
    token = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
    # Encabezados para la solicitud con el token
    headers = {
        'Authorization': f'Token {token}'
    }

    # Hacer la solicitud a la API con los encabezados
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Procesar el JSON de la respuesta
        data = response.json()

        # Pasar los datos al template
        return render(request, 'api/perfiles_lista.html', {'data': data})
    else:
        return JsonResponse({'error': 'No se pudo obtener los datos de la API'}, status=response.status_code)