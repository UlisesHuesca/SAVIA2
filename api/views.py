from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from dashboard.models import Inventario 
from compras.models import Compra
from .serializers import InventarioSerializer, CompraSerializer
# Create your views here.


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getData(request):
    inventario = Inventario.objects.all()
    serializer = InventarioSerializer(inventario, many=True)
    return Response(serializer.data)


class CompraAPI(generics.ListAPIView):
    compras = Compra.objects.all()
    serializer_class = CompraSerializer