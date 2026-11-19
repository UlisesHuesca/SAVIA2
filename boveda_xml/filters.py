import datetime

import django_filters
from django import forms
from django.db.models import Q
from .models import CFDI
from datetime import datetime, time, timedelta

from django.utils import timezone


class CFDIFilter(django_filters.FilterSet):
    ESTADOS_SAT = [
        ("VIGENTE", "Vigente"),
        ("CANCELADO", "Cancelado"),
        ("NO ENCONTRADO", "No encontrado"),
        ("SIN_VALIDAR", "Sin validar"),
    ]


    uuid = django_filters.CharFilter(field_name='uuid', lookup_expr='icontains', label='UUID',)
    emisor = django_filters.CharFilter(method='filter_emisor',label='Proveedor',)
    rfc_receptor = django_filters.CharFilter(field_name='rfc_receptor', lookup_expr='icontains', label='RFC receptor',)
    serie_folio = django_filters.CharFilter(method='filter_serie_folio',label='Serie o folio',)
    fecha_inicio = django_filters.DateFilter(method='filter_fecha_inicio',label='Timbrado desde',
        widget=forms.DateInput(
            attrs={'type': 'date'}
        ),
    )
    fecha_fin = django_filters.DateFilter(method='filter_fecha_fin',label='Timbrado hasta',
        widget=forms.DateInput(
            attrs={'type': 'date'}
        ),
    )
    total_minimo = django_filters.NumberFilter(field_name='total',lookup_expr='gte',label='Total mínimo',)
    total_maximo = django_filters.NumberFilter(field_name='total',lookup_expr='lte',label='Total máximo',)
    tipo_comprobante = django_filters.ChoiceFilter(field_name='tipo_comprobante',choices=CFDI.TIPO_COMPROBANTE_CHOICES,label='Tipo',)
    estado_sat = django_filters.ChoiceFilter(label="Estado SAT",choices=ESTADOS_SAT,method="filtrar_estado_sat",empty_label="Todos los estados",)


    class Meta:
        model = CFDI
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def filter_emisor(self, queryset, name, value):
        return queryset.filter(
            Q(rfc_emisor__icontains=value) |
            Q(nombre_emisor__icontains=value)
        )

    def filter_serie_folio(self, queryset, name, value):
        return queryset.filter(
            Q(serie__icontains=value) |
            Q(folio__icontains=value)
        )

    def filter_fecha_inicio(self, queryset, name, value,):
        if not value:
            return queryset

        fecha_desde = timezone.make_aware(datetime.combine(value, time.min), timezone.get_current_timezone(),)

        return queryset.filter(fecha_timbrado__gte=fecha_desde)


    def filter_fecha_fin(self, queryset, name, value,):
        if not value:
            return queryset

        fecha_hasta = timezone.make_aware(datetime.combine(value + timedelta(days=1),time.min,),timezone.get_current_timezone(),)

        return queryset.filter(fecha_timbrado__lt=fecha_hasta)

    def filtrar_estado_sat(self, queryset, name, value):

        if value == "SIN_VALIDAR":
            return queryset.filter(
                Q(estado_sat__isnull=True)
                | Q(estado_sat="")
            )

        if value:
            return queryset.filter(estado_sat=value)

        return queryset