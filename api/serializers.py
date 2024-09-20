from rest_framework import serializers
from dashboard.models import Inventario, Familia, Unidad, Product
from compras.models import Compra, Proveedor, Proveedor_direcciones, Estado, Estatus_proveedor
from requisiciones.models import Requis
from dashboard.models import Order
from user.models import Distrito, Banco


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

class EstatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estatus_proveedor
        fields = ['nombre']

class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estado
        fields = ['nombre']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['razon_social','rfc','nombre_comercial']

class BancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco
        fields = ['nombre']

class ProveedorDireccionesSerializer(serializers.ModelSerializer):
    nombre = ProveedorSerializer(read_only=True)
    distrito = DistritoSerializer(read_only=True)
    estado = EstadoSerializer(read_only=True)
    estatus = EstatusSerializer(read_only = True)
    banco = BancoSerializer(read_only= True)

    class Meta:
        model = Proveedor_direcciones
        fields = ['distrito','nombre','domicilio','telefono','estado','contacto','email','banco','clabe','cuenta','financiamiento','dias_credito','estatus']

class CompraSerializer(serializers.ModelSerializer):
    proveedor = ProveedorDireccionesSerializer(read_only=True)
    req = RequisicionSerializer(read_only=True)
    descargar = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = ['folio','proveedor','req','creada_por','created_at','moneda','cond_de_pago','costo_oc','descargar',]
    
    def get_descargar(self, obj):
        # Retorna la URL del PDF con el ID de la compra
        return f'https://grupovordcab.cloud/api/oc-pdf/{obj.id}/'
    
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