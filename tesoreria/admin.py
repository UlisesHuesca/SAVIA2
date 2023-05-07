from django.contrib import admin
from .models import Cuenta, Pago, Facturas

# Register your models here.
admin.site.register(Cuenta)

admin.site.register(Facturas)

admin.site.register(Pago)