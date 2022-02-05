from django.urls import path
from .automate_message_views import AddMessageTemplateView, SendCustomMessageView

urlpatterns = [
    path('template', AddMessageTemplateView.as_view(), name="add-automate-message-template"),
    path('custom_message', SendCustomMessageView.as_view(), name="send-custom-message")
]
