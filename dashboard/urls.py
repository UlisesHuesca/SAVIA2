from django.urls import path
from . import views


urlpatterns = [
    path('dashboard/', views.index, name= 'dashboard-index'),
    path('configuracion/proyectos', views.proyectos, name='configuracion-proyectos'),
    path('configuracion/proyectos/editar/<int:pk>', views.proyectos_edit, name='proyectos-edit'),
    path('configuracion/proyectos/add', views.proyectos_add, name='proyectos-add'),
    path('staff/', views.staff, name='dashboard-staff'),
    path('product/', views.product, name='dashboard-product'),
    path('product/upload_batch_products', views.upload_batch_products, name='upload_batch_products'),
    path('product/delete/<int:pk>/', views.product_delete, name='dashboard-product-delete'),
    path('product/update/<int:pk>/', views.product_update, name='dashboard-product-update'),
    path('product/add/', views.add_product, name='add-product'),
    path('proveedores/', views.proveedores, name='dashboard-proveedores'),
    path('proveedor/update/<int:pk>/', views.proveedores_update, name='dashboard-proveedores-update'),
    path('proveedor/direcciones/<int:pk>/', views.proveedor_direcciones, name='proveedor-direcciones'),
    path('proveedores/upload_batch_proveedores', views.upload_batch_proveedores, name='upload_batch_proveedores'),
    path('proveedores/upload_batch_proveedores_direcciones', views.upload_batch_proveedores_direcciones, name='upload_batch_proveedores_direcciones'),
    path('order/', views.order, name='dashboard-order'),
    path('ajax/load-subfamilias/', views.load_subfamilias, name='ajax_load_subfamilias'),  # <-- rutina en Ajax
    path('dashboard/staff_detail/<int:pk>/', views.staff_detail, name='dashboard-staff-detail'),
]

