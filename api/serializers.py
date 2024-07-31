from rest_framework import serializers
from dashboard.models import Inventario, Familia, Unidad, Product
from compras.models import Compra, Proveedor, Proveedor_direcciones
from requisiciones.models import Requis
from dashboard.models import Order
from user.models import Distrito


class DistritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distrito
        fields = ['nombre']

class OrdenSerializer(serializers.ModelSerializer):
    distrito = DistritoSerializer(read_only = True)

    class Meta:
        model = Order
        fields = ['distrito']

class RequisicionSerializer(serializers.ModelSerializer):
    orden = OrdenSerializer(read_only = True)

    class Meta:
        model = Requis
        fields = ['orden']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['razon_social']

class ProveedorDireccionesSerializer(serializers.ModelSerializer):
    nombre = ProveedorSerializer(read_only=True)
    
    class Meta:
        model = Proveedor_direcciones
        fields = ['nombre']

class CompraSerializer(serializers.ModelSerializer):
    proveedor = ProveedorDireccionesSerializer(read_only=True)
    req = RequisicionSerializer(read_only=True)

    class Meta:
        model = Compra
        fields = ['folio','proveedor','req','creada_por','created_at','moneda','cond_de_pago','costo_oc']

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Familia
        fields = ('nombre',)

class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ('nombre',)

class ProductSerializer(serializers.ModelSerializer):
    familia = FamiliaSerializer()
    unidad = UnidadSerializer()

    class Meta:
        model = Product
        fields = ('codigo', 'nombre', 'unidad', 'familia')


class InventarioSerializer(serializers.ModelSerializer):
    producto = ProductSerializer()

    class Meta:
        model = Inventario
        fields = '__all__'