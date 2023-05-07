from django.urls import path
from . import views


urlpatterns = [
    path('solicitud_viatico/', views.solicitud_viatico, name='solicitud-viatico'),
    path('viaticos/viaticos_pendientes_autorizar/', views.viaticos_pendientes_autorizar, name='viaticos-pendientes-autorizar'),
    path('viaticos/detalles_viaticos/<int:pk>', views.detalles_viaticos, name='detalles-viaticos'),
    path('viaticos/autorizar_viaticos/<int:pk>', views.autorizar_viaticos, name='autorizar-viaticos'),
    path('viaticos/solicitudes_viaticos/', views.solicitudes_viaticos, name='solicitudes-viaticos'),
    path('viaticos/cancelar_viaticos/<int:pk>', views.cancelar_viaticos, name='cancelar-viaticos'),
    path('viaticos/viaticos_autorizados/', views.viaticos_autorizados, name='viaticos_autorizados'),
    path('viaticos/asignar_montos/<int:pk>', views.asignar_montos, name='asignar-montos'),
    path('viaticos/delete_viatico/<int:pk>', views.delete_viatico, name='delete-viatico'),
    path('viaticos/viaticos_pendientes_autorizar2/', views.viaticos_pendientes_autorizar2, name='viaticos-pendientes-autorizar2'),
    path('viaticos/detalles_viaticos2/<int:pk>', views.detalles_viaticos2, name='detalles-viaticos2'),
    path('viaticos/autorizar_viaticos2/<int:pk>', views.autorizar_viaticos2, name='autorizar-viaticos2'),
    path('viaticos/cancelar_viaticos2/<int:pk>', views.cancelar_viaticos2, name='cancelar-viaticos2'),
    path('viaticos/viaticos_autorizados_pago/', views.viaticos_autorizados_pago, name='viaticos-autorizados-pago'),
    path('viaticos/viaticos_pagos/<int:pk>/', views.viaticos_pagos, name='viaticos-pagos'),
    path('viaticos/matriz_facturas_viaticos/<int:pk>/', views.matriz_facturas_viaticos, name='matriz-facturas-viaticos'),
    path('viaticos/matriz_facturas/<int:pk>', views.facturas_viaticos, name='facturas-viaticos'),
    path('viaticos/factura_viatico_edicion/<int:pk>', views.factura_viatico_edicion, name='factura-viatico-edicion'),
]