from django.urls import path
from .webhook_views import WebhookView

urlpatterns = [
    path('', WebhookView.as_view(), name="webhook")
]
