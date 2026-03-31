import django_filters
from . import models

class Costos_Filter(django_filters.FilterSet):
    distrito = django_filters.CharFilter(field_name='distrito__nombre', lookup_expr='icontains')
    contrato = django_filters.CharFilter(field_name='contrato__nombre', lookup_expr='icontains')
    tipo = django_filters.CharFilter(field_name='tipo__nombre', lookup_expr='icontains')
    fecha = django_filters.DateFilter(field_name='fecha', lookup_expr='icontains')

    class Meta:
        model = models.Solicitud_Costos
        fields = ['distrito','contrato','tipo','fecha']

class Depreciaciones_Filter(django_filters.FilterSet):
    distrito = django_filters.CharFilter(field_name='distrito__nombre', lookup_expr='icontains')
    contrato = django_filters.CharFilter(field_name='contrato__nombre', lookup_expr='icontains')
    mes_inicial = django_filters.DateFilter(field_name='mes_inicial', lookup_expr='icontains')

    class Meta:
        model = models.Depreciaciones
        fields = ['distrito','contrato','mes_inicial']