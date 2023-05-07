from django.contrib import admin
from .models import Proyecto, Subproyecto, Sector, Activo, Operacion, St_Entrega, Cliente

class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre','distrito')
    list_filter = ('distrito',)

class ActivoAdmin(admin.ModelAdmin):
    list_display = ('eco_unidad','distrito','tipo','serie','cuenta','factura_interna')
    list_filter = ('distrito',)

# Register your models here.
admin.site.register(Proyecto, ProyectoAdmin)

admin.site.register(St_Entrega)

admin.site.register(Cliente)

admin.site.register(Subproyecto)

admin.site.register(Sector)

admin.site.register(Activo, ActivoAdmin)

admin.site.register(Operacion)

