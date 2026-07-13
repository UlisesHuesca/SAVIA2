import django_filters
from .models import Solicitud_Gasto, Conceptos_Entradas, Tipo_Gasto, ValeRosa
from solicitudes.models import Proyecto, Subproyecto
from user.models import Distrito
from django_filters import CharFilter, DateFilter, ChoiceFilter, NumberFilter
from django.db.models import Q
from django.forms import TextInput




class Solicitud_Gasto_Filter(django_filters.FilterSet):
    folio = CharFilter(method='filter_folio_custom')
    solicitado_por = CharFilter(method = 'filter_solicitado_por',  label = "Solicitado por")
    solicitado_para = CharFilter(method = 'filter_solicitado_para',  label = "Solicitado para")
    #solicitado_para = CharFilter(field_name = 'colaborador__staff__staff__first_name',  lookup_expr='icontains')
    tipo = django_filters.ModelChoiceFilter(queryset=Tipo_Gasto.objects.all(), label="Tipo Gasto")
    start_date = DateFilter(field_name ='approbado_fecha2', lookup_expr='gte')
    end_date = DateFilter(field_name='approbado_fecha2', lookup_expr='lte')
    distrito = django_filters.ModelChoiceFilter(queryset=Distrito.objects.none(),  label="Distrito")
    #Busqueda parcial para la parte de gasto
    proyecto = django_filters.ModelChoiceFilter(queryset=Proyecto.objects.filter(activo=True, complete=True), method='filter_by_proyecto', label="Proyecto")
    subproyecto = django_filters.ModelChoiceFilter(queryset=Subproyecto.objects.all(), method='filter_by_subproyecto', label="Subproyecto")

   

    def __init__(self, *args, **kwargs):
        perfil = kwargs.pop('perfil', None)
        super().__init__(*args, **kwargs)

        if perfil:
            almacenes_distritos = perfil.almacen.values_list(
                'distrito__id',
                flat=True
            )

            self.filters['distrito'].queryset = Distrito.objects.filter(
                id__in=almacenes_distritos,
                status=True
            )

    class Meta:
        model = Solicitud_Gasto
        fields = ['staff','colaborador','folio','start_date','end_date','tipo','proyecto','subproyecto','distrito',]

    def filter_solicitado_por(self, queryset, name, value):
        if " " in value:
            first_name, last_name = value.split(" ", 1)
            return queryset.filter(
                Q(staff__staff__staff__first_name__icontains=first_name) &
                Q(staff__staff__staff__last_name__icontains=last_name)
            )
        else:
            return queryset.filter(
                Q(staff__staff__staff__first_name__icontains=value) |
                Q(staff__staff__staff__last_name__icontains=value)
            )
        
    def filter_solicitado_para(self, queryset, name, value):
        if " " in value:
            first_name, last_name = value.split(" ", 1)
            return queryset.filter(
                Q(colaborador__staff__staff__first_name__icontains=first_name) &
                Q(colaborador__staff__staff__last_name__icontains=last_name)
            )
        else:
            return queryset.filter(
                Q(colaborador__staff__staff__first_name__icontains=value) |
                Q(colaborador__staff__staff__last_name__icontains=value)
            )
    
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
    solicitado = CharFilter(method='solicitado', lookup_expr='icontains')

    class Meta:
        model = Conceptos_Entradas
        fields = ['concepto_material','entrada',]

    def almacenistaa(self, queryset, name, value):
        return queryset.filter(Q(entrada__almacenista__staff__staff__first_name__icontains = value) | Q(entrada__almacenista__staff__staff__last_name__icontains = value))
    
    def solicitadoo(self, queryset, name, value):
        return queryset.filter(Q(entrada__gasto__staff__staff__staff__first_name__icontains = value) | Q(entrada__gasto__staff__staff__staff__last_name__icontains = value))
    
class ValeRosaFilter(django_filters.FilterSet):

    ORIGEN_CHOICES = [
        ('GASTO', 'Gasto'),
        ('VIATICO', 'Viático'),
    ]

    ESTATUS_CHOICES = [
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('PENDIENTE', 'Pendiente'),
    ]

    folio = CharFilter(method='filter_folio',label='Folio')
    origen = ChoiceFilter(choices=ORIGEN_CHOICES,method='filter_origen',label='Origen')
    motivo = CharFilter(field_name='motivo',lookup_expr='icontains',label='Motivo')
    creado_por = CharFilter(method='filter_creado_por',label='Creado por')
    aprobado_por = CharFilter(method='filter_aprobado_por',label='Aprobado por')
    distrito = CharFilter(method='filter_distrito',label='Distrito')
    estatus = ChoiceFilter(choices=ESTATUS_CHOICES,method='filter_estatus',label='Estatus')
    start_date = DateFilter(field_name='creado_en',lookup_expr='date__gte',label='Creado desde')
    end_date = DateFilter(field_name='creado_en',lookup_expr='date__lte',label='Creado hasta')

    class Meta:
        model = ValeRosa

        fields = ['folio','origen','motivo','creado_por','aprobado_por','distrito','estatus','start_date','end_date',]

    def filter_folio(self, queryset, name, value):
        return queryset.filter(
            Q(gasto__folio__icontains=value) |
            Q(viatico__folio__icontains=value)
        )

    def filter_origen(self, queryset, name, value):
        if value == 'GASTO':
            return queryset.filter(
                gasto__isnull=False,
                viatico__isnull=True
            )

        if value == 'VIATICO':
            return queryset.filter(
                viatico__isnull=False,
                gasto__isnull=True
            )

        return queryset

    def filter_creado_por(self, queryset, name, value):
        return queryset.filter(
            Q(
                creado_por__staff__staff__first_name__icontains=value
            ) |
            Q(
                creado_por__staff__staff__last_name__icontains=value
            )
        )

    def filter_aprobado_por(self, queryset, name, value):
        return queryset.filter(
            Q(
                aprobado_por__staff__staff__first_name__icontains=value
            ) |
            Q(
                aprobado_por__staff__staff__last_name__icontains=value
            )
        )

    def filter_distrito(self, queryset, name, value):
        return queryset.filter(
            Q(gasto__distrito__nombre__icontains=value) |
            Q(viatico__distrito__nombre__icontains=value)
        )

    def filter_estatus(self, queryset, name, value):
        if value == 'APROBADO':
            return queryset.filter(esta_aprobado=True)

        if value == 'RECHAZADO':
            return queryset.filter(esta_aprobado=False)

        if value == 'PENDIENTE':
            return queryset.filter(esta_aprobado__isnull=True)

        return queryset