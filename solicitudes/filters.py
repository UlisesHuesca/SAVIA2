import django_filters
from dashboard.models import Inventario, Order, ArticulosOrdenados
from django_filters import CharFilter, DateFilter
from django.db.models import Q


class InventoryFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='producto__codigo', lookup_expr='icontains')


    class Meta:
        model = Inventario
        fields = ['producto','codigo',]


class InventarioFilter(django_filters.FilterSet):
    codigo = CharFilter(field_name='producto__codigo', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__nombre', lookup_expr='icontains')
    familia = CharFilter(field_name='producto__familia__nombre', lookup_expr='icontains')
    ubicacion = CharFilter(field_name='ubicacion', lookup_expr='icontains')
    estante = CharFilter(field_name='estante', lookup_expr='icontains')

    class Meta:
        model = Inventario
        fields = ['producto','codigo','familia','ubicacion','estante',]

class SolicitudesFilter(django_filters.FilterSet):
    #staff = CharFilter(field_name='staff__staff', lookup_expr='icontains')
    staff = CharFilter(method ='my_filter', label="Search")
    folio = CharFilter(field_name='folio', lookup_expr='icontains')
    proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name ='created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Order
        fields = ['staff','folio','proyecto','start_date','end_date',]

    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(staff__staff__first_name__icontains = value) | Q(staff__staff__last_name__icontains = value))



class SolicitudesProdFilter(django_filters.FilterSet):
    #staff = CharFilter(field_name='orden__staff__staff', lookup_expr='icontains')
    staff = CharFilter(method ='the_filter', label="Search")
    folio = CharFilter(field_name='orden__folio', lookup_expr='icontains')
    proyecto = CharFilter(field_name='orden__proyecto__nombre', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__producto__nombre',lookup_expr='icontains')
    start_date = DateFilter(field_name='orden__created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='orden__created_at', lookup_expr='lte')

    class Meta:
        model = ArticulosOrdenados
        fields = ['staff','folio','proyecto','producto','start_date','end_date',]

    def the_filter(self, queryset, name, value):
        return queryset.filter(Q(orden__staff__staff__first_name__icontains = value) | Q(orden__staff__staff__last_name__icontains = value))


