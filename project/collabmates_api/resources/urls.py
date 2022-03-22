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
    path('url/update', ResourceURL.as_view(), name="update_resource_url"),
    path('url/delete', ResourceURL.as_view(), name="delete_resource_url"),

    path('file/create', ResourceFile.as_view(), name="create_resource_file"),
    path('file/update', ResourceFile.as_view(), name="update_resource_file"),
    path('file/delete', ResourceFile.as_view(), name="delete_resource_file"),

    path('reference/create', ResourceReference.as_view(), name="create_resource_reference"),
    path('reference/fetch', ResourceReference.as_view(), name="fetch_resource_reference"),
    path('reference/delete', ResourceReference.as_view(), name="delete_resource_reference"),

    path('state/update', ResourceState.as_view(), name="update_resource_state"),
    path('state/fetch', ResourceState.as_view(), name="fetch_resource_reference"),
]
