from django.contrib import admin
from .models import Solicitud_Viatico, Concepto_Viatico, Viaticos_Factura, Puntos_Intermedios

# Register your models here.

class Solicitud_ViaticoAdmin(admin.ModelAdmin):
    list_display = ('id','folio','staff','lugar_comision','lugar_partida','autorizar','autorizar2','pagada')
    search_fields = ('id','folio')
    raw_id_fields =('staff','colaborador','proyecto','subproyecto','superintendente','gerente')

class Concepto_ViaticoAdmin(admin.ModelAdmin):
    list_display = ('id','viatico','producto','precio','cantidad','comentario')
    search_fields = ('id',)
    raw_id_fields =('producto','viatico',)


class Viatico_Factura_Admin(admin.ModelAdmin):
    list_display = ('id','solicitud_viatico','factura_pdf','factura_xml','uuid')
    search_fields = ('id','uuid','solicitud_viatico__folio')

admin.site.register(Solicitud_Viatico, Solicitud_ViaticoAdmin)

admin.site.register(Concepto_Viatico, Concepto_ViaticoAdmin)

admin.site.register(Viaticos_Factura, Viatico_Factura_Admin)

admin.site.register(Puntos_Intermedios)

