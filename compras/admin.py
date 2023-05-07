from django.contrib import admin
from .models import Compra, ArticuloComprado, Proveedor, Proveedor_direcciones, Proveedor_Direcciones_Batch, Estatus_proveedor, Uso_cfdi, Cond_credito, Moneda, Estado

class CompraAdmin(admin.ModelAdmin):
    list_display = ('id','folio', 'req','proveedor','autorizado1','autorizado2')
    list_filter = ('proveedor',)

class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ('razon_social',)

class Proveedor_direccionesAdmin(admin.ModelAdmin):
    search_fields = ('nombre__razon_social',)
# Register your models here.
admin.site.register(Compra, CompraAdmin)

admin.site.register(ArticuloComprado)

admin.site.register(Proveedor, ProveedorAdmin)

admin.site.register(Proveedor_direcciones, Proveedor_direccionesAdmin)

admin.site.register(Estatus_proveedor)

admin.site.register(Proveedor_Direcciones_Batch)

admin.site.register(Uso_cfdi)

admin.site.register(Cond_credito)

admin.site.register(Moneda)

admin.site.register(Estado)

