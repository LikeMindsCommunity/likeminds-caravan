from django.urls import path
from .view_chatroom_impl import (FetchChatroomView, CreateChatroomView, PinUnpinChatroomView,
                                 LeaveSecretChatroomView, AddSecretChatroomParticipantView, GetTaggingList,
                                 AutoFollowChatroomForAllMembersView, EditChatroomView,
                                 FetchParticipantsOfSecretChatroom)

urlpatterns = [
    path('fetch', FetchChatroomView.as_view(), name="fetch_chatroom"),
    path('create', CreateChatroomView.as_view(), name="create_chatroom"),
    path('pin', PinUnpinChatroomView.as_view(), name="pin_unpin_chatroom"),
    path('secret/add', AddSecretChatroomParticipantView.as_view(), name="add_secret_room_participant"),
    path('secret/leave', LeaveSecretChatroomView.as_view(), name="leave_secret_chatroom"),
    path('get_tagging_list', GetTaggingList.as_view(), name="get_tagging_list"),
    path('auto_follow_for_all_members', AutoFollowChatroomForAllMembersView.as_view(),
         name="auto_follow_for_all_members"),
    path('edit', EditChatroomView.as_view(), name="edit_chatroom"),
    path('secret/fetch_participants_meta', FetchParticipantsOfSecretChatroom.as_view(),
         name="fetch_participants_of_secret_chatroom"),

]
