from django.contrib import admin
from .models import Salidas, Requis, ArticulosRequisitados, ValeSalidas

class RequisAdmin(admin.ModelAdmin):
    list_display = ('id','folio','orden','autorizar')
    list_filter = ('folio',)

class ValeSalidasAdmin(admin.ModelAdmin):
    list_display = ('id','solicitud','complete')

class SalidasAdmin(admin.ModelAdmin):
    list_display = ('id','producto','cantidad','precio','complete','entrada')

# Register your models here.
admin.site.register(Salidas, SalidasAdmin)

admin.site.register(ValeSalidas, ValeSalidasAdmin)

admin.site.register(Requis, RequisAdmin)

admin.site.register(ArticulosRequisitados)