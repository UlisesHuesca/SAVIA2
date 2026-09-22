from django.contrib import admin
from dashboard.models import Activo
from .models import Categoria_Activo, Vehiculo_Activo, UBM_Activo
# Register your models here.

 
admin.site.register(Categoria_Activo)

admin.site.register(Vehiculo_Activo)

admin.site.register(UBM_Activo)