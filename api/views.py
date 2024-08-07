from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from dashboard.models import Inventario 
from compras.models import Compra
from .serializers import InventarioSerializer, CompraSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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