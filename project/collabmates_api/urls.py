from django.conf.urls import url
from django.urls import path, include
from . import views, tasks
from collabmates_api import views as api_views
from cms.marketing_banner.banner_views_impl import FetchBannerView
from django.views.generic import TemplateView
from .notification import send_test_notification
from .community.community_view_impl import ApproveOrDeclineCommunity, CommunityJoinView, EditCommunityView

urlpatterns = [

    url('', include('django_prometheus.urls')),
    path('mail/', TemplateView.as_view(template_name='mails/email_otp.html')),
    path('your_communities/<int:user_id>/', include('collabmates_api.member_community.urls')),
    path('home/bottom_menu', api_views.bottom_menu, name='bottom_menu'),

    path('community/<int:community_id>', api_views.community, name="community"),

    path('v1/join_community', CommunityJoinView.as_view(), name="join_community_responses_version_1"),

    path('v1/create_community', api_views.create_community_version_1, name='create_community_version_1'),
    path('fetch_community_types', api_views.fetch_community_types, name='fetch_community_types'),
    path('get_basic_directory_options', api_views.get_basic_directory_options, name='get_basic_directory_options'),

    path('v1/edit_questions', api_views.edit_questions_version_1,
         name="edit_questions_version_1"),

    path('multimedia/', include('collabmates_api.multimedia_operations.urls')),

    path('user/<int:user_id>', api_views.user, name="user"),
    path('edit_user', api_views.edit_user, name="edit_user"),
    path('update_email', api_views.update_email, name="update_email"),
    path('update_mobiles', api_views.update_mobiles, name="update_mobiles"),
    path('send_feedback', api_views.send_feedback, name="send_feedback"),

    path('admins/<int:community_id>', api_views.admins, name="admins"),
    path('members/<int:community_id>', api_views.members, name="members"),

    path('create_draft_collabcard', api_views.create_draft_collabcard, name="create_draft_collabcard"),

    path('fetch_chatroom', api_views.fetch_chatroom, name="fetch_chatroom"),
    path('v2/fetch_chatroom', api_views.fetch_chatroom_version_2, name="fetch_chatroom_version_2"),

    path('fetch_chatroom_feed', api_views.fetch_chatroom_feed, name="fetch_chatroom_feed"),
    path('fetch_community_chatroom_feed', api_views.fetch_community_chatroom_feed,
         name="fetch_community_chatroom_feed"),
    path('community_collabcard_invite/<int:community_id>', api_views.community_collabcard_invite,
         name="community_collabcard_invite"),
    path('v1/login', api_views.login_authenticate_version_1, name='v1/login'),
    path('generate_otp', api_views.generate_otp, name='generate_otp'),
    path('verify_otp', api_views.verify_otp, name='verify_otp'),
    path('merge_account', api_views.merge_account, name='merge_account'),
    path('otp_limit_mail', tasks.international_otp_generate_requests_blocked_mail, name='otp_limit_mail'),

    path('add_admin/<int:community_id>', api_views.add_admin, name='add_admin'),
    path('remove_promoter', api_views.remove_promoter, name='remove_promoter'),

    path('pending_members/<int:community_id>', api_views.pending_members, name='pending_members'),
    path('join', ApproveOrDeclineCommunity.as_view(), name='approve_or_decline_community'),
    path('pending_members_count/<int:community_id>', api_views.pending_request_count, name='pending_request_count'),

    path('collabcard_seen', api_views.collabcards_seen, name='collabcard_seen'),
    path('collabcard_attend', api_views.collabcard_attend, name='collabcard_attend'),
    path('chatroom_mute', api_views.chatroom_mute, name='chatroom_mute'),
    path('chatroom_rename', api_views.chatroom_rename, name='chatroom_rename'),
    path('chatroom_delete', api_views.chatroom_delete, name='chatroom_delete'),
    path('fetch_share_url', api_views.fetch_share_url, name='fetch_share_url'),
    path('set_chatroom_active', api_views.set_chatroom_active, name='set_chatroom_active'),

    path('conversation_meta', api_views.conversation_meta, name='conversation_meta'),
    path('mark_read', api_views.mark_read, name='mark_read'),

    path('v1/my_chatrooms', api_views.my_chatrooms_version_1, name='my_chatrooms_version_1'),

    path('fetch_chatroom_inactive', api_views.fetch_chatroom_inactive, name='fetch_chatroom_inactive'),

    path('fetch_info', api_views.fetch_info, name='fetch_info'),
    path('limit_access', api_views.limit_access, name='limit_access'),
    path('skip_community', api_views.skip_community, name='skip_community'),

    path('members_state', api_views.members_state, name='members_state'),

    # to be depreciated in future
    path('fetch_community_profile', api_views.fetch_community_profile, name='fetch_community_profile'),
    path('edit_member_profile', api_views.edit_member_profile, name='edit_member_profile'),

    path('remove_from_member', api_views.remove_from_member, name='remove_from_member'),
    path('fetch_user_chatrooms', api_views.fetch_user_chatrooms, name='fetch_user_chatrooms'),
    path('fetch_common_communities', api_views.fetch_common_communities, name='fetch_common_communities'),

    path('push', api_views.push, name='push'),
    path('collabcard_follow', api_views.collabcard_follow, name='collabcard_follow'),

    path('edit_community', views.edit_community, name='edit_community'),
    path('v1/edit_community', EditCommunityView.as_view(), name='edit_community_version_1'),
    path('edit_community_questions', views.edit_community_questions, name='edit_community_questions'),

    # path('upload_attachment',api_views.upload_attachment,name='upload_attachment'),
    path('upload_files', api_views.upload_files, name='upload_files'),
    path('v1/upload_files', api_views.upload_files_version_1, name='upload_files_version_1'),

    path('decode_url', api_views.decode_url, name='decode_url'),

    path('all_members', api_views.all_members, name='all_members'),
    path('v1/all_members', api_views.AllMembersVersion1.as_view(), name='all_members_version_1'),
    path('get_tagging_list', api_views.get_tagging_list, name='get_tagging_list'),

    # path('invite_members', api_views.invite_members, name='invite_members'),
    path('get_profile', api_views.get_profile, name='get_profile'),
    path('config', api_views.config, name='config'),

    path('fetch_report_tags', api_views.fetch_report_tags, name='fetch_report_tags'),
    path('push_report', api_views.push_report_v1, name='push_report'),

    path('v1/collabcard_poll', api_views.collabcard_poll_version_1, name='collabcard_poll_version_1'),
    path('questions', api_views.questions, name='questions'),
    path('fetch_master_questions', api_views.fetch_master_questions, name='fetch_master_questions'),

    path('fetch_filters', api_views.fetch_filters, name='fetch_filters'),
    path('push_email', api_views.push_email, name='push_email'),

    path('email_verify', api_views.email_verify, name='email_verify'),
    path('sync_email', api_views.sync_email, name='sync_email'),

    path('test_notification_api', api_views.test_notification_api, name='test_notification_api'),
    path('unread_conversation_notification', api_views.unread_conversation_notification,
         name='unread_conversation_notification'),

    path('create_poll', api_views.create_poll, name='create_poll'),
    path('create_poll_draft', api_views.create_poll_draft_collabcard, name='create_poll_draft'),
    path('submit_poll', api_views.submit_poll, name='submit_poll'),
    path('add_poll', api_views.add_poll, name='add_poll'),
    path('fetch_poll_users', api_views.fetch_poll_users, name='fetch_poll_users'),

    path('fetch_deleted_chatroom', api_views.fetch_deleted_chatroom, name='fetch_deleted_chatroom'),
    path('delete_conversation', api_views.delete_conversation, name='delete_conversation'),
    path('edit_conversation', api_views.edit_conversation, name='edit_conversation'),
    path('fetch_preview', api_views.fetch_preview, name='fetch_preview'),

    ############################ static apis #####################################

    path('fetch_intro_examples', api_views.fetch_intro_examples, name='fetch_intro_examples'),

    # ==================== moderation rights ========================================

    path('fetch_community_manager_rights', api_views.fetch_community_manager_rights,
         name='fetch_community_manager_rights'),
    path('update_community_manager_rights', api_views.update_community_manager_rights,
         name='update_community_manager_rights'),
    path('remove_community_manager', api_views.remove_community_manager, name='remove_community_manager'),
    path('transfer_ownership', api_views.transfer_community_ownership, name='transfer_ownership'),

    path('fetch_member_rights', api_views.fetch_community_member_rights, name='fetch_member_rights'),
    path('update_member_rights', api_views.update_community_member_rights, name='update_member_rights'),
    path('fetch_moderation_history', api_views.fetch_moderation_history, name='fetch_moderation_history'),
    path('fetch_reports', api_views.fetch_reports, name='fetch_reports'),
    path('close_report', api_views.close_report, name='close_report'),

    path('fetch_pending_chatroom', api_views.fetch_pending_chatroom, name='fetch_pending_chatroom'),
    path('action_pending_chatroom', api_views.ActionPendingChatroom.as_view(), name='action_pending_chatroom'),

    path('fetch_management_tools', api_views.fetch_management_tools, name='fetch_management_tools'),
    path('fetch_community_setting_rights', api_views.fetch_community_setting_rights,
         name='fetch_community_setting_rights'),
    path('update_community_rights', api_views.update_community_rights, name='update_community_rights'),
    path('block_member', api_views.block_member, name='block_member'),

    ############################ synching client db apis ##################################

    path('sync_conversation', api_views.SyncConversation.as_view(), name='sync_conversation'),
    path('sync_members', api_views.SyncMembers.as_view(), name='sync_members'),

    path('fetch_user_meta', api_views.fetch_user_meta, name='fetch_user_meta'),

    path('sync_chatrooms', api_views.SyncChatrooms.as_view(), name='sync_chatrooms'),

    path('sync_communities', api_views.SyncCommunities.as_view(), name='sync_communities'),

    path('sync_chatrooms_diff', api_views.SyncChatroomsDiff.as_view(), name='sync_chatrooms_diff'),
    path('sync_conversation_diff', api_views.SyncConversationDiff.as_view(), name='sync_conversation_diff'),

    #######################################################################################
    path('conversation/', include('collabmates_api.conversation.urls')),
    path('block_member', api_views.block_member, name='block_member'),
    path('send_test_notification', send_test_notification, name='send_test_notification'),
    path('chatroom/', include('collabmates_api.chatroom.urls')),
    path('user/', include('collabmates_api.user.urls')),
    path('v1/get_tagging_list', api_views.GetTaggingList.as_view(), name='get_tagging_list_v1'),
    path('community/', include('collabmates_api.community.urls')),
    path('banner/fetch', FetchBannerView.as_view(), name='fetch_banner_for_user'),
    path('home_snackbar/', include('collabmates_api.snackbar.urls')),
    path('community_member/', include('collabmates_api.member_community.urls')),
    path('search/', include('collabmates_api.search.urls')),
    path('community_onboarding/', include('collabmates_api.community_onboarding.urls'), name='community_onboarding'),
    path('community_membership/', include('collabmates_api.community_membership.urls'), name='community_membership'),
    path('cohort/', include('collabmates_api.cohort.urls'), name='community_cohorts'),
    path('external_service_apis/', include('collabmates_api.external_service_apis.urls'), name='external_service_apis'),
    path('notifications/', include('collabmates_api.notifications.urls'), name='notifications'),
    path('automate_message/', include('collabmates_api.automate_message.urls'), name='automate_message'),
    path('webhook', include('collabmates_api.webhook.urls'), name="webhooks"),
    path('sdk/', include('collabmates_api.sdk.urls'), name='sdk'),
    path('sync/', include('collabmates_api.sync.urls'), name='sync')
]

app_name = 'collabmates_api'
