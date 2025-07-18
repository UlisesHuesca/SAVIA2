# Finanzas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('crear_exhibit', views.crear_exhibit, name='crear-exhibit'),
    path('eliminar-linea/<int:linea_id>/', views.eliminar_linea_exhibit, name='eliminar_linea_exhibit'),
]
