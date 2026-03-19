import django_filters
from . import models

class Costos_Form(django_filters.FilterSet):
    distrito = django_filters.CharFilter(field_name='distrito__nombre', lookup_expr='icontains')
    contrato = django_filters.CharFilter(field_name='contrato__folio', lookup_expr='icontains')
    tipo = django_filters.CharFilter(field_name='tipo__nombre', lookup_expr='icontains')
    fecha = django_filters.DateFilter(field_name='fecha', lookup_expr='icontains')

    class Meta:
        model = models.Solicitud_Costos
        fields = ['distrito','contrato','tipo','fecha']