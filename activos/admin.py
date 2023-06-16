from django.contrib import admin
from .models import Activo, Tipo_Activo
# Register your models here.
class Tipo_Activo_Admin(admin.ModelAdmin):
    list_display = ('nombre',)
    #search_fields = ('oc',)

admin.site.register(Activo)

admin.site.register(Tipo_Activo, Tipo_Activo_Admin)