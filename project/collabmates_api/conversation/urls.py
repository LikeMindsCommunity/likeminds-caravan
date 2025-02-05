from django.urls import path
from .view_conversation_impl import (FetchConversation, CreateConversation, AddConversationPollOptions,
                                     SubmitConversationPoll, FetchConversationPollUsers, AddReaction,
                                     RemoveReaction, SetChatroomTopic, ConversationEventAttendView,
                                     SetConversationEventAttendedView, FetchUnseenCountInEvent,
                                     UpdateLastSeenEventChatroom, FetchLinkForEvent, FetchUserAllEvents,
                                     FetchUnreadPreview, FetchPreviewUnreadMessageCount,
                                     CreateMessageTask)

urlpatterns = [
    path('fetch', FetchConversation.as_view(), name="fetch_conversation"),
    path('create', CreateConversation.as_view(), name="create_conversation"),
    path('add_reaction', AddReaction.as_view(), name="add_reaction"),
    path('remove_reaction', RemoveReaction.as_view(), name="remove_reaction"),
    path('add_poll', AddConversationPollOptions.as_view(), name="add_poll"),
    path('submit_poll', SubmitConversationPoll.as_view(), name="submit_poll"),
    path('poll_users', FetchConversationPollUsers.as_view(), name="poll_users"),
    path('set_topic', SetChatroomTopic.as_view(), name="set_topic"),
    path('event/attend', ConversationEventAttendView.as_view(), name="attend_event"),
    path('event/attended', SetConversationEventAttendedView.as_view(), name="set_event_attended"),
    path('event/fetch_unseen_count', FetchUnseenCountInEvent.as_view(), name="fetch_unseen_count"),
    path('event/update_last_seen_event', UpdateLastSeenEventChatroom.as_view(), name="update_last_seen_event"),
    path('event/fetch_link', FetchLinkForEvent.as_view(), name="fetch_link_for_event"),
    path('event/fetch_all', FetchUserAllEvents.as_view(), name="fetch_all_events"),
    path('fetch_unread_previews', FetchUnreadPreview.as_view(), name="fetch_unread_previews"),
    path('fetch_preview_unread_messages_count', FetchPreviewUnreadMessageCount.as_view(),
         name="fetch_preview_unread_messages_count"),
    path('create_message_task', CreateMessageTask.as_view(),
         name="create_message_task")
]
