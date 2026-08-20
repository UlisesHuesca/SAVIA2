from django.urls import path

from . import views

app_name = 'boveda_xml'

urlpatterns = [
    path('', views.lista_cfdi, name='lista_cfdi',),
    path('carga-masiva/', views.carga_masiva_xml, name='carga_masiva_xml',),
    path('cfdi/<int:pk>/pdf/',views.generar_cfdi,name='generar_cfdi',),
    ]