from django.urls import path
from .sdk_views import (CreateSdkView, InitiateSdkView, AuthenticateSdkView)

urlpatterns = [
    path('create', CreateSdkView.as_view(), name="create-sdk"),
    path('initiate', InitiateSdkView.as_view(), name="initiate-sdk"),
    path('authenticate', AuthenticateSdkView.as_view(), name="authenticate-sdk")
]
