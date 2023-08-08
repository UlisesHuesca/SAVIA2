import django_filters
from requisiciones.models import ArticulosRequisitados
from .models import Compra, ArticuloComprado
from django_filters import CharFilter, DateFilter
from django.db.models import Q

class CompraFilter(django_filters.FilterSet):
    proveedor = CharFilter(field_name='proveedor__nombre__razon_social', lookup_expr='icontains')
    creada_por = CharFilter(field_name='creada_por', lookup_expr='icontains')
    req = CharFilter(field_name='req__id', lookup_expr='icontains')
    proyecto = CharFilter(field_name='req__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='req__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')
    costo_oc = CharFilter(field_name='costo_oc', lookup_expr='icontains')
    id = CharFilter(field_name='id', lookup_expr='icontains')

    class Meta:
        model = Compra
        fields = ['proveedor','creada_por','req','proyecto','subproyecto','start_date','end_date', 'costo_oc', 'id',]

class ArticuloCompradoFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    oc = CharFilter(field_name='oc__id', lookup_expr='icontains')

    class Meta:
        model = ArticuloComprado
        fields = ['producto','oc']

class ArticulosRequisitadosFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')

    class Meta:
        model = ArticulosRequisitados
        fields = ['producto']

class HistoricalArticuloCompradoFilter(django_filters.FilterSet):
    history_id = CharFilter(field_name='history_id', lookup_expr='icontains')
    history_user = CharFilter(method='nombre', lookup_expr='icontains')
    history_type = CharFilter(field_name='history_type', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    oc = CharFilter(field_name ='oc__id',lookup_expr='icontains')
    start_date = DateFilter(field_name='history_date', lookup_expr='gte')
    end_date = DateFilter(field_name='history_date', lookup_expr='lte')

    class Meta:
        model = ArticuloComprado.history.model
        fields = ['history_id','history_user','producto','oc','start_date','end_date']
    
    def nombre(self, queryset, name, value):
        return queryset.filter(Q(history_user__first_name__icontains = value) | Q(history_user__last_name__icontains = value))