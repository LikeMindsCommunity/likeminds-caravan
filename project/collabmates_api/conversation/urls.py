from django.urls import path
from .view_conversation_impl import (FetchConversation, CreateConversation, AddConversationPollOptions,
                                     SubmitConversationPoll, FetchConversationPollUsers, AddReaction,
                                     RemoveReaction, SetChatroomTopic)

urlpatterns = [
    path('fetch', FetchConversation.as_view(), name="fetch_conversation"),
    path('create', CreateConversation.as_view(), name="create_conversation"),
    path('add_reaction', AddReaction.as_view(), name="add_reaction"),
    path('remove_reaction', RemoveReaction.as_view(), name="remove_reaction"),
    path('add_poll', AddConversationPollOptions.as_view(), name="add_poll"),
    path('submit_poll', SubmitConversationPoll.as_view(), name="submit_poll"),
    path('poll_users', FetchConversationPollUsers.as_view(), name="poll_users"),
    path('set_topic', SetChatroomTopic.as_view(), name="set_topic")
]
