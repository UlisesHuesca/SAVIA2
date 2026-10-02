from django.contrib import admin
from dashboard.models import Activo
from .models import Categoria_Activo, Vehiculo_Activo, UBM_Activo, HistorialAsignacionActivo
# Register your models here.
class Historial_Admin(admin.ModelAdmin):
    raw_id_fields = ('responsable_anterior','responsable_nuevo','registrado_por','activo')
    #filter_horizontal = ('visores',)
    search_fields = ['activo']
 
admin.site.register(Categoria_Activo)

admin.site.register(Vehiculo_Activo)

admin.site.register(UBM_Activo)

admin.site.register(HistorialAsignacionActivo, Historial_Admin)