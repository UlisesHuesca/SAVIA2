from django.contrib import admin
from .models import Profile, Distrito, Tipo_perfil, Banco, Almacen, CustomUser, Empresa
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
# Register your classes here

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id','staff', 'distritos', 'tipo','st_activo')
    search_fields = ('staff__staff__username','tipo__nombre')
    raw_id_fields = ('staff',)
   
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id','staff', 'empresa',)
    search_fields = ('staff__username',)
    raw_id_fields = ('staff',)

class DistritoAdmin(admin.ModelAdmin):
    list_display = ('id','nombre')

class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('first_name','email')

# Register your models here.

admin.site.register(Profile, ProfileAdmin)

admin.site.register(CustomUser, CustomUserAdmin)

admin.site.register(Distrito, DistritoAdmin)

admin.site.register(Tipo_perfil)

admin.site.register(Banco)

admin.site.register(Almacen)

admin.site.register(Empresa)

# Desregistra el modelo User original y registra el nuevo con la personalización
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


