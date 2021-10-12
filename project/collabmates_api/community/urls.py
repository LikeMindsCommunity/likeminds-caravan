from django.urls import path
from collabmates_api.community.community_view_impl import (FetchCommunity, FetchChatroomFeed,
                                                           DeleteCommunityView, FetchCommunityFeedUrl,
                                                           FetchDiscoverableCommunities,
                                                           FetchCommunityOTLUrl, FetchMembersMeta,
                                                           FetchContentDownloadSettings, UpdateContentDownloadSettings,
                                                           FetchAllCommunities, JoinEmailAddView, JoinEmailFetchView,
                                                           FetchCommunityMeta)

urlpatterns = [
    path('fetch', FetchCommunity.as_view(), name="fetch_community"),
    path('fetch_all', FetchAllCommunities.as_view(), name="fetch_all_communities"),
    path('fetch_chatroom_feed', FetchChatroomFeed.as_view(), name="fetch_chatroom_feed"),
    path('delete',  DeleteCommunityView.as_view(), name="delete_community"),
    path('fetch_feed_url',  FetchCommunityFeedUrl.as_view(), name="fetch_feed_url"),
    path('fetch_discoverable_communities', FetchDiscoverableCommunities.as_view(),
         name="fetch_discoverable_communities"),
    path('fetch_otl_url', FetchCommunityOTLUrl.as_view(), name="fetch_otl_url"),
    path('fetch_members_meta', FetchMembersMeta.as_view(), name="fetch_members"),
    path('fetch_content_download_settings', FetchContentDownloadSettings.as_view(), name="fetch_settings"),
    path('update_content_download_settings', UpdateContentDownloadSettings.as_view(), name="update_settings"),
    path('fetch_community_meta', FetchCommunityMeta.as_view(), name="fetch_community_meta"),
    path('join_email/add', JoinEmailAddView.as_view(), name="add_join_email"),
    path('join_email/fetch', JoinEmailFetchView.as_view(), name="fetch_join_email")
]
