from django.contrib import admin
from .models import Exhibit, Linea_Exhibit, Tipo_Pago_Exhibit
# Register your models here.
admin.site.register(Tipo_Pago_Exhibit)

admin.site.register(Exhibit)
admin.site.register(Linea_Exhibit)