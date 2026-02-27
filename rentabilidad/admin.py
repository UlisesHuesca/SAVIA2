from django.contrib import admin
from .models import Concepto, Tipo_Costo, Costos, Ingresos, Depreciaciones, Solicitud_Costos, Solicitud_Ingresos

class Solicitud_Costos_Admin(admin.ModelAdmin):
    list_display = ('id','contrato','distrito','tipo','fecha','complete')

class Ingresos_Admin(admin.ModelAdmin):
    list_display = ('id','solicitud','contrato','concepto','complete')

class Costos_Admin(admin.ModelAdmin):
    list_display = ('id','solicitud','concepto','categorizacion','monto','complete')
# Register your models here.
admin.site.register(Concepto)

admin.site.register(Tipo_Costo)

admin.site.register(Solicitud_Costos, Solicitud_Costos_Admin)

admin.site.register(Costos, Costos_Admin)

admin.site.register(Solicitud_Ingresos)

admin.site.register(Ingresos, Ingresos_Admin)

admin.site.register(Depreciaciones)
