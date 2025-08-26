from django.contrib import admin
from compras.models import InvitacionProveedor, Debida_Diligencia, Miembro_Alta_Direccion, Funcionario_Publico_Relacionado
admin.site.site_header = 'SAVIA 2.0 | Administración'
# Register your models here.
admin.site.register(InvitacionProveedor)

admin.site.register(Debida_Diligencia)
admin.site.register(Miembro_Alta_Direccion)
admin.site.register(Funcionario_Publico_Relacionado)

