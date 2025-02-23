from django.urls import path
from . import views


urlpatterns = [
    path('solicitud_viatico/', views.solicitud_viatico, name='solicitud-viatico'),
    path('eliminar_punto/', views.eliminar_punto, name='eliminar-punto'),
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
    path('viaticos/detalles_viaticos3/<int:pk>', views.detalles_viaticos3, name='detalles-viaticos3'),
    path('viaticos/autorizar_viaticos2/<int:pk>', views.autorizar_viaticos2, name='autorizar-viaticos2'),
    path('viaticos/cancelar_viaticos2/<int:pk>', views.cancelar_viaticos2, name='cancelar-viaticos2'),
    path('viaticos/viaticos_autorizados_pago/', views.viaticos_autorizados_pago, name='viaticos-autorizados-pago'), #Vista donde se ve la solicitud de viatico
    path('viaticos/viaticos_pagos/<int:pk>/', views.viaticos_pagos, name='viaticos-pagos'),
    path('viaticos/matriz_facturas_viaticos/<int:pk>/', views.matriz_facturas_viaticos, name='matriz-facturas-viaticos'), #Vista donde se ven las facturas
    path('factura_cfdi/<int:pk>/', views.generar_cfdi_viaticos, name='generar_cfdi_viaticos'),
    path('viaticos/matriz_facturas/<int:pk>', views.facturas_viaticos, name='facturas-viaticos'),
    path('viaticos/factura_viatico_edicion/<int:pk>', views.factura_viatico_edicion, name='factura-viatico-edicion'),
    path('viaticos/render_viatico/<int:pk>', views.render_pdf_viatico, name='render-pdf-viatico'),
    path('viaticos/eliminar_factura_viatico/<int:pk>/', views.eliminar_factura_viatico, name='eliminar-factura-viatico'),
    path('viaticos/factura_nueva/<int:pk>', views.factura_nueva_viatico, name='factura-nueva-viatico'), #Agregar factura

]