import django_filters
from .models import Product, Proyecto, Subproyecto
from compras.models import Proveedor
from django_filters import CharFilter, DateTimeFilter

class ProductFilter(django_filters.FilterSet):
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='codigo', lookup_expr='icontains')
    familia = CharFilter(field_name='familia__nombre', lookup_expr='icontains')
    subfamilia = CharFilter(field_name='subfamilia__nombre', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['codigo','nombre','familia', 'subfamilia',]

class ProyectoFilter(django_filters.FilterSet):
    id = CharFilter(field_name='id', lookup_expr='icontains')
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    cliente = CharFilter(field_name='cliente', lookup_expr='icontains')
    folio_cotizacion = CharFilter(field_name='folio__cotizacion', lookup_expr='icontains')
    factura = CharFilter(field_name='factura', lookup_expr='icontains')
    status_entrega = CharFilter(field_name='status_de_entrega', lookup_expr='icontains')
    fecha = DateTimeFilter(field_name='created_at', lookup_expr='gte')

    class Meta:
        model = Proyecto
        fields = ['id','nombre','cliente','folio_cotizacion', 'status_entrega','fecha']

class SubproyectoFilter(django_filters.FilterSet):
    id = CharFilter(field_name='id', lookup_expr='icontains')
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    fecha = DateTimeFilter(field_name='created_at', lookup_expr='gte')

    class Meta:
        model = Subproyecto
        fields = ['id','nombre','fecha']


class ProveedorFilter(django_filters.FilterSet):
    razon_social = CharFilter(field_name='razon_social', lookup_expr='icontains')
    rfc = CharFilter(field_name='rfc', lookup_expr='icontains')
    nombre_comercial = CharFilter(field_name='nombre_comercial', lookup_expr='icontains')



    class Meta:
        model = Proveedor
        fields = ['razon_social','rfc','nombre_comercial']