from django.urls import path
from . import views


urlpatterns = [
    path('cobranza/pagos', views.pagos_cobranza, name='cobranza-pagos'),
    path('cobranza/pagos/agregar', views.add_pago_cliente, name='add-pago-cliente'),
    path('cobranza/pagos/editar/<int:pk>', views.pagos_edit, name='pagos-edit'),
    #path('configuracion/proyectos/editar/<int:pk>', views.proyectos_edit, name='proyectos-edit'),
    ]