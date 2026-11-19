from django.contrib import admin
from .models import CFDI

class CFDI_Admin(admin.ModelAdmin):
    list_display = ('uuid','factura_compra','tipo_comprobante','estado_sat')
    search_fields = ['uuid']
    #raw_id_fields = ('',)
# Register your models here.
admin.site.register(CFDI, CFDI_Admin)