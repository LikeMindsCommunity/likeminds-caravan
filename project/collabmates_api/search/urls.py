from django.urls import path
from .search_views import ChatroomSearchView, ConversationSearchView, ThirdPartySearchView, MemberDirectorySearchView

urlpatterns = [
    path('chatroom', ChatroomSearchView.as_view(), name="search_chatroom"),
    path('conversation', ConversationSearchView.as_view(), name="search_conversation"),
    path('third_party', ThirdPartySearchView.as_view(), name="third_party_search"),
    path('member_directory', MemberDirectorySearchView.as_view(), name="member_directory_search")
]
