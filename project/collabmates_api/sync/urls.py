from django.urls import path
from .sync_views import (SyncChatrooms, SyncConversations)

urlpatterns = [
    path('chatrooms', SyncChatrooms.as_view(), name="sync-chatrooms"),
    path('conversations', SyncConversations.as_view(), name="sync-conversations")
]
