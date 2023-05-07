from django.contrib import admin
from .models import Profile, Distrito, Tipo_perfil, Banco, Almacen
# Register your classes here

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('staff', 'tipo')
    search_fields = ('staff__username',)

# Register your models here.


admin.site.register(Profile, ProfileAdmin)

admin.site.register(Distrito)

admin.site.register(Tipo_perfil)

admin.site.register(Banco)

admin.site.register(Almacen)