from django.urls import path
from . import views


urlpatterns = [
    path('activos/', views.activos, name='activos'),
    path('activos/agregar', views.add_activo, name='add-activo'),
    path('activos/agregar/<int:pk>', views.add_activo2, name='add-activo2'),
    path('activos/edit/<int:pk>', views.edit_activo, name='edit-activo'),
    path('activos/qr/<int:pk>', views.generate_qr, name='generate-qr'),
    path('activos/asignar_activo/<int:pk>', views.asignar_activo, name='asignar-activo'),
    path('activos/render_pdf_responsiva_activos/<int:pk>/', views.render_pdf_responsiva_activos, name='render-pdf-responsiva-activos'),
    #path('carga_responsable', views.carga_responsable, name='carga-responsable')
    #path('configuracion/proyectos/editar/<int:pk>', views.proyectos_edit, name='proyectos-edit'),
    ]