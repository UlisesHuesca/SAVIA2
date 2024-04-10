from django.contrib import admin
from .models import Cuenta, Pago, Facturas, Comprobante_saldo_favor

class CuentaAdmin(admin.ModelAdmin):
    raw_id_fields = ('encargado',)

class PagoAdmin(admin.ModelAdmin):
    list_display = ('id','oc','gasto','viatico','tesorero','monto', 'hecho')
    #list_filter = ('familia',)
    search_fields = ['id','hecho','oc__folio','viatico__folio', 'gasto__folio']
    raw_id_fields = ('oc','gasto','viatico','tesorero',)


class FacturasAdmin(admin.ModelAdmin):
    search_fields = ['oc__folio']
    raw_id_fields = ('oc',)
    list_display = ('id','oc')

# Register your models here.
admin.site.register(Cuenta, CuentaAdmin)

admin.site.register(Facturas, FacturasAdmin)

admin.site.register(Pago, PagoAdmin)

admin.site.register(Comprobante_saldo_favor)