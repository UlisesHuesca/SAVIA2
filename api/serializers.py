from rest_framework import serializers
from django.db.models import DateField, Avg
from django.db.models.functions import Coalesce
from dashboard.models import Inventario, Familia, Unidad, Product
from solicitudes.models import Proyecto, Subproyecto
from tesoreria.models import Pago
from compras.models import Compra, Proveedor, Proveedor_direcciones, Estado, Estatus_proveedor, Moneda, ArticuloComprado
from requisiciones.models import Requis, ArticulosRequisitados
from dashboard.models import Order, ArticulosparaSurtir, ArticulosOrdenados
from user.models import Distrito, Banco, Profile, CustomUser
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

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
    #distrito = DistritoSerializer(read_only = True)

    class Meta:
        model = Order
        fields = ['id','distrito','proyecto','subproyecto']

class Articulos_Ordenados_Serializer(serializers.ModelSerializer):
    class Meta:
        model = ArticulosOrdenados
        fields = ['id','orden','producto','cantidad']



class Articulos_para_Surtir_Serializer(serializers.ModelSerializer):

    class Meta:
        model = ArticulosparaSurtir
        fields = ['id','articulos','cantidad','surtir']

class RequisicionSerializer(serializers.ModelSerializer):
    #orden = OrdenSerializer(read_only = True)

    class Meta:
        model = Requis
        fields = '__all__'

class Requisicion_Serializer(serializers.ModelSerializer):
    orden = OrdenSerializer(read_only = True)

    class Meta:
        model = Requis
        fields = ['id','folio','orden']

class Articulos_Requisitados_Serializer(serializers.ModelSerializer):

    class Meta:
        model = ArticulosRequisitados
        fields = ['id','producto','req','cantidad','cantidad_comprada']

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
        fields = '__all__'


class BancoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banco
        fields = ['id','nombre']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id','nombre']

class ProveedorDireccionesSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = Proveedor_direcciones
        fields = ['id','distrito','nombre','domicilio','telefono','estado','contacto','email','banco','clabe','cuenta','financiamiento','dias_credito','estatus']

class CompraSerializer(serializers.ModelSerializer):
    descargar = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = ['id','folio','proveedor','creada_por','req','created_at','moneda','cond_de_pago','costo_oc','pagada','descargar']
    
    def get_descargar(self, obj):
        # Retorna la URL del PDF con el ID de la compra
        return f'https://grupovordcab.cloud/api/oc-pdf/{obj.id}/'
        #return f'http://127.0.0.1:8000/api/oc-pdf/{obj.id}/'
    

class Compra_tabla_Serializer(serializers.ModelSerializer):
    #descargar = serializers.SerializerMethodField()
    folio_req = serializers.IntegerField(source='req.folio', read_only=True)
    folio_solicitud = serializers.IntegerField(source='req.orden.folio', read_only=True)
    distrito = serializers.CharField(source='req.orden.distrito.nombre', read_only=True)
    proyecto = serializers.CharField(source='req.orden.proyecto.nombre', read_only=True, allow_null = True, default = None)
    subproyecto = serializers.CharField(source='req.orden.subproyecto.nombre', read_only=True, allow_null = True, default = None)
    area = serializers.SerializerMethodField()
    solicitante = serializers.SerializerMethodField()
    creador = serializers.SerializerMethodField()  # nuevo campo
    created_at = serializers.DateTimeField(read_only=True, format='%d/%m/%Y')
    req_autorizada_fecha = serializers.DateField(source='req.approved_at', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre.razon_social', read_only=True)
    status_proveedor = serializers.CharField(source='proveedor.estatus.nombre', read_only=True)
    cond_de_pago = serializers.CharField(source='cond_de_pago.nombre', read_only=True)
    costo_oc = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    monto_pagado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    fecha_pago = serializers.SerializerMethodField()
    estado_autorizacion = serializers.SerializerMethodField()
    tipo_producto = serializers.SerializerMethodField()
    dias_entrega = serializers.IntegerField(source='dias_de_entrega', read_only=True)
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    tipo_cambio = serializers.SerializerMethodField()
    entrega = serializers.CharField(source='entrada_completa', read_only=True)
    tiene_facturas = serializers.SerializerMethodField()
    activo_fijo = serializers.CharField(source='req.orden.activo.nombre', read_only=True, allow_null = True, default = None)
    total_pesos = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = ['folio','folio_req','folio_solicitud','distrito','proyecto','subproyecto','area', 'solicitante','creador','created_at',
                  'req_autorizada_fecha','proveedor_nombre','status_proveedor','cond_de_pago','costo_oc','monto_pagado','pagada',
                  'fecha_pago','estado_autorizacion','tipo_producto','dias_entrega','moneda_nombre','tipo_cambio', 'entrega', 
                  'tiene_facturas', 'activo_fijo','total_pesos'
                  ]
    
    def get_solicitante(self, obj):
        try:
            staff = obj.req.orden.staff.staff.staff
            return f'{staff.first_name} {staff.last_name}'
        except AttributeError:
            return 'Desconocido'
        
    def get_creador(self, obj):
        """
        Devuelve el nombre y apellido del usuario que creó la compra.
        Accede a creada_por.staff.staff.first_name y last_name.
        """
        try:
            staff = obj.creada_por.staff.staff
            return f"{staff.first_name} {staff.last_name}".strip()
        except AttributeError:
            return None
        
    def get_fecha_pago(self, obj):
        pagos = Pago.objects.filter(
            oc=obj, hecho=True
        ).annotate(
            fecha_orden=Coalesce('pagado_real', 'pagado_date', output_field=DateField())
        ).order_by('pagado_date')

        if pagos.exists():
            primer_pago = pagos.first()
            primera_fecha_pago = (
                primer_pago.pagado_real or primer_pago.pagado_date
            )
            return primera_fecha_pago.strftime('%d/%m/%Y') if primera_fecha_pago else ""
        return ""
    
    def get_estado_autorizacion(self, obj):
        a1 = getattr(obj, 'autorizado1', None)
        a2 = getattr(obj, 'autorizado2', None)

        if a2 is True:
            return 'Autorizado'
        if a2 is False or a1 is False:
            return 'Cancelado'
        return 'Pendiente Autorización'
    
    def get_tipo_producto(self, obj):
        articulos = obj.articulocomprado_set.all()  # <-- relación sin related_name

        if not articulos.exists():
            return ""

        todos_servicios = all(
            a.producto.producto.articulos.producto.producto.servicio
            for a in articulos
        )
        ningun_servicio = all(
            not a.producto.producto.articulos.producto.producto.servicio
            for a in articulos
        )

        if todos_servicios:
            return "SERVICIOS"
        elif ningun_servicio:
            return "PRODUCTOS"
        return "PRODUCTO/SERVICIOS"
    
    def get_tiene_facturas(self, obj):
        # Usa el related_name correcto según tu modelo
        try:
            return 'Sí' if obj.facturas.exists() else 'No'
        except AttributeError:
            # Si no existe related_name 'facturas'
            return 'Sí' if obj.factura_set.exists() else 'No'
        
    def get_tipo_cambio(self, obj):
        """
        Devuelve el tipo de cambio como Decimal (o None si no hay valor válido).
        Usa el promedio de pagos hechos; si no hay, usa el de la OC.
        """
        avg_pago = (Pago.objects
                    .filter(oc=obj, hecho=True)
                    .aggregate(avg=Avg('tipo_de_cambio'))['avg'])

        # Prioriza el promedio; si no hay, toma el de la OC
        tipo = avg_pago if avg_pago not in (None, 0) else obj.tipo_de_cambio

        if tipo in (None, 0, Decimal('0')):
            return None

        try:
            tipo = Decimal(tipo)
        except (InvalidOperation, TypeError):
            return None

        # Redondeo opcional a 4 decimales (manteniendo Decimal)
        return tipo.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def get_total_pesos(self, obj):
        """
        Multiplica costo_oc * tipo_de_cambio.
        Si no hay tipo, devuelve costo_oc tal cual.
        Retorna Decimal (o podrías castear a float/str si tu serializer lo requiere).
        """
        tipo = self.get_tipo_cambio(obj)

        try:
            costo = Decimal(obj.costo_oc or 0)
        except (InvalidOperation, TypeError):
            costo = Decimal('0')

        if not tipo:
            return costo  # sin tipo: regresa costo en la moneda base

        total = (tipo * costo).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return total
    
      # 🔹 Aquí definimos el método seguro para 'area'
    def get_area(self, obj):
        try:
            return obj.req.orden.operacion.nombre
        except Exception:
            return None

    #def get_descargar(self, obj):
        # Retorna la URL del PDF con el ID de la compra
    #    return f'https://grupovordcab.cloud/api/oc-pdf/{obj.id}/'
        #return f'http://127.0.0.1:8000/api/oc-pdf/{obj.id}/'

class Articulo_Comprado_Serializer(serializers.ModelSerializer):

    class Meta:
        model = ArticuloComprado
        fields = ['id','producto','oc','cantidad','entrada_completa','precio_unitario']
    
  
    
class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Familia
        fields = ('nombre',)

class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ('nombre',)

class ProductSerializer(serializers.ModelSerializer):
    #familia = FamiliaSerializer()
    #unidad = UnidadSerializer()

    class Meta:
        model = Product
        fields = ('id', 'codigo', 'nombre','servicio')


class InventarioSerializer(serializers.ModelSerializer):
    #producto = ProductSerializer()

    class Meta:
        model = Inventario
        fields = '__all__'