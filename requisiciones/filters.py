import django_filters
from dashboard.models import ArticulosparaSurtir
from requisiciones.models import Salidas, Devolucion, Requis, ArticulosRequisitados
from entradas.models import EntradaArticulo
from django_filters import CharFilter, DateFilter
from django.db.models import Q

class RequisFilter(django_filters.FilterSet):
    requisicion = CharFilter(field_name='folio', lookup_expr='icontains')
    solicitud = CharFilter(field_name='orden__folio', lookup_expr='icontains')
    solicitante = CharFilter(method ='my_custom_filter', label="Search")
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')
    start_approved = DateFilter(field_name = 'approved_at', lookup_expr='gte')
    end_approved = DateFilter(field_name='approved_at',lookup_expr='lte')


    class Meta:
        model = Requis
        fields = ['requisicion','solicitud','solicitante','start_date','end_date','start_approved','end_approved']

    def my_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(orden__staff__staff__staff__first_name__icontains = value) | Q(orden__staff__staff__staff__last_name__icontains=value))
    
class RequisProductosFilter(django_filters.FilterSet):
    requisicion = CharFilter(field_name='req__folio', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    solicitud = CharFilter(field_name='req__orden__folio', lookup_expr='icontains')
    solicitante = CharFilter(method ='my_custom_filter', label="Search")
    start_date = DateFilter(field_name = 'req__created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='req__created_at',lookup_expr='lte')
    start_approved = DateFilter(field_name = 'req__approved_at', lookup_expr='gte')
    end_approved = DateFilter(field_name='req__approved_at',lookup_expr='lte')


    class Meta:
        model = ArticulosRequisitados
        fields = ['requisicion','producto','solicitud','solicitante','start_date','end_date','start_approved','end_approved']

    def my_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(req__orden__staff__staff__staff__first_name__icontains = value) | Q(req__orden__staff__staff__staff__last_name__icontains=value))

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
        return queryset.filter(Q(articulos__orden__staff__staff__staff__first_name__icontains = value) | Q(articulos__orden__staff__staff__staff__last_name__icontains=value))


class SalidasFilter(django_filters.FilterSet):
    vale = CharFilter(field_name='vale_salida__folio', lookup_expr='icontains')
    solicitud = CharFilter(field_name='vale_salida__solicitud__folio', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='producto__articulos__producto__producto__codigo', lookup_expr='icontains')
    nombre = CharFilter(method ='my_custom_filter', label="Search")
    proyecto = CharFilter(field_name='producto__articulos__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='producto__articulos__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')

    class Meta:
        model = Salidas
        fields = ['vale','solicitud','producto','codigo','nombre','proyecto','subproyecto','start_date','end_date',]
    
    def my_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(producto__articulos__orden__staff__staff__staff__first_name__icontains = value) | Q(producto__articulos__orden__staff__staff__staff__last_name__icontains=value))

class EntradasFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    folio = CharFilter(field_name = 'articulo_comprado__oc__folio', lookup_expr='icontains')
    folio_solicitud = CharFilter(field_name = 'articulo_comprado__oc__req__orden__folio', lookup_expr='icontains')
    codigo = CharFilter(field_name='articulo_comprado__producto__producto__articulos__producto__producto__codigo', lookup_expr='icontains')
    nombre = CharFilter(method ='my_custom_filter', label="Search")
    proyecto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='articulo_comprado__producto__producto__articulos__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')

    class Meta:
        model = EntradaArticulo
        fields = ['producto','folio','codigo','nombre','proyecto','subproyecto','start_date','end_date','folio_solicitud']

    def my_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(articulo_comprado__producto__articulos__orden__staff__staff__first_name__icontains = value) | Q(articulo_comprado__producto__articulos__orden__staff__staff__last_name__icontains=value))

class DevolucionFilter(django_filters.FilterSet):
    solicitud = CharFilter(method='solicitante_custom_filter', lookup_expr='icontains')
    almacenista = CharFilter(method='almacenista_custom_filter', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')
    inicio = DateFilter(field_name = 'fecha', lookup_expr='gte')
    fin =  DateFilter(field_name='fecha',lookup_expr='lte')
    #fecha = DateFilter(field_name='created_at',lookup_expr='lte')
    #hora = models.TimeField(null=True)

    class Meta:
        model = Devolucion
        fields = ['solicitud','almacenista','start_date','end_date','fecha']

    def solicitante_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(solicitud__staff__staff__staff__first_name__icontains = value) | Q(solicitud__staff__staff__staff__last_name__icontains=value))

    def almacenista_custom_filter(self, queryset, name, value):
        return queryset.filter(Q(almacenista__staff__staff__first_name__icontains = value) | Q(almacenista__staff__staff__last_name__icontains=value))
    

class HistoricalSalidasFilter(django_filters.FilterSet):
    history_id = CharFilter(field_name='history_id', lookup_expr='icontains')
    history_user = CharFilter(method='nombre', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='producto__articulos__producto__producto__codigo', lookup_expr='icontains')
    start_date = DateFilter(field_name='history_date', lookup_expr='gte')
    end_date = DateFilter(field_name='history_date', lookup_expr='lte')
    distrito = CharFilter(field_name='vale_salida__solicitud__distrito__nombre', lookup_expr='icontains')

    class Meta:
        model = Salidas.history.model
        fields = ['history_id','history_user','producto','start_date','end_date', 'codigo','distrito']

    def nombre(self, queryset, name, value):
        return queryset.filter(Q(history_user__first_name__icontains = value) | Q(history_user__last_name__icontains = value))
    
class Historical_articulos_surtir_filter(django_filters.FilterSet):
    history_id = CharFilter(field_name='history_id', lookup_expr='icontains')
    history_user = CharFilter(method='nombre', lookup_expr='icontains')
    producto = CharFilter(field_name='articulos__producto__producto__nombre', lookup_expr='icontains')
    codigo = CharFilter(field_name='articulos__producto__producto__codigo', lookup_expr='icontains')
    start_date = DateFilter(field_name='history_date', lookup_expr='gte')
    end_date = DateFilter(field_name='history_date', lookup_expr='lte')
    distrito = CharFilter(field_name='articulos__orden__distrito__nombre', lookup_expr='icontains')

    class Meta:
        model = ArticulosparaSurtir.history.model
        fields = ['history_id','history_user','producto','start_date','end_date', 'codigo','distrito']

    def nombre(self, queryset, name, value):
        return queryset.filter(Q(history_user__first_name__icontains = value) | Q(history_user__last_name__icontains = value))