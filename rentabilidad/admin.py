from django.contrib import admin
from .models import Concepto, Tipo_Costo, Costos, Ingresos, Depreciaciones, Solicitud_Costos, Solicitud_Ingresos

# Register your models here.
admin.site.register(Concepto)

admin.site.register(Tipo_Costo)

admin.site.register(Solicitud_Costos)

admin.site.register(Costos)

admin.site.register(Solicitud_Ingresos)

admin.site.register(Ingresos)

admin.site.register(Depreciaciones)
