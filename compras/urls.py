from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('compras/requisiciones_autorizadas', views.requisiciones_autorizadas, name='requisicion-autorizada'),
    path('compras/oc/<int:pk>/', views.oc_modal, name='oc'),
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
    path('salida_material/oc_pdf/<int:pk>/', views.render_oc_pdf, name='oc-pdf'),
    path('compras/productos_oc/<int:pk>/', views.productos_oc,name='productos-oc')
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
