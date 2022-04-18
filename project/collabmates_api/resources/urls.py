from django.urls import path

from .resources_view_impl import *


urlpatterns = [
    path('settings/update', ResourceSettings.as_view(), name="update_resource_settings"),
    path('settings/fetch', ResourceSettings.as_view(), name="fetch_resource_settings"),
]
