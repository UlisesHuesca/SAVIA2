import django_filters
from dashboard.models import ArticulosparaSurtir
from requisiciones.models import Salidas
from entradas.models import EntradaArticulo
from django_filters import CharFilter, DateFilter
from django.db.models import Q

class ArticulosparaSurtirFilter(django_filters.FilterSet):
    solicitud = CharFilter(field_name='articulos__orden__folio', lookup_expr='icontains')
    producto = CharFilter(field_name='articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='articulos__producto__producto__codigo', lookup_expr='icontains')
    #nombre = CharFilter(field_name='articulos__orden__staff__staff__first_name', lookup_expr='icontains')
    nombre = CharFilter(method ='my_custom_filter', label="Search")
    #apellido =CharFilter(field_name='articulos__orden__staff__staff__last_name', lookup_expr='icontains')
    proyecto = CharFilter(field_name='articulos__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='articulos__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'articulos__orden__approved_at', lookup_expr='gte')
    end_date = DateFilter(field_name='articulos__orden__approved_at',lookup_expr='lte')

    class Meta:
        model = ArticulosparaSurtir
        fields = ['solicitud','producto','codigo','nombre','proyecto','subproyecto','start_date','end_date',]

    def my_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(articulos__orden__staff__staff__first_name__icontains = value) | Q(articulos__orden__staff__staff__last_name__icontains=value))


class SalidasFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='producto__articulos__producto__producto__codigo', lookup_expr='icontains')
    nombre = CharFilter(field_name='producto__articulos__orden__staff', lookup_expr='icontains')
    proyecto = CharFilter(field_name='producto__articulos__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='producto__articulos__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')

    class Meta:
        model = Salidas
        fields = ['producto','codigo','nombre','proyecto','subproyecto','start_date','end_date',]

class EntradasFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='articulo_comprado__producto__producto__articulos__producto__producto__codigo', lookup_expr='icontains')
    nombre = CharFilter(field_name='articulo_comprado__producto__articulos__orden__staff', lookup_expr='icontains')
    proyecto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')

    class Meta:
        model = EntradaArticulo
        fields = ['producto','codigo','nombre','proyecto','subproyecto','start_date','end_date',]
