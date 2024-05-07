from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('compras/requisiciones_autorizadas', views.requisiciones_autorizadas, name='requisicion-autorizada'),
    path('compras/oc/<int:pk>/', views.oc_modal, name='oc'),
    #path('reporte_compras', views.generar_reporte, name='reporte_compras'),
    path('verificar_estado/', views.verificar_estado, name='verificar_estado'),
    path('clear_task_id/', views.clear_task_id, name='clear_task_id'),
    path('verificar_estado_producto/', views.verificar_estado_productos, name='verificar_estado_producto'),
    path('clear_task_id_producto/', views.clear_task_id_productos, name='clear_task_id_producto'),
    path('update_oc/', views.update_oc, name='update-oc'),
    path('compras/matriz_compras/', views.matriz_oc, name='matriz-compras'),
    path('compras/upload_facturas/<int:pk>/', views.upload_facturas, name='upload-facturas'),
    path('compras/upload_xml/<int:pk>/', views.upload_xml, name='upload-xml'),
    path('compras/autorizacion_oc1/',views.autorizacion_oc1, name='autorizacion-oc1'),
    path('compras/autorizacion_oc2/',views.autorizacion_oc2, name='autorizacion-oc2'),
    path('compras/cancelar_oc1/<int:pk>/',views.cancelar_oc1, name='cancelar-oc1'),
    path('compras/regresar_oc/<int:pk>/',views.back_oc, name='back-oc'),
    path('compras/cancelar_oc2/<int:pk>/',views.cancelar_oc2, name='cancelar-oc2'),
    path('compras/autorizar_oc1/<int:pk>/', views.autorizar_oc1, name='autorizar-oc1'),
    path('compras/autorizar_oc2/<int:pk>/', views.autorizar_oc2, name='autorizar-oc2'),
    path('salida_material/oc_pdf/<int:pk>/', views.descargar_pdf, name='oc-pdf'),
    path('compras/pdf_proveedores/<int:pk>/', views. generar_pdf_proveedor , name='generar-pdf-proveedor'),
    path('compras/productos_oc/<int:pk>/', views.productos_oc, name='productos-oc'),
    path('compras/eliminar_articulos/<int:pk>', views.eliminar_articulos, name='eliminar-articulos'),
    path('compras/articulos_restantes/<int:pk>', views.articulos_restantes, name='articulos-restantes'),
    path('compras/productos_pendientes/', views.productos_pendientes, name='productos-pendientes'),
    path('compras/compras_devueltas', views.compras_devueltas,name='compras-devueltas'),
    path('compras/compra_edicion/<int:pk>', views.compra_edicion, name='compra-edicion'),
    path('compras/matriz_oc_productos/', views.matriz_oc_productos, name='matriz-oc-productos'),
    path('compras/comparativos', views.comparativos, name='comparativos'),
    path('compras/crear_comparativo', views.crear_comparativo, name='crear_comparativo'),
    path('carga_proveedor', views.carga_proveedor, name='carga-proveedor'),
    path('carga_proveedor_comparativo', views.carga_proveedor_comparativo, name='carga-proveedor-comparativo'),
    path('carga_productos', views.carga_productos, name='carga-productos'),
    path('compras/articulos_comparativo/<int:pk>', views.articulos_comparativo, name='articulos-comparativo'),
    path('compras/articulo_comparativo_delete/<int:pk>', views.articulo_comparativo_delete, name='articulo-comparativo-delete'),
    path('compras/historico_articulos_compras', views.historico_articulos_compras, name='historico-articulos-compras'),
    path('compras/historico_compras', views.historico_compras, name='historico-compras'),
    path('compras/mostrar_comparativo/<int:pk>', views.mostrar_comparativo, name='mostrar-comparativo'),
    path('editar_comparativo/<int:pk>/', views.editar_comparativo, name='editar-comparativo'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
