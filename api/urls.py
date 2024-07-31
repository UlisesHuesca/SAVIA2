from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token



urlpatterns = [
    path('inventario', views.getData, name='api'),
    path('compras', views.CompraAPI, name ='compras'),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    ]