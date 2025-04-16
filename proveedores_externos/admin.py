from django.contrib import admin
from compras.models import InvitacionProveedor
admin.site.site_header = 'SAVIA 2.0 | Administración'
# Register your models here.
admin.site.register(InvitacionProveedor)

