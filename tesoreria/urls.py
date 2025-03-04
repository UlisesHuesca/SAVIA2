from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('tesoreria/compras_por_pagar', views.compras_por_pagar, name='compras-por-pagar'),
    path('tesoreria/compras_autorizadas', views.compras_autorizadas, name='compras-autorizadas'),
    path('tesoreria/compras_autorizadas/pagos/<int:pk>/', views.compras_pagos, name='compras-pagos'),
    path('tesoreria/matriz_pagos/', views.matriz_pagos, name='matriz-pagos'),

    path('mis_comprobaciones_gasto/', views.mis_comprobaciones_gasto, name='mis_comprobaciones_gasto'),
    path('mis_comprobaciones_viatico/', views.mis_comprobaciones_viaticos, name='mis_comprobaciones_viaticos'),

    path('tesoreria/control_cuentas/', views.control_cuentas, name ='control-cuentas'),
    path('tesoreria/control_bancos/<int:pk>', views.control_bancos, name='control-bancos'),
    path('tesoreria/transferencia_cuentas/', views.transferencia_cuentas, name='transferencia-cuentas'),
    path('tesoreria/cargo_abono/', views.cargo_abono, name='cargo-abono'),
    path('tesoreria/saldo_inicial/', views.saldo_inicial, name='saldo-inicial'),
    path('tesoreria/matriz_facturas_nomodal/<int:pk>', views.matriz_facturas_nomodal, name='matriz-facturas-nomodal'),
    path('tesoreria/matriz_complementos/<int:pk>', views.matriz_complementos, name='matriz-complementos'),
    path('tesoreria/factura_compra_edicion/<int:pk>',views.factura_compra_edicion,name='factura-compra-edicion' ),
    path('tesoreria/factura_nueva/<int:pk>', views.factura_nueva, name='factura-nueva'),
    path('tesoreria/complemento_nuevo/<int:pk>', views.complemento_nuevo, name='complemento-nuevo'),
    path('tesoreria/factura_eliminar/<int:pk>', views.factura_eliminar, name='factura-eliminar'),
    path('tesoreria/complemento_eliminar/<int:pk>', views.complemento_eliminar, name='complemento-eliminar'),
    path('tesoreria/matriz_mis_gastos/', views.mis_gastos, name='mis-gastos'),
    path('tesoreria/matriz_mis_viaticos/', views.mis_viaticos, name='mis-viaticos'),
    path('tesoreria/saldo_a_favor/<int:pk>', views.saldo_a_favor, name='saldo-a-favor'),
    path('tesoreria/edit_pago/<int:pk>', views.edit_pago, name='edit-pago'),
    path('tesoreria/edit_comprobante_pago/<int:pk>', views.edit_comprobante_pago, name='edit-comprobante-pago'),
    path('prellenar_formulario/',views.prellenar_formulario, name ='prellenar-formulario'),
    # La URL para el formulario de pagos masivos
    path('tesoreria/masivos/', views.mass_payment_view, name='vista_pagos_masivos'),
    path('tesoreria/layout_pagos/', views.layout_pagos, name='layout_pagos'),
    path('factura_cfdi/<int:pk>/', views.generar_cfdi, name='generar_cfdi'),
   
    ]