from django.urls import path

from .resources_view_impl import *


urlpatterns = [
    path('settings/update', ResourceSettings.as_view(), name="update_resource_settings"),
    path('settings/fetch', ResourceSettings.as_view(), name="fetch_resource_settings"),

    path('category/create', ResourceCategory.as_view(), name="create_resource_category"),
    path('category/fetch', ResourceCategory.as_view(), name="fetch_resource_category"),
    path('category/update', ResourceCategory.as_view(), name="update_resource_category"),
    path('category/delete', ResourceCategory.as_view(), name="delete_resource_category"),

    path('url/create', ResourceURL.as_view(), name="create_resource_url"),
    path('url/fetch', ResourceURL.as_view(), name="fetch_resource_url"),
    path('url/update', ResourceURL.as_view(), name="update_resource_url"),
    path('url/delete', ResourceURL.as_view(), name="delete_resource_url"),

]
