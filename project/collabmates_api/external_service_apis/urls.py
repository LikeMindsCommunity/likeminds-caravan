from django.urls import path
from .external_service_apis_view_impl import *

urlpatterns = [
    path('send_email', SendEmailView.as_view(), name="send_email"),
    path('send_wa_bulk_messages', SendWhatsAppMessageView.as_view(), name="send_wa_bulk_message")
]
