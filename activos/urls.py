from django.urls import path
from . import views


urlpatterns = [
    path('activos/', views.activos, name='activos'),
    path('activos/agregar', views.add_activo, name='add-activo'),
    path('activos/qr/<int:pk>', views.generate_qr, name='generate-qr'),
    #path('configuracion/proyectos/editar/<int:pk>', views.proyectos_edit, name='proyectos-edit'),
    ]