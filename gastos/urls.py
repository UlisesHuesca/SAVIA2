from django.urls import path
from . import views


urlpatterns = [
    path('gasto/crear_gasto', views.crear_gasto, name='crear-gasto'),
    path('gasto/delete/<int:pk>', views.delete_gasto, name='delete-gasto'),
    path('gasto/editar_gasto/<int:pk>/', views.editar_gasto, name='editar-gasto'),
    path('gasto/solicitudes_gasto/', views.solicitudes_gasto, name='solicitudes-gasto'),
    path('gasto/detalle_gastos/<int:pk>/', views.detalle_gastos, name='detalle-gastos'),
    path('gasto/gastos_pendientes_autorizar/', views.gastos_pendientes_autorizar, name='gastos-pendientes-autorizar'),
    path('gasto/gastos_pendientes_autorizar2/', views.gastos_pendientes_autorizar2, name='gastos-pendientes-autorizar2'),
    path('gasto/autorizar_gasto/<int:pk>/', views.autorizar_gasto, name = 'autorizar-gasto'),
    path('gasto/autorizar_gasto2/<int:pk>/', views.autorizar_gasto2, name = 'autorizar-gasto2'),
    path('gasto/cancelar_gasto/<int:pk>/', views.cancelar_gasto, name='cancelar-gasto'),
    path('gasto/eliminar_factura/<int:pk>/', views.eliminar_factura, name='eliminar-factura'),
    path('gasto/cancelar_gasto2/<int:pk>/', views.cancelar_gasto2, name='cancelar-gasto2'),
    path('gasto/pago_gastos_autorizados/', views.pago_gastos_autorizados, name='pago-gastos-autorizados'),
    path('gasto/pago_gasto/<int:pk>/', views.pago_gasto, name='pago-gasto'),
    path('gasto/matriz_facturas_gasto/<int:pk>', views.matriz_facturas_gasto, name='matriz-facturas-gasto'),
    path('gasto/facturas_gasto/<int:pk>', views.facturas_gasto, name='facturas-gasto'),
    path('gasto/matriz_gasto_entrada/', views.matriz_gasto_entrada, name ='matriz-gasto-entrada'),
    path('gasto/entrada/<int:pk>', views.gasto_entrada, name='gasto-entrada'),
    path('gasto/delete_articulo_entrada/<int:pk>', views.delete_articulo_entrada, name='delete-articulo-entrada'),
    path('gasto/render_gasto/<int:pk>', views.render_pdf_gasto, name='render-pdf-gasto'),
    ]