from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token



urlpatterns = [
    path('inventario', views.getData, name='api'),
    path('compras', views.CompraAPI, name ='compras'),
    path('proveedores', views.proveedores_api, name="proveedores"),
    path('proyectos', views.proyectos_api, name="proyectos"),
    path('subproyectos', views.proyectos_api, name="subproyectos"),
    path('monedas', views.monedas_api, name="monedas"),
    path('profiles', views.profiles_api, name="profiles"),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('perfiles_rh/', views.obtener_perfiles, name='perfiles_rh'),
    path('tabla_festivos/', views.tabla_festivos, name='tabla_festivos'),
    path('oc-pdf/<int:pk>/', views.descargar_pdf_oc, name='api-oc-pdf'),
    ]