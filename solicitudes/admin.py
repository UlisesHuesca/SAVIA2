from django.contrib import admin
from .models import Proyecto, Subproyecto, Sector, Operacion, St_Entrega, Cliente

class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','distrito')
    list_filter = ('distrito',)

class SubproyectoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','proyecto')


# Register your models here.
admin.site.register(Proyecto, ProyectoAdmin)

admin.site.register(St_Entrega)

admin.site.register(Cliente)

admin.site.register(Subproyecto, SubproyectoAdmin)

admin.site.register(Sector)

admin.site.register(Operacion)

