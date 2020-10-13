from django.urls import path, include
from . import views
from collabmates_api import views as api_views
# from collabmates_api.notification import send_poll_notification_manually
from django.views.decorators.csrf import csrf_exempt

#for testing email templates only remove.  in prod/beta
from django.views.generic import TemplateView

urlpatterns = [
    #for testing email templates only. remove in prod/beta
#     path('mail/', TemplateView.as_view(template_name='mails/verify_email_template.html')),
    path('mail/', TemplateView.as_view(template_name='mails/email_otp.html')),

    #path('communities', api_views.communities, name="communities"),
    path('your_communities/<int:user_id>', api_views.your_communities, name="your_communities"),

    path('community/<int:community_id>', api_views.community, name="community"),

    path('similar_communities/<int:community_id>', api_views.similar_community, name="similar_community"),

    path('v1/join_community', views.join_community_responses_version_1, name="join_community_responses_version_1"),

    path('v1/create_community',api_views.create_community_version_1,name='create_community_version_1'),
    path('fetch_community_types', api_views.fetch_community_types, name='fetch_community_types'),
    path('get_basic_directory_options', api_views.get_basic_directory_options, name='get_basic_directory_options'),

    #path('v1/create_community_questions',api_views.create_community_questions,name='create_community_questions'),
    path('v1/edit_questions', api_views.edit_questions_version_1,
         name="edit_questions_version_1"),
    #path('get_onboarding_examples', api_views.get_onboarding_examples,name="get_onboarding_examples"),



    path('dismiss', api_views.dismiss,name="dismiss"),


    path('user/<int:user_id>', api_views.user, name="user"),
    path('edit_user',api_views.edit_user,name="edit_user"),
    path('update_email', api_views.update_email, name="update_email"),
    path('update_mobiles', api_views.update_mobiles, name="update_mobiles"),
    path('send_feedback', api_views.send_feedback, name="send_feedback"),

    path('admins/<int:community_id>', api_views.admins, name="admins"),
    path('members/<int:community_id>', api_views.members, name="members"),
    path('ask_approval', api_views.ask_approval, name="ask_approval"),

    path('create_collabcard', api_views.create_card, name="create_card"),
    path('create_draft_collabcard', api_views.create_draft_collabcard, name="create_draft_collabcard"),

    path('collabcard/<int:card_id>', api_views.collabcard, name="collabcard"),

    path('fetch_chatroom', api_views.fetch_chatroom, name="fetch_chatroom"),
    path('v1/fetch_chatroom', api_views.fetch_chatroom_version_1, name="fetch_chatroom_version_1"),

    path('fetch_chatroom_feed', api_views.fetch_chatroom_feed, name="fetch_chatroom_feed"),
    path('v1/fetch_chatroom_feed', api_views.fetch_chatroom_feed_version_1, name="fetch_chatroom_feed_version_1"),
    path('fetch_community_chatroom_feed', api_views.fetch_community_chatroom_feed, name="fetch_community_chatroom_feed"),


    #path('community_collabcard/<int:community_id>', api_views.community_cards, name="community_cards"),
    path('community_collabcard_invite/<int:community_id>', api_views.community_collabcard_invite, name="community_collabcard_invite"),
    path('v1/community_collabcard/<int:community_id>', api_views.community_cards_version_1,
         name="community_cards_version_1"),


    path('create_answer', api_views.create_answer, name="create_answer"),
    path('create_conversation', api_views.create_conversation, name="create_conversation"),

    path('login',api_views.login_authenticate,name = 'login'),
    path('v1/login',api_views.login_authenticate_version_1,name = 'v1/login'),
    path('generate_otp',api_views.generate_otp,name = 'generate_otp'),
    path('verify_otp',api_views.verify_otp,name = 'verify_otp'),
    path('merge_account',api_views.merge_account,name='merge_account'),

    path('popup',api_views.popup,name='popup'),
    path('snooze_popup',api_views.snooze_popup,name='snooze_popup'),
    path('dismiss_popup',api_views.dismiss_popup,name='dismiss_popup'),
    path('phonebook', api_views.phonebook, name='phonebook'),



    #path('image_upload',api_views.image_upload,name = 'image'),
    path('add_admin/<int:community_id>',api_views.add_admin,name = 'add_admin'),
    path('remove_promoter',api_views.remove_promoter,name = 'remove_promoter'),

    path('pending_members/<int:community_id>',api_views.pending_members,name = 'pending_members'),
    path('join',api_views.request_response,name = 'join'),
    path('pending_members_count/<int:community_id>',api_views.pending_request_count,name = 'pending_request_count'),

    path('collabcard_seen', api_views.collabcards_seen, name='collabcard_seen'),
    path('collabcard_attend', api_views.collabcard_attend, name='collabcard_attend'),
    path('chatroom_mute', api_views.chatroom_mute, name='chatroom_mute'),
    path('chatroom_rename', api_views.chatroom_rename, name='chatroom_rename'),
    path('chatroom_delete', api_views.chatroom_delete, name='chatroom_delete'),
    path('set_chatroom_active', api_views.set_chatroom_active, name='set_chatroom_active'),

    path('conversation_meta', api_views.conversation_meta, name='conversation_meta'),
    path('conversation_seen', api_views.conversation_seen, name='conversation_seen'),
    path('mark_read', api_views.mark_read, name='mark_read'),

    path('my_chatrooms', api_views.my_chatrooms, name='my_chatrooms'),
    path('v1/my_chatrooms', api_views.my_chatrooms_version_1, name='my_chatrooms_version_1'),

    path('fetch_chatroom_inactive', api_views.fetch_chatroom_inactive, name='fetch_chatroom_inactive'),

    path('fetch_info', api_views.fetch_info, name='fetch_info'),
    path('limit_access', api_views.limit_access, name='limit_access'),
    path('skip_community', api_views.skip_community, name='skip_community'),

    path('members_state',api_views.members_state,name='members_state'),
    path('edit_member_profile',api_views.edit_member_profile,name='edit_member_profile'),
    path('remove_from_member',api_views.remove_from_member,name='remove_from_member'),
    path('fetch_community_profile',api_views.fetch_community_profile,name='fetch_community_profile'),
    path('fetch_user_chatrooms', api_views.fetch_user_chatrooms, name='fetch_user_chatrooms'),
    path('fetch_common_communities', api_views.fetch_common_communities, name='fetch_common_communities'),

    path('push', api_views.push, name='push'),
    path('collabcard_follow',api_views.collabcard_follow,name='collabcard_follow'),
    path('accept_invitation',views.accept_invitation,name='accept_invitation'),

    path('edit_community', views.edit_community, name='edit_community'),
    path('v1/edit_community', views.edit_community_version_1, name='edit_community_version_1'),
    path('edit_community_questions', views.edit_community_questions, name='edit_community_questions'),


    #path('upload_attachment',api_views.upload_attachment,name='upload_attachment'),
    path('upload_files', api_views.upload_files, name='upload_files'),

    path('update_location',api_views.update_location,name='upload_location'),
    path('fetch_location/<int:user_id>',api_views.get_user_location,name='fetch_location'),

    path('decode_url', api_views.decode_url, name='decode_url'),

    path('all_members', api_views.all_members, name='all_members'),
    path('get_tagging_list', api_views.get_tagging_list, name='get_tagging_list'),

    path('member_activity', api_views.member_activity, name='member_activity'),

    path('invite_members', api_views.invite_members, name='invite_members'),
    path('get_profile', api_views.get_profile, name='get_profile'),
    path('config', api_views.config, name='config'),
    path('onboarding', api_views.onboarding, name='onboarding'),
    path('push_onboarding', api_views.push_onboarding, name='push_onboarding'),

    path('fetch_report_tags', api_views.fetch_report_tags, name='fetch_report_tags'),
    path('push_report', api_views.push_report, name='push_report'),

    path('community_collabcard_id', api_views.community_collabcard_id, name='community_collabcard_id'),
    path('community_collabcard_meta', api_views.community_collabcard_meta, name='community_collabcard_meta'),

    path('collabcard_poll', api_views.collabcard_poll, name='collabcard_poll'),
    path('v1/collabcard_poll', api_views.collabcard_poll_version_1, name='collabcard_poll_version_1'),

    path('fetch_whatsapp_tool', api_views.fetch_whatsapp_tool, name='fetch_whatsapp_tool'),
    path('questions', api_views.questions, name='questions'),
    path('fetch_master_questions', api_views.fetch_master_questions, name='fetch_master_questions'),

    path('fetch_filters', api_views.fetch_filters, name='fetch_filters'),
    path('push_email', api_views.push_email, name='push_email'),


    #email verify
    path('email_verify', api_views.email_verify, name='email_verify'),
    path('sync_email', api_views.sync_email, name='sync_email'),

    path('test_notification_api',api_views.test_notification_api,name='test_notification_api'),
    path('unread_conversation_notification', api_views.unread_conversation_notification, name='unread_conversation_notification'),

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

    ##############################################################################


    ############################ synching client db apis ##################################

    path('sync_conversation', api_views.sync_conversation, name='sync_conversation'),
    path('sync_members', api_views.sync_members, name='sync_members'),
    path('block_member', api_views.block_member, name='block_member'),

    #######################################################################################

]

app_name = 'collabmates_api'