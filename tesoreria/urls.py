from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('tesoreria/compras_autorizadas', views.compras_autorizadas, name='compras-autorizadas'),
    path('tesoreria/compras_autorizadas/pagos/<int:pk>/', views.compras_pagos, name='compras-pagos'),
    path('tesoreria/matriz_pagos/', views.matriz_pagos, name='matriz-pagos'),
    path('tesoreria/matriz_facturas/<int:pk>', views.matriz_facturas, name='matriz-facturas'),
    path('tesoreria/matriz_facturas_nomodal/<int:pk>', views.matriz_facturas_nomodal, name='matriz-facturas-nomodal'),
    path('tesoreria/factura_compra_edicion/<int:pk>',views.factura_compra_edicion,name='factura-compra-edicion' ),
    path('tesoreria/factura_nueva/<int:pk>', views.factura_nueva, name='factura-nueva'),
    path('tesoreria/factura_eliminar/<int:pk>', views.factura_eliminar, name='factura-eliminar'),
    path('tesoreria/matriz_mis_gastos/', views.mis_gastos, name='mis-gastos'),
    path('tesoreria/matriz_mis_viaticos/', views.mis_viaticos, name='mis-viaticos'),
    ]