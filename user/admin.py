from django.contrib import admin
from .models import Profile, Distrito, Tipo_perfil, Banco, Almacen, CustomUser
# Register your classes here

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id','staff', 'distritos', 'tipo')
    search_fields = ('staff__staff__username',)

   
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id','staff', 'empresa', 'image')

class DistritoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre')

# Register your models here.


admin.site.register(Profile, ProfileAdmin)

admin.site.register(CustomUser, CustomUserAdmin)

admin.site.register(Distrito, DistritoAdmin)

admin.site.register(Tipo_perfil)

admin.site.register(Banco)

admin.site.register(Almacen)