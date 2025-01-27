from django.urls import path
from . import views  # Importa las vistas de la app

urlpatterns = [
    # Ejemplo de ruta (ajusta según tu aplicación)
    path('matriz_oc_proveedores', views.matriz_oc_proveedores , name='matriz-oc-proveedores'),
]