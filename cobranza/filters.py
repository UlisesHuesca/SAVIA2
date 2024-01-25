import django_filters
from .models import Cobranza
from django_filters import CharFilter, DateTimeFilter



class PagosFilter(django_filters.FilterSet):
    id = CharFilter(field_name='id', lookup_expr='icontains')
    proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    cliente = CharFilter(field_name='proyecto__cliente', lookup_expr='icontains')
    fecha_pago = DateTimeFilter(field_name='fecha_pago', lookup_expr='gte')
    monto_abono = CharFilter(field_name='monto_abono',lookup_expr='gte')
    comentario = CharFilter(field_name='comentario', lookup_expr='icontains')

    class Meta:
        model = Cobranza
        fields = ['id', 'proyecto','fecha_pago','monto_abono','comentario',]