from django.urls import path
from collabmates_api.community.community_view_impl import FetchCommunity, FetchChatroomFeed

urlpatterns = [
    path('fetch', FetchCommunity.as_view(), name="fetch_community"),
    path('fetch_chatroom_feed', FetchChatroomFeed.as_view(), name="fetch_chatroom_feed")

]

