import django_filters
from .models import Solicitud_Viatico
from django_filters import CharFilter, DateFilter
from django.db.models import Q


class Solicitud_Viatico_Filter(django_filters.FilterSet):
    #staff = CharFilter(field_name='staff__staff', lookup_expr='icontains')
    staff = CharFilter(method ='my_filter', label="Search")
    id = CharFilter(field_name='id', lookup_expr='icontains')
    proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name ='created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Solicitud_Viatico
        fields = ['staff','id','proyecto','subproyecto','start_date','end_date',]
    
    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(colaborador__staff__first_name__icontains = value) | Q(colaborador__staff__last_name__icontains = value))