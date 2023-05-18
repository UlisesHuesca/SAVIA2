from django.contrib import admin
from .models import Salidas, Requis, ArticulosRequisitados, ValeSalidas, Devolucion, Devolucion_Articulos

class RequisAdmin(admin.ModelAdmin):
    list_display = ('id','folio','orden','autorizar')
    list_filter = ('folio',)

class ValeSalidasAdmin(admin.ModelAdmin):
    list_display = ('id','solicitud','complete')

class Articulos_RequisitadosAdmin(admin.ModelAdmin):
    list_display = ('req','producto','cantidad')
    search_fields = ['producto__articulos__producto__producto__nombre']

class SalidasAdmin(admin.ModelAdmin):
    list_display = ('id','producto','cantidad','precio','complete','entrada')

class DevolucionAdmin(admin.ModelAdmin):
    list_display = ('id','solicitud','almacenista')

class Devolucion_ArticulosAdmin(admin.ModelAdmin):
    list_display = ('vale_devolucion','producto','cantidad','precio','comentario')

# Register your models here.
admin.site.register(Salidas, SalidasAdmin)

admin.site.register(ValeSalidas, ValeSalidasAdmin)

admin.site.register(Requis, RequisAdmin)

admin.site.register(ArticulosRequisitados, Articulos_RequisitadosAdmin)

admin.site.register(Devolucion, DevolucionAdmin)

admin.site.register(Devolucion_Articulos, Devolucion_ArticulosAdmin)