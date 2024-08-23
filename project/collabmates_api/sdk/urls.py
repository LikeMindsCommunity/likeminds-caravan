from django.urls import path
from .sdk_views import (SdkProjectView, InitiateSdkView, AuthenticateSdkView, OnboardingScreensView, SdkMauView)

urlpatterns = [
    path('project', SdkProjectView.as_view(), name="sdk-project"),
    path('initiate', InitiateSdkView.as_view(), name="initiate-sdk"),
    path('authenticate', AuthenticateSdkView.as_view(), name="authenticate-sdk"),
    path('onboarding', OnboardingScreensView.as_view(), name="onboarding-screens"),
    path('mau_overview', SdkMauView.as_view(), name="mau-overview")
]
