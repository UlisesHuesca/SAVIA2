from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Product, Order, Familia, Unidad, Subfamilia, Marca, Inventario, ArticulosOrdenados, ArticulosparaSurtir, Products_Batch, Tipo_Orden, Inventario_Batch, Activo, Estatus_Activo 
from compras.models import Proveedor_Batch
# Esta línea es para cambiarle el nombre al sitio administrador por default (Django administration)
admin.site.site_header = 'SAVIA 2.0 | Administración'


# Esta es la configuración para que sucedan dos cosas una que se muestre en forma tabular en 'administration' que nos salgan filtros
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','familia', 'codigo')
    list_filter = ('familia',)
    search_fields = ['nombre']


class InventarioAdmin(SimpleHistoryAdmin):
    list_display = ('id','producto','cantidad','cantidad_apartada','price','minimo')
    list_filter = ('producto',)
    history_list_display = ('status')
    search_fields = ['producto__nombre']
    raw_id_fields = ('producto',) 

class ActivoAdmin(admin.ModelAdmin):
    list_display = ('id','eco_unidad','tipo_activo','serie','cuenta_contable','factura_interna')
    search_fields = ['nombre']

class ArticulosOrdenadosAdmin(admin.ModelAdmin):
    list_display = ('id','orden','producto','cantidad')
    search_fields = ['producto__producto__nombre', 'producto__producto__codigo']
    raw_id_fields = ('producto','orden',) 

class ArticulosparaSurtirAdmin(admin.ModelAdmin):
    search_fields = ['articulos__producto__producto__nombre']
    list_display = ('id','articulos','cantidad', 'surtir','requisitar','cantidad_requisitar','salida','precio')
    search_fields = ['articulos__orden__folio','articulos__producto__producto__nombre','articulos__orden__distrito__nombre']
    raw_id_fields = ('articulos',)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id','folio','staff','proyecto','subproyecto','tipo','approved_at','requisitado','requisitar')
    search_fields = ['folio']
    raw_id_fields = ('staff','proyecto','subproyecto','superintendente','supervisor','activo',)


class SubfamiliaAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','familia')

# Register your models here.
admin.site.register(Familia)

admin.site.register(Subfamilia,SubfamiliaAdmin)

admin.site.register(Unidad)

admin.site.register(Product, ProductAdmin)

admin.site.register(Order, OrderAdmin)

admin.site.register(Marca)

admin.site.register(Inventario, InventarioAdmin)

admin.site.register(ArticulosOrdenados, ArticulosOrdenadosAdmin)

admin.site.register(ArticulosparaSurtir, ArticulosparaSurtirAdmin)

admin.site.register(Products_Batch)

admin.site.register(Inventario_Batch)

admin.site.register(Proveedor_Batch)

admin.site.register(Tipo_Orden)

admin.site.register(Activo, ActivoAdmin)

admin.site.register(Estatus_Activo)
