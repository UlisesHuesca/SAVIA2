from django.contrib import admin
from .models import Compra, ArticuloComprado, Proveedor, Proveedor_direcciones, Proveedor_Direcciones_Batch, Estatus_proveedor, Uso_cfdi, Cond_pago, Moneda, Estado, Comparativo, Item_Comparativo

class CompraAdmin(admin.ModelAdmin):
    list_display = ('id','folio', 'req','proveedor','oc_autorizada_por2','cond_de_pago','autorizado1','autorizado2')
    list_filter = ('proveedor',)
    search_fields = ['folio']
    raw_id_fields = ('req','oc_autorizada_por','oc_autorizada_por2',)

class ArticuloComprado_Admin(admin.ModelAdmin):
    list_display = ('id','oc','producto','cantidad')
    search_fields = ['producto__producto__articulos__producto__producto__nombre','oc__folio']
    raw_id_fields = ('producto','oc',)

class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ('razon_social',)

class Proveedor_direccionesAdmin(admin.ModelAdmin):
    search_fields = ('nombre__razon_social',)
    raw_id_fields = ('nombre','creado_por',)
   

class Comparativo_Admin(admin.ModelAdmin):
     raw_id_fields = ('proveedor','proveedor2','proveedor3',)

class Item_Comparativo_Admin(admin.ModelAdmin):
     raw_id_fields = ('producto',)

# Register your models here.
admin.site.register(Compra, CompraAdmin)

admin.site.register(ArticuloComprado, ArticuloComprado_Admin)

admin.site.register(Proveedor, ProveedorAdmin)

admin.site.register(Proveedor_direcciones, Proveedor_direccionesAdmin)

admin.site.register(Estatus_proveedor)

admin.site.register(Proveedor_Direcciones_Batch)

admin.site.register(Uso_cfdi)

admin.site.register(Cond_pago)

admin.site.register(Moneda)

admin.site.register(Estado)

admin.site.register(Comparativo, Comparativo_Admin)

admin.site.register(Item_Comparativo, Item_Comparativo_Admin)

