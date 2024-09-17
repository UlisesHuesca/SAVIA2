import django_filters
from .models import Profile, Almacen, Distrito, Tipo_perfil, Empresa
from django.forms import SelectMultiple
from django.db.models import Q

from django_filters import CharFilter, DateTimeFilter

class ProfileFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(field_name='staff__staff__username',lookup_expr='icontains',label='User')
    nombre = CharFilter(method='filter_nombre', lookup_expr='icontains')
    distritos = django_filters.ModelChoiceFilter(queryset=Distrito.objects.all(), label='Distrito')
    almacen = django_filters.ModelChoiceFilter(queryset=Almacen.objects.all(), label='Almacén')
    tipo = django_filters.ModelChoiceFilter(queryset=Tipo_perfil.objects.all(), label='Tipo de Perfil')
    st_activo = django_filters.BooleanFilter(label='Activo')
    nivel = django_filters.NumberFilter(field_name='staff__nivel', label='Nivel')
    empresa = django_filters.ModelChoiceFilter(queryset=Empresa.objects.all(), field_name='staff__empresa',label='Empresa')
    puesto = django_filters.CharFilter(field_name='staff__puesto',lookup_expr='icontains',label='Puesto')

    class Meta:
        model = Profile
        fields = ['distritos', 'almacen', 'tipo', 'st_activo']

    def filter_nombre(self, queryset, name, value):
        return queryset.filter(Q(staff__staff__first_name__icontains=value) | Q(staff__staff__last_name__icontains=value))