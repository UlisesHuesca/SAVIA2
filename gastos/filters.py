import django_filters
from .models import Solicitud_Gasto, Conceptos_Entradas, Tipo_Gasto
from solicitudes.models import Proyecto, Subproyecto
from django_filters import CharFilter, DateFilter
from django.db.models import Q




class Solicitud_Gasto_Filter(django_filters.FilterSet):
    #staff = CharFilter(field_name='staff__staff', lookup_expr='icontains')
    staff = CharFilter(method ='my_filter', label="Search")
    folio = CharFilter(method='filter_folio_custom')
    solicitado = CharFilter(method = 'solicitado_para', label="Search")
    #id = CharFilter(field_name='id', lookup_expr='icontains')
    #proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    #subproyecto = CharFilter(field_name='subproyecto__nombre', lookup_expr='icontains')
    tipo = django_filters.ModelChoiceFilter(queryset=Tipo_Gasto.objects.all(), label="Tipo Gasto")
    start_date = DateFilter(field_name ='created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at', lookup_expr='lte')
    #Busqueda parcial para la parte de gasto
    proyecto = django_filters.ModelChoiceFilter(queryset=Proyecto.objects.filter(activo=True, complete=True), method='filter_by_proyecto', label="Proyecto")
    subproyecto = django_filters.ModelChoiceFilter(queryset=Subproyecto.objects.all(), method='filter_by_subproyecto', label="Subproyecto")

    class Meta:
        model = Solicitud_Gasto
        fields = ['staff','folio','start_date','end_date','tipo','proyecto','subproyecto']

    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(staff__staff__staff__first_name__icontains = value) | Q(staff__staff__staff__last_name__icontains = value))
    
    def solicitado_para(self, queryset, name, value):
        return queryset.filter(Q(colaborador__staff__staff__first_name__icontains = value) | Q(colaborador__staff__staff__last_name__icontains = value))
    
   
    def filter_folio_custom(self, queryset, name, value):
        if len(value) == 1:
            return queryset.filter(folio=value)
        else:
            return queryset.filter(folio__icontains=value)
    def filter_by_proyecto(self, queryset, name, value):
        if value:
            return queryset.filter(articulos__proyecto=value).distinct()
        return queryset

    def filter_by_subproyecto(self, queryset, name, value):
        if value:
            return queryset.filter(articulos__subproyecto=value).distinct()
        return queryset
    
class Conceptos_EntradasFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='concepto_material__producto__nombre', lookup_expr='icontains')
    almacenista = CharFilter(method='almacenistaa', lookup_expr='icontains')
    folio = CharFilter(field_name='entrada__gasto__gasto__folio', lookup_expr='icontains')
    solicitado = CharFilter(method='solicitadoo', lookup_expr='icontains')

    class Meta:
        model = Conceptos_Entradas
        fields = ['concepto_material','entrada',]

    def almacenistaa(self, queryset, name, value):
        return queryset.filter(Q(entrada__almacenista__staff__staff__first_name__icontains = value) | Q(entrada__almacenista__staff__staff__last_name__icontains = value))
    
    def solicitadoo(self, queryset, name, value):
        return queryset.filter(Q(entrada__gasto__staff__staff__staff__first_name__icontains = value) | Q(entrada__gasto__staff__staff__staff__last_name__icontains = value))