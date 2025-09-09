from django.urls import path
from .import views 

urlpatterns = [
    path('rentabilidad/costos', views.costos, name='rentabilidad-costos'),
    path('rentabilidad/add_costo', views.add_costo, name='add-costo')
]