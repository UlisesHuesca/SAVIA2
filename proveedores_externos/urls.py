from django.urls import path
from . import views  # Importa las vistas de la app

urlpatterns = [
    # Ejemplo de ruta (ajusta según tu aplicación)
    path('matriz_oc_proveedores', views.matriz_oc_proveedores , name='matriz-oc-proveedores'),
    path('matriz_direcciones', views.matriz_direcciones , name='matriz-direcciones'),
    path('edit_csf/<int:pk>', views.edit_csf, name='edit-csf'),
    path('edit_acta_credencial/<int:pk>', views.edit_acta_credencial, name='edit-acta-credencial'),
    path('edit_comprobante_domicilio/<int:pk>', views.edit_comprobante_domicilio, name='edit-comprobante-domicilio'),
    path('edit_opinion_cumplimiento/<int:pk>', views.edit_opinion_cumplimiento, name='edit-opinion-cumplimiento'),
    path('edit_curriculum/<int:pk>', views.edit_curriculum, name='edit-curriculum'),
    path('edit_competencia/<int:proveedor_id>', views.subir_documento_competencia, name='subir-documento-competencia'),
    path('edit_calidad/<int:pk>', views.edit_calidad, name='edit-calidad'),
    path('edit_otros/<int:pk>', views.edit_otros, name='edit-otros'),
    path('edit_contrato/<int:proveedor_id>', views.subir_documento_contrato, name='subir-documento-contrato'),
    path('edit_factura_predial/<int:proveedor_id>', views.subir_documento_factura_predial, name='subir-documento-factura-predial'),
    path('evidencias_proveedor/<int:pk>', views.evidencias_proveedor, name='evidencias-proveedor'),
    path('subir_evidencias/<int:pk>', views.subir_evidencias, name='subir-evidencias'),
    path('eliminar_evidencia/<int:pk>/', views.eliminar_evidencia, name='eliminar-evidencia'),
    path('update_comentario/', views.update_comentario, name='update_comentario'),
    path('politica/aceptar/', views.aceptar_politica, name='aceptar-politica'),
    path('proveedores/invitar/', views.invitar_proveedor, name='invitar-proveedor'),
    path('registro-proveedor/<uuid:token>/', views.registro_proveedor, name='registro-proveedor'),
]