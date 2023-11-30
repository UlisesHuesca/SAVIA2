import django_filters
from .models import Activo
from django_filters import CharFilter, DateTimeFilter, BooleanFilter

class ActivoFilter(django_filters.FilterSet):
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='codigo', lookup_expr='icontains')
    familia = CharFilter(field_name='familia__nombre', lookup_expr='icontains')
    subfamilia = CharFilter(field_name='subfamilia__nombre', lookup_expr='icontains')
    activo = BooleanFilter()

    class Meta:
        model = Product
        fields = ['codigo','nombre','familia', 'subfamilia','activo']