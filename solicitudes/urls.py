from django.urls import path
from . import views


urlpatterns = [
    path('', views.product_selection, name='solicitud-product-selection'),
    path('solicitud/resurtimiento', views.product_selection_resurtimiento, name='product_selection_resurtimiento'),
    path('crear/', views.checkout, name='solicitud-checkout'),
    path('crear_resurtimiento/', views.checkout_resurtimiento, name='solicitud-checkout-resurtimiento'),
    path('inventario/product_quantity_edit/<int:pk>/', views.product_quantity_edit, name='product-quantity-edit'),
    path('editar/<int:pk>', views.checkout_editar, name='solicitud-checkout-editar'),
    path('solicitud/matriz', views.solicitud_matriz, name='solicitud-matriz'),
    path('solicitud/matriz-pendientes',views.solicitud_pendiente, name='solicitudes-pendientes'),
    path('solicitud/matriz/productos', views.solicitud_matriz_productos, name='solicitud-matriz-productos'),
    path('solicitud/autorizacion', views.solicitud_autorizacion, name='solicitud-pendientes-autorizacion'),
    path('solicitud/autorizada/<int:pk>/', views.autorizada_sol, name='solicitud-autorizada'),
    path('solicitud/cancelada/<int:pk>/', views.cancelada_sol, name='solicitud-cancelada'),
    path('inventario/', views.inventario, name='solicitud-inventario'),
    path('inventario/delete/<int:pk>/', views.inventario_delete, name='solicitud-inventario-delete'),
    path('inventario/add/', views.inventario_add, name='solicitud-inventario-add'),
    path('inventario/update/<int:pk>/', views.inventario_update_modal, name='solicitud-inventario-update-modal'),
    path('inventario/historico_inventario/', views.historico_inventario, name='historico-inventario'),
    path('detalle_autorizar/<int:pk>', views.detalle_autorizar, name='solicitud-detalle-autorizar'),
    path('ajax/load-subproyectos/', views.load_subproyectos, name='ajax_load_subproyectos'),  # <-- rutina en Ajax
    path('update_item/', views.updateItem, name='update-item'),
    path('update_item_res/', views.updateItemRes, name='update-item-res'),
    path('solicitud/status_sol/<int:pk>', views.status_sol, name='status_sol'),
    #path('reporte_salidas/', views.reporte_salidas, name='reporte-salidas'),
]
