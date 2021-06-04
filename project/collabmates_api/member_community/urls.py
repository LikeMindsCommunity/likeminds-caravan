from django.urls import path
from collabmates_api.member_community.views_impl import ViewsImpl, FetchCommunityFeed, FetchHomeCommunities, \
    FetchFeedMeta, FetchChatroomHome, FetchOnboardingCommunities, CompleteCommunityOnboarding, \
    FetchUserDeletedCommunities

urlpatterns = [
    path('', ViewsImpl.get_member_communities, name="get_member_communities"),
    path('fetch_feed', FetchCommunityFeed.as_view(), name="fetch_feed"),
    path('home_communities', FetchHomeCommunities.as_view(), name="home_communities"),
    path('fetch_feed_meta', FetchFeedMeta.as_view(), name="fetch_feed_meta"),
    path('fetch_chatroom_home', FetchChatroomHome.as_view(), name="fetch_chatroom_home"),
    path('fetch_onboarding_communities', FetchOnboardingCommunities.as_view(), name="fetch_onboarding_communities"),
    path('complete_community_onboarding', CompleteCommunityOnboarding.as_view(), name="complete_community_onboarding"),
    path('fetch_deleted', FetchUserDeletedCommunities.as_view(), name="fetch_deleted_communities")

]
