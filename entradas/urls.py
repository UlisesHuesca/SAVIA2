from django.urls import path
from . import views


urlpatterns = [
    path('entradas/pendientes_entrada', views.pendientes_entrada, name='pendientes_entrada'),
    path('entradas/entrada_servicios', views.entrada_servicios, name='entrada-servicios'),
    path('entradas/pendientes_entrada/articulos/<int:pk>', views.articulos_entrada, name='articulos-entrada'),
    path('entradas/entrada_been_used', views.entrada_usada, name='entrada-usada'),
    path('entradas/pendientes_entrada/servicios/<int:pk>', views.articulos_entrada_servicios, name='articulos-entrada-servicios'),
    path('update_entrada/', views.update_entrada, name='update-entrada'),
    path('entradas/pendientes_calidad', views.pendientes_calidad, name='pendientes_calidad'),
    path('entradas/pendientes_calidad/reporte/<int:pk>', views.reporte_calidad, name='reporte_calidad'),
    path('entradas/devolucion_a_proveedor/', views.devolucion_a_proveedor, name='devolucion_a_proveedor'),
    path('entradas/no_conformidad/<int:pk>', views.no_conformidad, name='no-conformidad'),
    path('entradas/productos/<int:pk>', views.productos, name="productos"),
    path('no_conformidad/', views.update_no_conformidad, name="update_no_conformidad"),
    path('entradas/reportes_calidad',views.matriz_reportes_calidad, name='matriz-reportes-calidad'),
    path('entradas/matriz_nc', views.matriz_nc, name = 'matriz-nc'),
    path('entradas/productos_nc/<int:pk>', views.productos_nc, name="productos-nc"),
    path('entradas/cierre_nc/<int:pk>', views.cierre_nc, name="cierre-nc"),
    ]