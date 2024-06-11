

"""inventoryproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from user import views as user_view
from user.views import CustomPasswordResetView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from user.forms import EmailLoginForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('solicitudes/', include('solicitudes.urls')),
    path('requisiciones/', include('requisiciones.urls')),
    path('compras/', include('compras.urls')),
    path('entradas/', include('entradas.urls')),
    path('tesoreria/', include('tesoreria.urls')),
    path('cobranza/', include('cobranza.urls')),
    path('viaticos/', include('viaticos.urls')),
    path('gastos/', include('gastos.urls')),
    path('activos/', include('activos.urls')),
    path('user/', include('user.urls')),
    path('api/', include('api.urls')),
    path('register/', user_view.register, name='user-register'),
    path('profile/', user_view.profile, name='user-profile'),
    #path('', auth_views.LoginView.as_view(template_name='user/login.html'), name='user-login'),
    path('', auth_views.LoginView.as_view(template_name='user/login.html', authentication_form=EmailLoginForm), name='user-login'),
    path('password-reset/', CustomPasswordResetView.as_view(
        template_name='user/password_reset.html',
        html_email_template_name='user/password_reset_email.html',
        subject_template_name = 'user/password_reset_subject.txt'
    ), name='password-reset'),
    path('logout/', auth_views.LogoutView.as_view(template_name='user/logout.html'), name='user-logout'),
    #path('RH/', include('rh.urls')),   
] 

#+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
