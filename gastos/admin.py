from django.contrib import admin
from .models import Solicitud_Gasto, Articulo_Gasto, Tipo_Gasto, Entrada_Gasto_Ajuste, Conceptos_Entradas
# Register your models here.
class Solicitud_Gasto_Admin(admin.ModelAdmin):
    list_display = ('id','staff','colaborador', 'superintendente','pagada')
    #list_filter = ('familia',)
    search_fields = ('colaborador',)

class Articulo_Gasto_Admin(admin.ModelAdmin):
    list_display =('id','staff','producto','comentario', 'gasto', 'created_at', 'validacion')

class Entrada_Gasto_Ajuste_Admin(admin.ModelAdmin):
    list_display =('id','gasto','almacenista','completo')

admin.site.register(Solicitud_Gasto, Solicitud_Gasto_Admin)

admin.site.register(Articulo_Gasto, Articulo_Gasto_Admin)

admin.site.register(Tipo_Gasto)

admin.site.register(Entrada_Gasto_Ajuste, Entrada_Gasto_Ajuste_Admin)

admin.site.register(Conceptos_Entradas)