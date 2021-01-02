from django.urls import path
from .view_conversation_impl import FetchConversation, CreateConversation

urlpatterns = [
    path('fetch', FetchConversation.as_view(), name="fetch_conversation"),
    path('create', CreateConversation.as_view(), name="create_conversation")

]
