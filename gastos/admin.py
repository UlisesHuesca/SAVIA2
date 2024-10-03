from django.contrib import admin
from .models import Solicitud_Gasto, Articulo_Gasto, Tipo_Gasto, Entrada_Gasto_Ajuste, Conceptos_Entradas, Factura, Porcentaje_iva
# Register your models here.
class Solicitud_Gasto_Admin(admin.ModelAdmin):
    list_display = ('id','created_at','folio','staff','colaborador', 'superintendente','pagada',)
    raw_id_fields = ('staff','colaborador','superintendente','proveedor','autorizado_por2') 
    search_fields = ('folio','id')

class Conceptos_Entradas_Admin(admin.ModelAdmin):
    list_display =('id', 'concepto_material', 'entrada',)

class Articulo_Gasto_Admin(admin.ModelAdmin):
    list_display =('id','gasto','staff','proyecto', 'subproyecto','producto','comentario','created_at', 'validacion')
    raw_id_fields = ('gasto','staff','producto','proyecto','subproyecto')
    search_fields = ('gasto__folio',)

class Entrada_Gasto_Ajuste_Admin(admin.ModelAdmin):
    list_display =('id','gasto','almacenista','completo')

class Factura_Admin(admin.ModelAdmin):
    list_display = ('id','solicitud_gasto', 'fecha_subida', 'archivo_pdf', 'archivo_xml','uuid')   
    raw_id_fields = ('solicitud_gasto',) 
    search_fields = ('id','solicitud_gasto__id', 'solicitud_gasto__folio','uuid')


admin.site.register(Solicitud_Gasto, Solicitud_Gasto_Admin)

admin.site.register(Articulo_Gasto, Articulo_Gasto_Admin)

admin.site.register(Tipo_Gasto)

admin.site.register(Entrada_Gasto_Ajuste, Entrada_Gasto_Ajuste_Admin)

admin.site.register(Conceptos_Entradas, Conceptos_Entradas_Admin)

admin.site.register(Factura, Factura_Admin)

admin.site.register(Porcentaje_iva)