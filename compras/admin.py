from django.contrib import admin
from .models import Compra, ArticuloComprado, Proveedor, Proveedor_direcciones, Proveedor_Direcciones_Batch, Estatus_proveedor, Uso_cfdi, Cond_pago, Moneda, Estado, Comparativo, Item_Comparativo, DocumentosProveedor, TipoPrioridad, Responsable_Interaccion

class CompraAdmin(admin.ModelAdmin):
    list_display = ('id','folio', 'req','proveedor','oc_autorizada_por2','cond_de_pago','autorizado1','autorizado2')
    list_filter = ('proveedor',)
    search_fields = ['id','folio']
    raw_id_fields = ('req','oc_autorizada_por','oc_autorizada_por2','proveedor','creada_por','comparativo_model','tesorero')

class ArticuloComprado_Admin(admin.ModelAdmin):
    list_display = ('id','oc','producto','cantidad','entrada_completa')
    search_fields = ['producto__producto__articulos__producto__producto__nombre','oc__folio']
    raw_id_fields = ('oc','producto',)

class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ('razon_social','rfc')
    list_display = ('id','razon_social','folio_consecutivo') 
    #raw_id_fields = ('perfil_proveedor',)

class Proveedor_direccionesAdmin(admin.ModelAdmin):
    search_fields = ('nombre__razon_social','email')
    raw_id_fields = ('nombre','creado_por')
    list_display = ('id','nombre','distrito') 
   

class Comparativo_Admin(admin.ModelAdmin):
    search_fields = ('nombre','creada_por__staff__staff__first_name','creada_por__staff__staff__last_name',)
    list_display = ('id','creada_por','nombre',) 
    raw_id_fields = ('proveedor','proveedor2','proveedor3',)

class Item_Comparativo_Admin(admin.ModelAdmin):
    raw_id_fields = ('producto',)

class Moneda_Admin(admin.ModelAdmin):
    list_display = ('id','nombre')

class DocumentosProveedorAdmin(admin.ModelAdmin):
    search_fields = ('proveedor__razon_social','tipo_documento',)
    list_display = ('id','proveedor','tipo_documento','archivo',)
    raw_id_fields = ('proveedor',)

# Register your models here.
admin.site.register(Compra, CompraAdmin)

admin.site.register(DocumentosProveedor, DocumentosProveedorAdmin)

admin.site.register(ArticuloComprado, ArticuloComprado_Admin)

admin.site.register(Proveedor, ProveedorAdmin)

admin.site.register(Proveedor_direcciones, Proveedor_direccionesAdmin)

admin.site.register(Estatus_proveedor)

admin.site.register(Proveedor_Direcciones_Batch)

admin.site.register(Uso_cfdi)

admin.site.register(Cond_pago)

admin.site.register(Moneda, Moneda_Admin)

admin.site.register(Estado)

admin.site.register(Comparativo, Comparativo_Admin)

admin.site.register(Item_Comparativo, Item_Comparativo_Admin)

admin.site.register(TipoPrioridad)

admin.site.register(Responsable_Interaccion)

