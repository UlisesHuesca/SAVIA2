from django.contrib import admin
from .models import Proyecto, Subproyecto, Sector, Operacion, St_Entrega, Cliente, Contrato, Status_Contrato, Tipo_Proyecto, Clase_Costo_Proyecto, Pozo

class PozoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'distrito', 'contrato', 'cerrar_pozo', 'created_at', 'updated_at')
    list_filter = ('distrito', 'contrato', 'cerrar_pozo')
    search_fields = ['nombre', 'distrito__nombre', 'contrato__nombre']

class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','distrito')
    list_filter = ('distrito',)
    search_fields = ['nombre']

class SubproyectoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','proyecto')
    search_fields = ['nombre','proyecto__nombre']


# Register your models here.


admin.site.register(Proyecto, ProyectoAdmin)

admin.site.register(Tipo_Proyecto)

admin.site.register(Clase_Costo_Proyecto)

admin.site.register(Contrato)

admin.site.register(Status_Contrato)

admin.site.register(St_Entrega)

admin.site.register(Cliente)

admin.site.register(Subproyecto, SubproyectoAdmin)

admin.site.register(Sector)

admin.site.register(Operacion)

admin.site.register(Pozo, PozoAdmin)

