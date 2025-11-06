from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token



urlpatterns = [
    path('productos_api', views.productos_api, name='productos-api'),
    path('inventario_api', views.inventario_api, name='inventario-api'),
    path('solicitudes_api', views.solicitudes_api, name ='solicitudes-api'),
    path('productos_solicitados_api', views.productos_solicitados_api, name ='productos-solicitados-api'),
    path('productos_surtir_api', views.productos_surtir_api, name ='productos-surtir-api'),
    path('requisiciones_api', views.requisiciones_api, name ='requisiciones-api'),
    path('productos_requisitados_api', views.productos_requisitados_api, name ='productos-requisitados-api'),
    path('compras_api', views.CompraAPI, name ='compras-api'),
    path('Compra_tabla_api', views.Compra_tabla_api, name ='Compra-tabla-api'),
    path('productos_comprados_api', views.productos_comprados_api, name ='productos-comprados-api'),
    path('proveedor_direccion_api', views.proveedor_direccion_api, name="proveedor-direccion-api"),
    path('proveedor_api', views.proveedor_api, name="proveedor-api"),
    path('proyectos_api', views.proyectos_api, name="proyectos-api"),
    path('subproyectos_api', views.proyectos_api, name="subproyectos-api"),
    path('monedas_api', views.monedas_api, name="monedas-api"),
    path('distritos_api', views.distritos_api, name="distritos-api"),
    path('profiles_api', views.profiles_api, name="profiles-api"),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('perfiles_rh/', views.obtener_perfiles, name='perfiles_rh'),
    path('tabla_festivos/', views.tabla_festivos, name='tabla_festivos'),
    path('oc-pdf/<int:pk>/', views.descargar_pdf_oc, name='api-oc-pdf'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    ]