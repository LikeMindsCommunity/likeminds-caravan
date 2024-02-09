from django.urls import path
from .sync_views import (SyncChatrooms, SyncChannelDetail, SyncConversations)

urlpatterns = [
    path('chatrooms', SyncChatrooms.as_view(), name="sync-chatrooms"),
    path('channel_detail', SyncChannelDetail.as_view(), name="sync-channel-detail"),
    path('conversations', SyncConversations.as_view(), name="sync-conversations")
]
