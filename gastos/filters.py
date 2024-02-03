import django_filters
from .models import Solicitud_Gasto
from django_filters import CharFilter, DateFilter
from django.db.models import Q




class Solicitud_Gasto_Filter(django_filters.FilterSet):
    #staff = CharFilter(field_name='staff__staff', lookup_expr='icontains')
    staff = CharFilter(method ='my_filter', label="Search")
    folio = CharFilter(method='filter_id_custom')
    #id = CharFilter(field_name='id', lookup_expr='icontains')
    #proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    #subproyecto = CharFilter(field_name='subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name ='created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Solicitud_Gasto
        fields = ['staff','id','start_date','end_date',]

    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(staff__staff__staff__first_name__icontains = value) | Q(staff__staff__staff__last_name__icontains = value))
    
   
    def filter_folio_custom(self, queryset, name, value):
        if len(value) == 1:
            return queryset.filter(folio=value)
        else:
            return queryset.filter(folio__icontains=value)
