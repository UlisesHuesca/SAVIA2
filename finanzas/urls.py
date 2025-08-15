# Finanzas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('exhibit', views.matriz_exhibit, name='matriz-exhibit'),
    path('crear_exhibit', views.crear_exhibit, name='crear-exhibit'),
    path('eliminar-linea/<int:linea_id>/', views.eliminar_linea_exhibit, name='eliminar_linea_exhibit'),
    path('generar-exhibit/<int:pk>/', views.generar_exhibit_xml, name='generar-exhibit-xml'),
    path('ver-pagos-relacionados/<int:exhibit_id>/', views.ver_pagos_relacionados, name='ver-pagos-relacionados'),
]
