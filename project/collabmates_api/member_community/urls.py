from django.urls import path
from collabmates_api.member_community.views_impl import ViewsImpl, FetchCommunityFeed, FetchHomeCommunities, \
    FetchFeedMeta, FetchChatroomHome, FetchOnboardingCommunities, CompleteCommunityOnboarding, \
    FetchUserDeletedCommunities, FetchMemberDetails, ShowDmMessageIcon, FetchMemberProfileView, EditMemberProfileView, \
    RequestDMLimitView, FetchDMChatroomsView, MemberCanDMView, JoinCommunitySDKView, UnsubscribeEmailNotificationsView,\
    FetchAccessView, FetchPostFeedView, FetchExcludedChatroomsView

urlpatterns = [
    path('', ViewsImpl.get_member_communities, name="get_member_communities"),
    path('fetch_feed', FetchCommunityFeed.as_view(), name="fetch_feed"),
    path('home_communities', FetchHomeCommunities.as_view(), name="home_communities"),
    path('fetch_feed_meta', FetchFeedMeta.as_view(), name="fetch_feed_meta"),
    path('fetch_chatroom_home', FetchChatroomHome.as_view(), name="fetch_chatroom_home"),
    path('fetch_onboarding_communities', FetchOnboardingCommunities.as_view(), name="fetch_onboarding_communities"),
    path('complete_community_onboarding', CompleteCommunityOnboarding.as_view(), name="complete_community_onboarding"),
    path('fetch_deleted', FetchUserDeletedCommunities.as_view(), name="fetch_deleted_communities"),
    path('fetch_members_detail', FetchMemberDetails.as_view(), name="fetch_members_detail"),
    path('show_dm', ShowDmMessageIcon.as_view(), name="show_dm"),
    path('fetch_profile', FetchMemberProfileView.as_view(), name="fetch_member_profile"),
    path('edit_profile', EditMemberProfileView.as_view(), name="edit_member_profile"),
    path('request_dm_limit', RequestDMLimitView.as_view(), name="request_dm_limit"),
    path('fetch_dm_chatrooms', FetchDMChatroomsView.as_view(), name="request_dm_limit"),
    path('can_dm', MemberCanDMView.as_view(), name="member_can_dm"),
    path('join', JoinCommunitySDKView.as_view(), name="join_community_sdk"),
    path('unsubscribe_email_notifications', UnsubscribeEmailNotificationsView.as_view(),
         name="unsubscribe_email_notifications"),
    path('fetch_access', FetchAccessView.as_view(), name="fetch_access"),
    path('post_feed', FetchPostFeedView.as_view(), name="fetch_post_feed"),
    path('excluded_chatrooms', FetchExcludedChatroomsView.as_view(), name="fetch_excluded_chatrooms")
]
