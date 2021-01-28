from django.urls import path
from .view_chatroom_impl import FetchChatroomView, CreateChatroomView

urlpatterns = [
    path('fetch', FetchChatroomView.as_view(), name="fetch_chatroom"),
    path('create', CreateChatroomView.as_view(), name="create_chatroom")

]
