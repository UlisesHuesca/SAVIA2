from django.urls import path
from . import views


urlpatterns = [
    path('sol_autorizadas/', views.solicitud_autorizada, name='solicitud-autorizada'),
    path('salida_material/<int:pk>/', views.salida_material, name='salida-material'),
    path('sol_autorizadas/firma', views.solicitud_autorizada_firma, name='solicitud-autorizada-firma'),
    path('salida_material/firma/<int:pk>/', views.salida_material_usuario, name='salida-material-usuario'),
    path('sol_autorizadas_orden/', views.solicitud_autorizada_orden, name='solicitud-autorizada-orden'),
    path('autorizacion/', views.requisicion_autorizacion, name='requisicion-autorizacion'),
    path('sol_autorizadas_orden/detalle/<int:pk>/', views.detalle_orden, name='detalle-orden'),
    path('sol_autorizadas_orden/requisicion_detalle/<int:pk>/', views.requisicion_detalle, name='requisicion-detalle'),
    path('sol_autorizadas_orden/requisicion_creada/<int:pk>/', views.requisicion_creada_detalle, name='requisicion-creada-detalle'),
    path('sol_autorizadas_orden/requisicion_autorizar/<int:pk>/', views.requisicion_autorizar, name='requisicion-autorizar'),
    path('sol_autorizadas_orden/requisicion_cancelar/<int:pk>/', views.requisicion_cancelar, name='requisicion-cancelar'),
    path('salida_material/solicitud_pdf/<int:pk>/', views.render_pdf_view, name='solicitud-pdf'),
    path('reporte_entradas/', views.reporte_entradas, name='reporte-entradas'),
    path('reporte_salidas/', views.reporte_salidas, name='reporte-salidas'),
    path('inventario/historico_articulos_para_surtir/', views.historico_articulos_para_surtir, name='historico-articulos-para-surtir'),
    path('salidas/historico_salidas/', views.historico_salidas, name='historico-salidas'),
    ]