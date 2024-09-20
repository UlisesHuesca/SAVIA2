from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token



urlpatterns = [
    path('inventario', views.getData, name='api'),
    path('compras', views.CompraAPI, name ='compras'),
    path('proveedores', views.proveedores_api, name="proveedores"),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('perfiles_rh/', views.obtener_perfiles, name='perfiles_rh'),

    ]