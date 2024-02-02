import django_filters
from dashboard.models import Activo
from django_filters import CharFilter, DateTimeFilter, BooleanFilter
from django.db.models import Q



class ActivoFilter(django_filters.FilterSet):
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    responsable = CharFilter(method ='my_filter', label="Search")
    tipo_activo = CharFilter(field_name='tipo_activo__nombre', lookup_expr='icontains')
    subfamilia = CharFilter(field_name='subfamilia__nombre', lookup_expr='icontains')
    #activo = BooleanFilter()

    class Meta:
        model = Activo
        fields = ['responsable','nombre','tipo_activo', 'subfamilia','activo']

    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(responsable__staff__staff__first_name__icontains = value) | Q(responsable__staff__staff__last_name__icontains = value))