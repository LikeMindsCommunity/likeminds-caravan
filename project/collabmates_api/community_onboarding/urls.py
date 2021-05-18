from django.urls import path
from .community_onboarding_view_impl import OnboardingFetchPinnedChatrooms, OnboardingFetchPollChatrooms, \
    OnboardingFetchEventChatrooms, RecentNDaysConversationChatrooms, RecentNPercentageConversationChatrooms

urlpatterns = [
    path('fetch_pinned_chatrooms', OnboardingFetchPinnedChatrooms.as_view(),
         name='onboarding_fetch_pinned_chatrooms'),

    path('fetch_poll_chatrooms', OnboardingFetchPollChatrooms.as_view(),
         name='fetch_poll_chatrooms'),

    path('fetch_event_chatrooms', OnboardingFetchEventChatrooms.as_view(),
         name='fetch_event_chatrooms'),

    path('recent_n_days_conversation_chatrooms', RecentNDaysConversationChatrooms.as_view(),
         name='recent_n_days_conversation_chatrooms'),

    path('n_percentage_member_conversation_chatrooms', RecentNPercentageConversationChatrooms.as_view(),
         name='n_percentage_member_conversation_chatrooms'),

]
