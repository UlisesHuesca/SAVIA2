from django.contrib import admin
from .models import Salidas, Requis, ArticulosRequisitados, ValeSalidas, Devolucion, Devolucion_Articulos, Tipo_Devolucion

class RequisAdmin(admin.ModelAdmin):
    list_display = ('id','folio','orden','autorizar')
    list_filter = ('folio',)
    raw_id_fields = ('orden','created_by','requi_autorizada_por', 'rejected_by',)

class ValeSalidasAdmin(admin.ModelAdmin):
    list_display = ('id','folio','solicitud','complete','created_at','cancelada')
    raw_id_fields = ('solicitud','almacenista','material_recibido_por')

class Articulos_RequisitadosAdmin(admin.ModelAdmin):
    list_display = ('id','req','producto','cantidad')
    search_fields = ['producto__articulos__producto__producto__nombre']
    raw_id_fields = ('producto','req',)

class SalidasAdmin(admin.ModelAdmin):
    list_display = ('id','producto','cantidad','precio','complete','entrada')
    search_fields = ['producto__articulos__producto__producto__nombre']
    raw_id_fields = ('producto', 'vale_salida',)

class DevolucionAdmin(admin.ModelAdmin):
    list_display = ('id','solicitud','almacenista')
    raw_id_fields = ('solicitud','almacenista','salida')

class Devolucion_ArticulosAdmin(admin.ModelAdmin):
    list_display = ('vale_devolucion','producto','cantidad','precio','comentario')
    search_fields = ['producto__articulos__producto__producto__nombre']


class Tipo_Admin(admin.ModelAdmin):
    list_display = ('id','nombre')

# Register your models here.
admin.site.register(Salidas, SalidasAdmin)

admin.site.register(ValeSalidas, ValeSalidasAdmin)

admin.site.register(Tipo_Devolucion, Tipo_Admin)

admin.site.register(Requis, RequisAdmin)

admin.site.register(ArticulosRequisitados, Articulos_RequisitadosAdmin)

admin.site.register(Devolucion, DevolucionAdmin)

admin.site.register(Devolucion_Articulos, Devolucion_ArticulosAdmin)