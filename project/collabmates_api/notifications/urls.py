from django.urls import path

from .tasks_view_impl import SendEventCreationMail


urlpatterns = [
    path('send_event_creation_mail', SendEventCreationMail.as_view(), name="send_event_creation_mail"),
]
