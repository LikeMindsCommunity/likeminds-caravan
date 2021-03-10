from django.urls import path
from .view_chatroom_impl import FetchChatroomView, CreateChatroomView, PinUnpinChatroomView

urlpatterns = [
    path('fetch', FetchChatroomView.as_view(), name="fetch_chatroom"),
    path('create', CreateChatroomView.as_view(), name="create_chatroom"),
    path('pin', PinUnpinChatroomView.as_view(), name="pin_unpin_chatroom")

]
