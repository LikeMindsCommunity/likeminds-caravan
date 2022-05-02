from django.urls import path
from .sdk_views import CreateSdkView, InitiateSdkView

urlpatterns = [
    path('create', CreateSdkView.as_view(), name="create-sdk"),
    path('initiate', InitiateSdkView.as_view(), name="initiate-sdk")
]
