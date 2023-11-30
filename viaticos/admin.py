from django.contrib import admin
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura

# Register your models here.

class Solicitud_ViaticoAdmin(admin.ModelAdmin):
    list_display = ('id','staff','lugar_comision','lugar_partida','autorizar','autorizar2')
    search_fields = ('id',)

class Concepto_ViaticoAdmin(admin.ModelAdmin):
    list_display = ('id','viatico','producto','precio','cantidad','comentario')
    search_fields = ('id',)


admin.site.register(Solicitud_Viatico, Solicitud_ViaticoAdmin)

admin.site.register(Concepto_Viatico, Concepto_ViaticoAdmin)

admin.site.register(Viaticos_Factura)

