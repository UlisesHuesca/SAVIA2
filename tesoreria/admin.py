from django.contrib import admin
from .models import Cuenta, Pago, Facturas, Comprobante_saldo_favor, Tipo_Pago, Saldo_Cuenta

class CuentaAdmin(admin.ModelAdmin):
    raw_id_fields = ('encargado',)
    search_fields = ['cuenta']

class PagoAdmin(admin.ModelAdmin):
    list_display = ('id','oc','gasto','viatico','tesorero','monto', 'hecho','tipo','cuenta','pagado_real')
    #list_filter = ('familia',)
    search_fields = ['id','hecho','oc__folio','viatico__folio', 'gasto__folio','cuenta__cuenta','uuid']
    raw_id_fields = ('oc','gasto','viatico','tesorero',)


class FacturasAdmin(admin.ModelAdmin):
    search_fields = ['oc__folio','id']
    raw_id_fields = ('oc',)
    list_display = ('id','oc','factura_pdf')


# Register your models here.
admin.site.register(Cuenta, CuentaAdmin)

admin.site.register(Facturas, FacturasAdmin)

admin.site.register(Pago, PagoAdmin)

admin.site.register(Comprobante_saldo_favor)

admin.site.register(Tipo_Pago)

admin.site.register(Saldo_Cuenta)