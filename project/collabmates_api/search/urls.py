from django.urls import path
from .search_views import ChatroomSearchView, ConversationSearchView

urlpatterns = [
    path('chatroom', ChatroomSearchView.as_view(), name="search_chatroom"),
    path('conversation', ConversationSearchView.as_view(), name="search_conversation"),
]
