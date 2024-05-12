from django.contrib import admin
from .models import Entrada, EntradaArticulo, Reporte_Calidad, No_Conformidad, NC_Articulo, Tipo_Nc, Cierre_Nc

# Register your models here.
class EntradaAdmin(admin.ModelAdmin):
    list_display = ('id','folio','almacenista','oc','completo','entrada_date')
    list_filter = ('oc',)
    search_fields = ['oc__folio']
    raw_id_fields = ('oc','almacenista')

class Tipo_NcAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

class No_ConformidadAdmin(admin.ModelAdmin):
    list_display = ('id','oc','comentario','tipo_nc')
    raw_id_fields =('oc','almacenista')

class Reporte_CalidadAdmin(admin.ModelAdmin):
    list_display = ('id','articulo','cantidad')
    raw_id_fields =('articulo',)

class NC_ArticuloAdmin(admin.ModelAdmin):
    raw_id_fields = ('articulo_comprado',)

class EntradaArticuloAdmin(admin.ModelAdmin):
    list_display = ('id','get_entrada_folio','cantidad','articulo_comprado','liberado','cantidad','cantidad_por_surtir')
    search_fields = ['articulo_comprado__producto__producto__articulos__producto__producto__nombre', 'entrada__folio','entrada__oc__folio']
    raw_id_fields = ('entrada','articulo_comprado')

    def get_entrada_folio(self, obj):
        return obj.entrada.folio
    get_entrada_folio.short_description = 'Folio de Entrada'  # Establece un nombre de columna personalizado
    get_entrada_folio.admin_order_field = 'entrada__folio'  # Permite ordenar por este campo

admin.site.register(Entrada, EntradaAdmin)

admin.site.register(EntradaArticulo, EntradaArticuloAdmin)

admin.site.register(Reporte_Calidad, Reporte_CalidadAdmin)

admin.site.register(No_Conformidad, No_ConformidadAdmin)

admin.site.register(NC_Articulo,NC_ArticuloAdmin)

admin.site.register(Tipo_Nc, Tipo_NcAdmin)

admin.site.register(Cierre_Nc)