from django.contrib import admin
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo

# Register your models here.
class EntradaAdmin(admin.ModelAdmin):
    list_display = ('id','almacenista','oc','completo')
    list_filter = ('oc',)

class EntradaArticuloAdmin(admin.ModelAdmin):
    list_display = ('id','entrada','cantidad','articulo_comprado','liberado')
    list_filter = ('entrada',)

admin.site.register(Entrada, EntradaAdmin)

admin.site.register(EntradaArticulo, EntradaArticuloAdmin)

admin.site.register(Reporte_Calidad)

admin.site.register(No_Conformidad)

admin.site.register(NC_Articulo)