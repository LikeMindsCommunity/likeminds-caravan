from django.urls import path
from .webhook_views import WebhookView, WebhooksView

urlpatterns = [
    path('', WebhooksView.as_view(), name="all-webhooks"),
    path('/<int:webhook_id>', WebhookView.as_view(), name="webhook")
]
