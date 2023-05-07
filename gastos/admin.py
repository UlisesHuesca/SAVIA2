from django.contrib import admin
from .models import Solicitud_Gasto, Articulo_Gasto, Tipo_Gasto



# Register your models here.
class Solicitud_Gasto_Admin(admin.ModelAdmin):
    list_display = ('id','staff','colaborador', 'superintendente','pagada')
    #list_filter = ('familia',)
    search_fields = ('colaborador',)

class Articulo_Gasto_Admin(admin.ModelAdmin):
    list_display =('staff','producto','comentario', 'gasto', 'created_at')

admin.site.register(Solicitud_Gasto, Solicitud_Gasto_Admin)

admin.site.register(Articulo_Gasto, Articulo_Gasto_Admin)

admin.site.register(Tipo_Gasto)