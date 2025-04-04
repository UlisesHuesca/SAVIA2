import django_filters
from requisiciones.models import ArticulosRequisitados
from .models import Compra, ArticuloComprado, Comparativo
from django_filters import CharFilter, DateFilter, ChoiceFilter, BooleanFilter
from django.db.models import Q
from datetime import timedelta, datetime
from django.utils.timezone import now
import logging



class CompraFilter(django_filters.FilterSet):

    PAGO_CHOICES = [
        ('CREDITO', 'Credito'),
        ('CONTADO', 'Contado'),
    ]

    MONEDA_CHOICES = [
        ('DOLARES','DOLARES'),
        ('PESOS','PESOS'),
    ]

    PAGADA_CHOICES = [
    ('true', 'Pagada'),
    ('false', 'No pagada'),
    ]
    proveedor = CharFilter(field_name='proveedor__nombre__razon_social', lookup_expr='icontains')
    creada_por = CharFilter(field_name='creada_por', lookup_expr='icontains')
    req = CharFilter(field_name='req__folio', lookup_expr='icontains')
    solicitud = CharFilter(field_name='req__orden__id', lookup_expr='icontains')
    proyecto = CharFilter(field_name='req__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='req__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at',lookup_expr='lte')
    costo_oc = CharFilter(field_name='costo_oc', lookup_expr='icontains')
    folio = CharFilter(field_name='folio', lookup_expr='icontains')
    atrasado = django_filters.BooleanFilter(method='filtro_atrasado')
    pago = ChoiceFilter(choices=PAGO_CHOICES, method='filter_by_pago', label='Pago') # Changed filter
    moneda = ChoiceFilter(choices = MONEDA_CHOICES, method='filter_by_moneda', label ='Moneda')
    distrito = CharFilter(field_name='req__orden__distrito__nombre', lookup_expr='icontains')
    pagada = ChoiceFilter(choices=PAGADA_CHOICES, method='filter_by_pagada', label='Pagada') # Changed filter

    class Meta:
        model = Compra
        fields = ['folio','proveedor','creada_por','req','solicitud','proyecto','subproyecto','start_date','end_date', 'costo_oc','atrasado','pago', 'moneda','pagada']

    def filter_by_pago(self, queryset, name, value):
        # Asegúrate de que 'value' coincida con las opciones 'CREDITO' o 'CONTADO'
        if value == 'CREDITO':
            return queryset.filter(cond_de_pago__nombre='CREDITO')
        elif value == 'CONTADO':
            return queryset.filter(cond_de_pago__nombre='CONTADO')
        return queryset
    
    def filter_by_pagada(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(pagada=True)
        elif value == 'false':
            return queryset.filter(pagada=False)
        return queryset

    def filter_by_moneda(self, queryset, name, value):
        # Asegúrate de que 'value' coincida con las opciones 'CREDITO' o 'CONTADO'
        if value == 'DOLARES':
            return queryset.filter(moneda__nombre='DOLARES')
        elif value == 'PESOS':
            return queryset.filter(moneda__nombre='PESOS')
        return queryset
    
    def filtro_atrasado(self, queryset, name, value):
        if value:
            compras_atrasadas = []
            for compra in queryset:
                fecha_limite = None  # Inicialización de fecha_limite
                if compra.cond_de_pago.nombre == 'CREDITO':
                    fecha_limite = compra.autorizado_at_2.date() + timedelta(days=compra.dias_de_credito)
                elif compra.cond_de_pago.nombre == 'CONTADO':
                    if compra.fecha_pago != 0:
                        fecha_limite = compra.fecha_pago.date() + timedelta(days=compra.dias_de_credito)

                
                
                # Si fecha_limite no está definida, continúa al siguiente elemento del bucle
                if not fecha_limite:
                    continue

                if fecha_limite < now().date():
                    compras_atrasadas.append(compra.id)

            return queryset.filter(id__in=compras_atrasadas)
        elif value == False:
            # Filtrar solo las compras que no están atrasadas
            compras_no_atrasadas = []
            for compra in queryset:
                fecha_limite = None  # Inicialización de fecha_limite
                if compra.cond_de_pago == 'CREDITO':
                    fecha_limite = compra.autorizado_at_2.date() + timedelta(days=compra.dias_de_credito)
                elif compra.cond_de_pago == 'CONTADO':
                    if compra.fecha_pago != 0:
                        fecha_limite = compra.fecha_pago.date() + timedelta(days=compra.dias_de_credito)

                if not fecha_limite:
                    continue

                if fecha_limite >= now().date():
                    compras_no_atrasadas.append(compra.id)

                # Impresiones de depuración
               
            return queryset.filter(id__in=compras_no_atrasadas)

class ArticuloCompradoFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    oc = CharFilter(field_name='oc__folio', lookup_expr='icontains')
    start_date = DateFilter(field_name = 'oc__created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='oc__created_at',lookup_expr='lte')

    class Meta:
        model = ArticuloComprado
        fields = ['producto','oc', 'start_date','end_date']

class ArticulosRequisitadosFilter(django_filters.FilterSet):
    producto = CharFilter(field_name='producto__articulos__producto__producto__nombre', lookup_expr='icontains')

    class Meta:
        model = ArticulosRequisitados
        fields = ['producto']

class HistoricalArticuloCompradoFilter(django_filters.FilterSet):
    history_id = CharFilter(field_name='history_id', lookup_expr='icontains')
    history_user = CharFilter(method='nombre', lookup_expr='icontains')
    history_type = CharFilter(field_name='history_type', lookup_expr='icontains')
    producto = CharFilter(field_name='producto__producto__articulos__producto__producto__nombre', lookup_expr='icontains')
    oc = CharFilter(field_name ='oc__id',lookup_expr='icontains')
    start_date = DateFilter(field_name='history_date', lookup_expr='gte')
    end_date = DateFilter(field_name='history_date', lookup_expr='lte')

    class Meta:
        model = ArticuloComprado.history.model
        fields = ['history_id','history_user','producto','oc','start_date','end_date']
    
    def nombre(self, queryset, name, value):
        return queryset.filter(Q(history_user__first_name__icontains = value) | Q(history_user__last_name__icontains = value))
    
class HistoricalCompraFilter(django_filters.FilterSet):
    history_id = CharFilter(field_name='history_id', lookup_expr='icontains')
    history_user = CharFilter(method='nombre', lookup_expr='icontains')
    history_type = CharFilter(field_name='history_type', lookup_expr='icontains')
    folio = CharFilter(field_name ='folio',lookup_expr='icontains')
    autorizado2 = BooleanFilter(field_name='autorizado2', lookup_expr='exact')
    autorizado1 = BooleanFilter(field_name='autorizado2', lookup_expr='exact')
    regresar_oc = BooleanFilter(field_name='autorizado2', lookup_expr='exact')
    start_date = DateFilter(field_name='history_date', lookup_expr='gte')
    end_date = DateFilter(field_name='history_date', lookup_expr='lte')

    class Meta:
        model = Compra.history.model
        fields = ['history_id','history_user','folio','autorizado2','autorizado1','regresar_oc','start_date','end_date']
        
    def nombre(self, queryset, name, value):
        return queryset.filter(Q(history_user__first_name__icontains = value) | Q(history_user__last_name__icontains = value))

class ComparativoFilter(django_filters.FilterSet):
    nombre = CharFilter(field_name='nombre', lookup_expr='icontains')
    proveedor = CharFilter(field_name="proveedor__razon_social", lookup_expr='icontains')
    proveedor2 = CharFilter(field_name="proveedor__razon_social", lookup_expr='icontains')
    proveedor3 = CharFilter(field_name="proveedor__razon_social", lookup_expr='icontains')
    creada_por = CharFilter(method='creador', lookup_expr='icontains')
    start_date = DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Comparativo
        fields = ['nombre','proveedor','proveedor2','proveedor3','creada_por','start_date','end_date']

    def creador(self, queryset, name, value):
        return queryset.filter(Q(creada_por__staff__staff__first_name__icontains = value) | Q(creada_por__staff__staff__last_name__icontains = value))