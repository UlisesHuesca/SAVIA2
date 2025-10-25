from rest_framework import serializers
from dashboard.models import Inventario, Familia, Unidad, Product
from solicitudes.models import Proyecto, Subproyecto
from compras.models import Compra, Proveedor, Proveedor_direcciones, Estado, Estatus_proveedor, Moneda
from requisiciones.models import Requis
from dashboard.models import Order
from user.models import Distrito, Banco, Profile, CustomUser
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name','last_name']

class Custom_UserSerializer(serializers.ModelSerializer):
    staff = UserSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'staff','cuenta_bancaria', 'clabe','banco']

class ProfileSerializer(serializers.ModelSerializer):
    staff = Custom_UserSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = ['id','staff','distritos','st_activo']


class ProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proyecto
        fields = ['id','nombre']

class SubProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subproyecto
        fields = ['id','nombre']

class DistritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distrito
        fields = ['id','nombre']

class OrdenSerializer(serializers.ModelSerializer):
    distrito = DistritoSerializer(read_only = True)

    class Meta:
        model = Order
        fields = ['id','distrito','proyecto','subproyecto']

class RequisicionSerializer(serializers.ModelSerializer):
    orden = OrdenSerializer(read_only = True)

    class Meta:
        model = Requis
        fields = ['id','orden']

class EstatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estatus_proveedor
        fields = ['id','nombre']

class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estado
        fields = ['nombre']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['id','razon_social','rfc']
        

class BancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco
        fields = ['id','nombre']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id','nombre']

class ProveedorDireccionesSerializer(serializers.ModelSerializer):
    #nombre = ProveedorSerializer(read_only=True)
    #distrito = DistritoSerializer(read_only=True)
    #estado = EstadoSerializer(read_only=True)
    #estatus = EstatusSerializer(read_only = True)
    #banco = BancoSerializer(read_only= True)

    class Meta:
        model = Proveedor_direcciones
        fields = ['id','distrito','nombre','domicilio','telefono','estado','contacto','email','banco','clabe','cuenta','financiamiento','dias_credito','estatus']

class CompraSerializer(serializers.ModelSerializer):
    #proveedor = ProveedorDireccionesSerializer(read_only=True)
    #req = RequisicionSerializer(read_only=True)
    descargar = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = ['id','folio','proveedor','req','creada_por','created_at','moneda','cond_de_pago','costo_oc','descargar',]
    
    def get_descargar(self, obj):
        # Retorna la URL del PDF con el ID de la compra
        return f'https://grupovordcab.cloud/api/oc-pdf/{obj.id}/'
        #return f'http://127.0.0.1:8000/api/oc-pdf/{obj.id}/'
    
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