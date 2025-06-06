import django_filters
from .models import Compra, Pago
from django_filters import CharFilter, DateFilter, ChoiceFilter, BooleanFilter
from django.db.models import Q

class PagoFilter(django_filters.FilterSet):
    oc = CharFilter(field_name='oc__folio', lookup_expr='icontains')
    proveedor = CharFilter(field_name='oc__proveedor',lookup_expr='icontains')
    monto_pagado = CharFilter(field_name='monto_pagado', lookup_expr='icontains')
    proyecto = CharFilter(field_name='oc__req__orden__proyecto',lookup_expr='icontains')
    subproyecto = CharFilter(field_name='oc__req__orden__subproyecto', lookup_expr='icontains')
    solicitada_por = CharFilter(field_name='oc__req__orden__staff__staff', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'pagado_date', lookup_expr='gte')
    end_date = DateFilter(field_name='pagado_date',lookup_expr='lte')
    id = CharFilter(field_name='id', lookup_expr='icontains')

    class Meta:
        model = Compra
        fields = ['oc','proveedor','proyecto','subproyecto','monto_pagado','solicitada_por','start_date','end_date','id']

class Matriz_Pago_Filter(django_filters.FilterSet):

    TIPO_CHOICES = [
        ('compra', 'Compra'),
        ('gasto', 'Gasto'),
        ('viatico', 'Viatico'),
    ]

    folio = CharFilter(method='my_filter', label='Search')
    proyecto = CharFilter(method ='my_proyecto', label="Search")
    tipo = ChoiceFilter(choices=TIPO_CHOICES, method='filter_by_tipo', label='Tipo') # Changed filter
    facturas_completas = BooleanFilter(method='filter_by_facturas_completas', label='Facturas Completas') # New filter
    tiene_facturas = django_filters.BooleanFilter(method='filter_by_tiene_facturas', label='Tiene Facturas')
    tesorero = CharFilter(method='tesorero_nombre', lookup_expr='icontains')
    #proyecto = CharFilter(field_name='proyecto__nombre', lookup_expr='icontains')
    cuenta = CharFilter(field_name = 'cuenta__cuenta', lookup_expr='icontains')
    start_date = DateFilter(field_name ='pagado_real', lookup_expr='gte')
    end_date = DateFilter(field_name='pagado_real', lookup_expr='lte')
    proveedor = CharFilter(method = 'beneficiario_proveedor', lookup_expr='icontains')


    class Meta:
        model = Pago
        fields = ['oc','pagado_date','tesorero','cuenta']

    def my_filter(self, queryset, name, value):
        return queryset.filter(Q(oc__folio__icontains = value) | Q(gasto__folio__icontains = value)| Q(viatico__folio__icontains = value))

    def beneficiario_proveedor(self, queryset, name, value):
        return queryset.filter(Q(oc__proveedor__nombre__razon_social__icontains = value) | Q(gasto__colaborador__staff__staff__first_name__icontains = value)| Q(gasto__staff__staff__staff__first_name__icontains = value)| Q(gasto__colaborador__staff__staff__last_name__icontains = value)| Q(gasto__staff__staff__staff__last_name__icontains = value)| Q(viatico__colaborador__staff__staff__first_name__icontains = value)| Q(viatico__staff__staff__staff__first_name__icontains = value)| Q(viatico__colaborador__staff__staff__last_name__icontains = value)| Q(viatico__staff__staff__staff__last_name__icontains = value))

    def my_proyecto(self, queryset, name, value):
        return queryset.filter(Q(oc__req__orden__proyecto__nombre__icontains = value) | Q(gasto__articulos__proyecto__nombre__icontains = value) | Q(viatico__proyecto__nombre__icontains = value))
    
    def filter_by_tipo(self, queryset, name, value):  # new method
        if value.lower() == 'compra':
            return queryset.filter(oc__isnull=False)
        elif value.lower() == 'viatico':
            return queryset.filter(viatico__isnull=False)
        elif value.lower() == 'gasto':
            return queryset.filter(gasto__isnull=False)
        return queryset
    
    def filter_by_facturas_completas(self, queryset, name, value):  # New method
        return queryset.filter(Q(oc__facturas_completas=value) | Q(gasto__facturas_completas=value) | Q(viatico__facturas_completas=value))
    
    def filter_by_tiene_facturas(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(oc__facturas__isnull=False) |
                Q(gasto__facturas__isnull=False) |
                Q(viatico__facturas__isnull=False)
            ).distinct()
        else:
            return queryset.filter(
                Q(oc__facturas__isnull=True) &
                Q(gasto__facturas__isnull=True) &
                Q(viatico__facturas__isnull=True)
            ).distinct()
    
    def tesorero_nombre(self, queryset, name, value):
    # Verificar si el valor ingresado contiene un espacio (nombre y apellido juntos)
        if " " in value:
            first_name, last_name = value.split(" ", 1)  # Dividir solo en la primera ocurrencia del espacio
            return queryset.filter(
                Q(tesorero__staff__staff__first_name__icontains=first_name) & 
                Q(tesorero__staff__staff__last_name__icontains=last_name)
            )
        else:
            # Si solo se ingresó una palabra, buscar en ambos campos
            return queryset.filter(
                Q(tesorero__staff__staff__first_name__icontains=value) | 
                Q(tesorero__staff__staff__last_name__icontains=value)
            )
