from django.urls import path
from collabmates_api.chatroom.view_chatroom_impl import FetchChatroomView

urlpatterns = [
    path('fetch', FetchChatroomView.as_view(), name="fetch_chatroom")

]
