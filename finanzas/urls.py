# Finanzas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('crear_exhibit', views.crear_exhibit, name='crear-exhibit'),
]
