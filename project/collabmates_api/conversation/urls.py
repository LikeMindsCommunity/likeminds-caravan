from django.urls import path
from .view_conversation_impl import FetchConversation, CreateConversation, AddConversationPollOptions, \
    SubmitConversationPoll, FetchConversationPollUsers

urlpatterns = [
    path('fetch', FetchConversation.as_view(), name="fetch_conversation"),
    path('create', CreateConversation.as_view(), name="create_conversation"),
    path('add_poll', AddConversationPollOptions.as_view(), name="add_poll"),
    path('submit_poll', SubmitConversationPoll.as_view(), name="submit_poll"),
    path('poll_users', FetchConversationPollUsers.as_view(), name="poll_users")

]
