import django_filters
from django import forms
from django.db.models import Q
from .models import CFDI


class CFDIFilter(django_filters.FilterSet):

    uuid = django_filters.CharFilter(
        field_name='uuid',
        lookup_expr='icontains',
        label='UUID',
    )

    emisor = django_filters.CharFilter(
        method='filter_emisor',
        label='Proveedor',
    )

    rfc_receptor = django_filters.CharFilter(
        field_name='rfc_receptor',
        lookup_expr='icontains',
        label='RFC receptor',
    )

    serie_folio = django_filters.CharFilter(
        method='filter_serie_folio',
        label='Serie o folio',
    )

    fecha_inicio = django_filters.DateFilter(
        field_name='fecha_timbrado',
        lookup_expr='date__gte',
        label='Timbrado desde',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    fecha_fin = django_filters.DateFilter(
        field_name='fecha_timbrado',
        lookup_expr='date__lte',
        label='Timbrado hasta',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    total_minimo = django_filters.NumberFilter(
        field_name='total',
        lookup_expr='gte',
        label='Total mínimo',
    )

    total_maximo = django_filters.NumberFilter(
        field_name='total',
        lookup_expr='lte',
        label='Total máximo',
    )

    tipo_comprobante = django_filters.ChoiceFilter(
        field_name='tipo_comprobante',
        choices=CFDI.TIPO_COMPROBANTE_CHOICES,
        label='Tipo',
    )

    estatus = django_filters.ChoiceFilter(
        field_name='estatus',
        choices=CFDI.ESTATUS_CHOICES,
        label='Estatus',
    )

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