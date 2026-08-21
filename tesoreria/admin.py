from django.contrib import admin
from .models import Cuenta, Pago, Facturas, Comprobante_saldo_favor, Tipo_Pago, Saldo_Cuenta, Complemento_Pago, EstadoCuenta
from user.models import Profile

class CuentaAdmin(admin.ModelAdmin):
    list_display = ('cuenta','banco','distrito','encargado','status')
    raw_id_fields = ('encargado','visor',)
    filter_horizontal = ('visores',)
    search_fields = ['cuenta','encargado__staff__staff__first_name']

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'visores':
            kwargs['queryset'] = Profile.objects.order_by(
                'staff__staff__first_name',
                'staff__staff__last_name',
            )

        return super().formfield_for_manytomany(
            db_field,
            request,
            **kwargs,
        )

class PagoAdmin(admin.ModelAdmin):
    list_display = ('id','oc','gasto','viatico','tesorero','monto', 'hecho','tipo','cuenta','pagado_real','distrito','control_documentos')
    #list_filter = ('familia',)
    search_fields = ['id','hecho','oc__folio','viatico__folio', 'gasto__folio','cuenta__cuenta','monto']
    raw_id_fields = ('oc','gasto','viatico','tesorero',)


class FacturasAdmin(admin.ModelAdmin):
    search_fields = ['oc__folio','id','uuid']
    raw_id_fields = ('oc',)
    list_display = ('id','oc','factura_pdf')

class ComplementosAdmin(admin.ModelAdmin):
    search_fields = ['id','uuid']
    raw_id_fields = ('facturas',)
    list_display = ('id','complemento_pdf')

class TipoPagoAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_display = ('id','nombre')

class Saldo_Cuenta_Admin(admin.ModelAdmin):
    search_fields = ['cuenta__cuenta']
    list_display = ('id','cuenta','monto_inicial','fecha_inicial')



# Register your models here.
admin.site.register(Cuenta, CuentaAdmin)

admin.site.register(Complemento_Pago, ComplementosAdmin)

admin.site.register(Facturas, FacturasAdmin)

admin.site.register(Pago, PagoAdmin)

admin.site.register(Comprobante_saldo_favor)

admin.site.register(Tipo_Pago, TipoPagoAdmin)

admin.site.register(Saldo_Cuenta, Saldo_Cuenta_Admin)

admin.site.register(EstadoCuenta)