from django.urls import path
from .view_chatroom_impl import (FetchChatroomView, CreateChatroomView, PinUnpinChatroomView,
                                 LeaveSecretChatroomView, AddSecretChatroomParticipantView)

urlpatterns = [
    path('fetch', FetchChatroomView.as_view(), name="fetch_chatroom"),
    path('create', CreateChatroomView.as_view(), name="create_chatroom"),
    path('pin', PinUnpinChatroomView.as_view(), name="pin_unpin_chatroom"),
    path('secret/add', AddSecretChatroomParticipantView.as_view(), name="add_secret_room_participant"),
    path('secret/leave', LeaveSecretChatroomView.as_view(), name="leave_secret_chatroom"),

]
