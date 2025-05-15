from django.urls import path
from . import views


urlpatterns = [
    path('dashboard/', views.index, name= 'dashboard-index'),
    path('profile_selection', views.select_profile, name='select-profile'),
    path('configuracion/proyectos', views.proyectos, name='configuracion-proyectos'),
    path('configuracion/subproyectos/<int:pk>', views.subproyectos, name='subproyectos'),
    path('configuracion/proyectos/editar/<int:pk>', views.proyectos_edit, name='proyectos-edit'),
    path('configuracion/proyectos/add', views.proyectos_add, name='proyectos-add'),
    path('configuracion/subproyectos_add/<int:pk>', views.subproyectos_add, name='subproyectos-add'),
    path('configuracion/subproyectos_edit/<int:pk>', views.subproyectos_edit, name='subproyectos-edit'),
    path('staff/', views.staff, name='dashboard-staff'),
    path('product/', views.product, name='dashboard-product'),
    path('product_calidad/', views.product_calidad, name='product_calidad'),
    path('product_calidad_add/', views.Add_Product_Critico, name='product_calidad_add'),
    path('product_calidad/<int:pk>/', views.product_calidad_update, name='product_calidad_update'),
    path('product/<int:pk>/add_requerimiento/', views.add_requerimiento_calidad, name='add_requerimiento_calidad'),
    path('eliminar_requerimiento_calidad/<int:pk>/', views.eliminar_requerimiento_calidad, name='eliminar_requerimiento_calidad'),
    path('product/precio_referencia/<int:pk>', views.precio_referencia, name = 'precio-referencia'),
    path('product/upload_batch_products', views.upload_batch_products, name='upload_batch_products'),
    #path('product/delete/<int:pk>/', views.product_delete, name='dashboard-product-delete'),
    path('product/update/<int:pk>/', views.product_update, name='dashboard-product-update'),
    path('product/add/', views.add_product, name='add-product'),
    path('proveedores/', views.proveedores, name='dashboard-proveedores'),
    path('proveedores/add/', views.add_proveedores, name='add_proveedores'),
    path('proveedores/add_nuevo/', views.add_proveedores2, name='add_proveedores2'),
    path('proveedores/add_proveedor_comparativo/', views.add_proveedores_comparativo, name='add_proveedores_comparativo'),
    path('proveedor/matriz_revision_proveedor', views.matriz_revision_proveedor, name='matriz-revision-proveedor'),
    path('proveedor/update/<int:pk>/', views.proveedores_update, name='dashboard-proveedores-update'),
    path('proveedor/direcciones/<int:pk>/', views.proveedor_direcciones, name='proveedor-direcciones'),
    path('proveedor/add_direccion/<int:pk>/', views.add_proveedor_direccion, name='add-proveedor-direccion'),
    path('proveedor/edit_direccion/<int:pk>', views.edit_proveedor_direccion, name='edit_proveedor_direccion'),
    path('proveedores/upload_batch_proveedores', views.upload_batch_proveedores, name='upload_batch_proveedores'),
    path('proveedores/upload_batch_proveedores_direcciones', views.upload_batch_proveedores_direcciones, name='upload_batch_proveedores_direcciones'),
    path('proveedores/documentacion/<int:pk>', views.documentacion_proveedores, name='documentacion-proveedores'),
    path('ajax/load-subfamilias/', views.load_subfamilias, name='ajax_load_subfamilias'),  # <-- rutina en Ajax
    path('dashboard/staff_detail/<int:pk>/', views.staff_detail, name='dashboard-staff-detail'),
    path('dashboard/update_comentario/', views.update_comentario, name='update_comentario'),
    path('proveedores/altas', views.proveedores_altas, name='proveedores-altas'),
]

