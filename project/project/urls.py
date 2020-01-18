"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import path, re_path, include
from django.conf.urls import url, include
from togther import views
from collabmates_api import views as api_views  
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import admin_login
from utility.utils import page_not_found
from django.shortcuts import render,render_to_response


def handler404(request, exception, template_name="__404__.html"):
    response = render_to_response("__404__.html")
    response.status_code = 404
    return response

def handler500(request, exception, template_name="500.html"):
    response = render_to_response("500.html")
    response.status_code = 500
    return response

urlpatterns = [
    #url(r'^login/$', auth_views.LoginView, name='login'),
    url(r'^logout/$', auth_views.LogoutView, name='logout'),
    url(r'^oauth/', include('social_django.urls', namespace='social')),  # <--
    url(r'^collabmates_admin/', admin.site.urls),
    path('', include('togther.urls'),name= 'togther'),
    path('accounts/login/', views.home, name='login'),
    path('api/', include('collabmates_api.urls'),name= 'api'),
    path('admin_dashboard/',include('dashboard.urls'),name='admin_dashboard'),
    path('utils/', include('utility.urls'), name='utils'),
    path('admin_login', admin_login, name="admin_login"),
    path('page_not_found', page_not_found, name="page_not_found"),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

