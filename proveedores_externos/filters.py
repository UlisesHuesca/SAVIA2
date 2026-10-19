import django_filters
from django_filters import CharFilter, DateFilter, ChoiceFilter, BooleanFilter
from django.db.models import Exists, OuterRef
from compras.models import Compra
from tesoreria.models import Pago
from datetime import timedelta
from django.utils.timezone import now


class Compra_PE_Filter(django_filters.FilterSet):

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

    DISTRITO_CHOICES = [
    ('ALTAMIRA', 'Altamira'),
    ('POZA RICA', 'Poza Rica'),
    ('MATRIZ', 'Matriz'),
    ('VERACRUZ', 'Veracruz'),
    ('VILLAHERMOSA', 'Villahermosa'),
    # etc...
]
    proveedor = CharFilter(field_name='proveedor__nombre__razon_social', lookup_expr='icontains')
    creada_por = CharFilter(field_name='creada_por', lookup_expr='icontains')
    req = CharFilter(field_name='req__folio', lookup_expr='icontains')
    solicitud = CharFilter(field_name='req__orden__id', lookup_expr='icontains')
    proyecto = CharFilter(field_name='req__orden__proyecto__nombre', lookup_expr='icontains')
    subproyecto = CharFilter(field_name='req__orden__subproyecto__nombre', lookup_expr='icontains')
    start_date =  start_date = DateFilter(method='filter_fecha_pago',label='Pago desde')
    end_date = DateFilter(method='filter_fecha_pago',label='Pago hasta')
    costo_oc = CharFilter(field_name='costo_oc', lookup_expr='icontains')
    folio = CharFilter(field_name='folio', lookup_expr='icontains')
    atrasado = django_filters.BooleanFilter(method='filtro_atrasado')
    pago = ChoiceFilter(choices=PAGO_CHOICES, method='filter_by_pago', label='Pago') # Changed filter
    moneda = ChoiceFilter(choices = MONEDA_CHOICES, method='filter_by_moneda', label ='Moneda')
    distrito = ChoiceFilter(choices = DISTRITO_CHOICES, field_name='req__orden__distrito__nombre', label="Distrito")# Filtra por el nombre exacto)
    pagada = ChoiceFilter(choices=PAGADA_CHOICES, method='filter_by_pagada', label='Pagada') # Changed filter

    class Meta:
        model = Compra
        fields = ['folio','proveedor','creada_por','req','solicitud','proyecto','subproyecto','start_date','end_date', 'costo_oc','atrasado','pago', 'moneda','pagada','distrito']

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

    def filter_fecha_pago(self, queryset, name, value):

        pagos = Pago.objects.filter(
            oc_id=OuterRef('pk'),
            hecho=True,
            pagado_real__isnull=False
        )

        if name == 'start_date':
            pagos = pagos.filter(pagado_real__gte=value)

        elif name == 'end_date':
            pagos = pagos.filter(pagado_real__lte=value)

        return queryset.filter(Exists(pagos))