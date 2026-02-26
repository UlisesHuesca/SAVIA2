from django.contrib import admin
from .models import Concepto, Tipo_Costo, Costos, Ingresos, Depreciaciones, Solicitud_Costos, Solicitud_Ingresos

class Solicitud_Costos_Admin(admin.ModelAdmin):
    list_display = ('id','contrato','distrito','tipo','fecha','complete')
    #raw_id_fields = ('staff','colaborador','superintendente','proveedor','autorizado_por2') 
    #search_fields = ('folio','id','staff__staff__staff__first_name')

# Register your models here.
admin.site.register(Concepto)

admin.site.register(Tipo_Costo)

admin.site.register(Solicitud_Costos, Solicitud_Costos_Admin)

admin.site.register(Costos)

admin.site.register(Solicitud_Ingresos)

admin.site.register(Ingresos)

admin.site.register(Depreciaciones)
