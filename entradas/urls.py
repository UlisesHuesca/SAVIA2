from django.urls import path
from . import views


urlpatterns = [
    path('entradas/pendientes_entrada', views.pendientes_entrada, name='pendientes_entrada'),
    path('entradas/pendientes_entrada/articulos/<int:pk>', views.articulos_entrada, name='articulos_entrada'),
    path('update_entrada/', views.update_entrada, name='update-entrada'),
    path('entradas/pendientes_calidad', views.pendientes_calidad, name='pendientes_calidad'),
    path('entradas/pendientes_calidad/reporte/<int:pk>', views.reporte_calidad, name='reporte_calidad'),
    path('entradas/devolucion_a_proveedor/', views.devolucion_a_proveedor, name='devolucion_a_proveedor'),
    ]