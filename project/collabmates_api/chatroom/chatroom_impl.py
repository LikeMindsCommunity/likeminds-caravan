import json
from datetime import datetime
import time
from typing import Union
from rest_framework import status as status_codes
from django.contrib.auth.models import User
from django.db.models import Q

from utility.string_utilities import StringUtilities
from ..chatroom.chatroom_manager import ChatroomManager
from ..serializers import (get_preview_for_url, get_chatroom_instance, CommunitySerializer,
                           CollabcardSerializer, UserinfoSerializer, HOURS_24)
from ..sync.model_update import update_models_for_syncing_apis
from ..views import (adding_guest_in_chatroom, get_chatroom_actions, get_expiry_time_of_chatroom,
                     create_chatroom_state_instance, get_icons_states_of_chatroom_version_1,
                     save_the_latest_conversation, collabcard_follow_internal,
                     send_chatroom_creation_notifications_and_mails, update_seen_status_for_new_user_in_chatroom,
                     create_chatroom, get_latest_conversation_members, )
from ..tasks import update_pending_chatroom_count_for_promoters
from ..notification import (get_tagged_members_list, send_notification_to_event_co_hosts,
                            schedule_poll_end_notification, send_ice_breaker_notification, send_sync_notification,
                            send_pin_chatroom_notification, send_notification_for_new_secret_room_participant,
                            send_notification_for_removed_secret_room_participant)
from ..user.user_impl import UserHelper

from togther.models import (Members, Collabcard, card_answers, Community,
                            collabcardState, conversationEngage, userMemberRights,
                            CollabcardPolls, draftChatroom, draftPolls, ModelUtilities)
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import chatroom_states, member_states, card_types, collabcard_states, SyncNotificationTypes, \
    SyncTypes

from utility.request_utilities import RequestUtilities
from utility.utils import decode_meta_from_url, check_notification_flag
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.celery_tasks import set_chatroom_state_for_all_members_on_card_creation, get_chatroom_user_images_for_web, \
    schedule_chatroom_unpinning_after_event_completion
from utility.firebase import update_last_answer_id
from utility.exception_utilities import (InvalidUserException, InvalidCommunityException,
                                         InvalidHeaderException, CustomException)
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ChatroomImpl(ChatroomManager):
    member_id = None
    chatroom_id = None
    source_id = None
    aj = None

    def __init__(self, member_id: str, chatroom_id: str = None, source_id: str = None, aj: str = None):
        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.source_id = source_id
        self.aj = aj

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def set_member_id(self, member_id: Union[str, int]) -> None:
        self.member_id = member_id

    def get_chatroom_id(self):
        return self.chatroom_id

    def set_chatroom_id(self, chatroom_id):
        self.chatroom_id = chatroom_id

    def get_source_id(self):
        return self.source_id

    def set_source_id(self, source_id):
        self.source_id = source_id

    def get_aj(self):
        return self.aj

    def set_aj(self, aj):
        self.aj = aj

    def _is_user_guest(self, card_instance):

        is_guest = False
        if card_instance:
            if self.get_aj() and self.get_source_id():
                is_guest = True

        return is_guest

    def _make_user_chatroom_guest(self, card_instance):
        guest_context = adding_guest_in_chatroom({}, card_instance, self.get_aj(), self.get_source_id(),
                                                 card_instance.community.id, current_user_id=self.get_member_id())
        return guest_context

    def _fetch_chatroom_dict(self, card_instance):
        chatroom_obj = get_chatroom_instance(card_instance, self.get_member_id())

        return chatroom_obj

    def _fetch_chatroom_internal_link(self, card_instance):

        if card_instance.internal_link:
            try:
                preview = get_preview_for_url(self.get_member_id(), card_instance.internal_link,
                                              community_instance=card_instance.preview_community,
                                              chatroom_instance=card_instance.preview_chatroom,
                                              send_preview_text=False)

                return preview

            except Exception as e:
                error_logger.error(e.args)

    def _fetch_total_response_count(self, card_instance):

        total_response_count = card_answers.objects.filter(card=card_instance,
                                                           state=chatroom_states.ANSWER
                                                           ).filter(Q(attachment_count=0) |
                                                                    Q(attachments_uploaded=True)
                                                                    ).count()

        return total_response_count

    def _fetch_card_status(self, chatroom_data):

        card_status = {
            'state': chatroom_data['state'],
            'mute_status': chatroom_data['mute_status'],
            'follow_status': chatroom_data['follow_status'],
            'attending_status': chatroom_data['attending_status'],
            'is_guest': chatroom_data['is_guest'],
            'type': chatroom_data['type'],
            'is_tagged': chatroom_data['is_tagged'],
            'active': chatroom_data['active']
        }

        return card_status

    def _fetch_chatroom_actions(self, card_instance, chatroom_data):

        card_status = self._fetch_card_status(chatroom_data)
        is_promoter = False
        is_child = False
        parent_list = []
        member_instance = Members.objects.filter(member_id=self.get_member_id(),
                                                 community_id=card_instance.community).filter(
            Q(state=member_states.ADMIN))

        if member_instance.exists():
            is_promoter = True
            parent_cm_list = member_instance[0].parent_cm_list
            parent_list = json.loads(parent_cm_list) if parent_cm_list else []
            is_child = str(card_instance.user.id) in parent_list

        is_card_creator = False

        if self.get_member_id() and int(self.get_member_id()) == card_instance.user.id:
            is_card_creator = True
        # sending the chatroom actions
        chatroom_actions = get_chatroom_actions(card_status, creator=is_card_creator, card_instance=card_instance,
                                                promoter=is_promoter,
                                                current_user_instance=self.get_member_id(),
                                                community_instance=card_instance.community, is_child=is_child,
                                                parent_list=parent_list
                                                )
        return chatroom_actions

    def _save_external_seen_in_chatroom_state(self, card_instance, user_instance):

        chatroom_state = collabcardState.objects.filter(card=card_instance, user=self.get_member_id())
        # if the user is seeing this chatroom from external link or notification
        if not chatroom_state.exists() and user_instance:
            expire_at = get_expiry_time_of_chatroom()
            create_chatroom_state_instance(card_instance, user_instance, state=0, external_seen=True,
                                           expire_at=expire_at,
                                           function_called="get_chatroom_internal_version_1")
        elif user_instance:
            instance = chatroom_state[0]
            if not instance.external_seen:
                instance.external_seen = True
                instance.expiry_time = get_expiry_time_of_chatroom()
                instance.save()

    def _fetch_icon_states_for_chatroom(self, card_instance, chatroom_data):

        icons = {}
        card_status = self._fetch_card_status(chatroom_data)
        icon_states = get_icons_states_of_chatroom_version_1(card_status, card_instance, self.get_member_id())
        icons['show_follow_telescope'] = icon_states['show_follow_telescope']
        icons['show_follow_auto_tag'] = icon_states['show_follow_auto_tag']
        icons['show_active'] = icon_states['show_active']

        return icons

    def _fetch_number_of_unread_messages(self, card_instance, user_instance):

        engage_filter = conversationEngage.objects.filter(card=card_instance, user=user_instance)
        unseen_count = 0
        if engage_filter.exists():
            unseen_count = engage_filter[0].unseen_count
        return unseen_count

    def _save_latest_conversation_on_screen(self, card_instance):

        save_the_latest_conversation(card_instance, self.get_member_id())

    def _chatroom_participants_count(self, card_instance):

        return collabcardState.objects.filter(follow_status=True, card=card_instance, remove=None,
                                              is_tagged=False).count()

    def _fill_chatroom_basic_info(self, card_content, title, community, user, chatroom_type):
        card_content['title'] = title
        card_content['community'] = community
        card_content['user'] = user
        card_content['type'] = chatroom_type

    @staticmethod
    def fill_pinned_information(card_content):

        if card_content['type'] == card_types.CARD_PURPOSE or\
                card_content['type'] == card_types.CARD_MASTER_INTRO or\
                card_content['type'] == card_types.CARD_EVENT or\
                card_content['type'] == card_types.CARD_PUBLIC_EVENT:

            card_content['is_pinned'] = True
            card_content['pinning_time'] = TimeUtilities.current_time_in_milliseconds()

    def _fill_secret_room_details(self, card_content, req_body, community):

        if req_body.get("is_secret", False) and \
                req_body.get("secret_chatroom_participants", None):
            card_content['is_secret'] = True

            secret_chatroom_participants = req_body.get("secret_chatroom_participants", None)

            if secret_chatroom_participants:
                cm_list = set(Members.get_managers_list(community=community))
                final_participants_list = list(set(secret_chatroom_participants) | cm_list)
                card_content['secret_chatroom_participants'] = json.dumps(final_participants_list)

    def _fill_chatroom_attachment_count(self, card_content, req_body):
        card_content['image_count'] = req_body.get('image_count', 0)
        card_content['pdf_count'] = req_body.get('pdf_count', 0)
        card_content['video_count'] = req_body.get('video_count', 0)
        card_content['audio_count'] = req_body.get('audio_count', 0)
        card_content['has_files'] = req_body.get('has_files', False)

        card_content['attachment_count'] = req_body.get('attachment_count', 0)
        card_content['attachments_uploaded'] = False

        if card_content['attachment_count'] == 0 and card_content['pdf_count'] > 0:
            card_content['attachment_count'] = card_content['pdf_count']

        if card_content['attachment_count'] > 0 or card_content['pdf_count'] > 0:
            card_content['has_files'] = True
            req_body['has_files'] = True

    def _fill_chatroom_epoch_time(self, card_content, req_body) -> None:
        card_content['date_time'] = req_body.get('date_time', 0)
        card_content['duration'] = req_body.get('duration', 0)
        card_content['start_date'] = req_body.get('start_date', 0)

        if card_content['type'] == card_types.CARD_POLL:
            # for saving poll expiry time
            expiry_time = req_body.get('expiry_time', 0)
            if expiry_time > 0:
                # rounding off epoch time into exact minute
                # removing any extra seconds
                expiry_time = expiry_time // 1000
                expiry_time = expiry_time - (expiry_time % 60)

            card_content['end_date'] = expiry_time * 1000
        else:
            card_content['end_date'] = req_body.get('end_date', 0)

        card_content['date_epoch'] = TimeUtilities.current_time_in_sec()

    def _fill_chatroom_event_details(self, req_body, card_content):
        card_content['location'] = req_body.get('location', None)
        card_content['location_lat'] = req_body.get('location_lat', None)
        card_content['location_long'] = req_body.get('location_long', None)

        card_content['about'] = req_body.get('about', None)
        card_content['co_hosts'] = json.dumps(req_body['co_hosts']) if ('co_hosts' in req_body) else None
        card_content['online_link'] = req_body.get('online_link', None)

    def _fill_chatroom_poll_details(self, card_content, req_body):
        card_content['poll_type'] = req_body.get('poll_type', None)
        card_content['is_poll_anonymous'] = req_body.get('is_anonymous', None)
        card_content['allow_add_option'] = req_body.get('allow_add_option', None)
        card_content['multiple_select'] = req_body.get('multiple_select', False)
        card_content['multiple_select_no'] = req_body.get('multiple_select_no', None)
        card_content['multiple_select_state'] = req_body.get('multiple_select_state', None)

    def _fill_chatroom_header(self, card_content, req_body, chatroom_type, chatroom_name, decoded_chatroom_title):

        card_type = chatroom_type
        has_been_named = False
        if 'header' in req_body:
            card_content['header'] = req_body['header']
            has_been_named = True
            card_content['has_been_named'] = has_been_named

        else:

            decoded_title = decoded_chatroom_title

            if len(decoded_title) <= 30:
                card_content['header'] = decoded_title[:30]
            else:
                card_content['header'] = decoded_title[:27] + "..."

            if card_type == card_types.CARD_PURPOSE:
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True
            elif card_type == card_types.CARD_INTRO:
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True
            else:
                card_content['has_been_named'] = has_been_named

    def _add_og_tags(self, req_body, card_content):
        if 'share_link' in req_body:
            card_content['share_link'] = req_body['share_link']
            og_tags = decode_meta_from_url(req_body['share_link'])
            card_content['og_tags'] = json.dumps(og_tags)

    def _check_and_set_chatroom_pending_status(self, card_content, is_intro_card, user_has_auto_approve_right):
        if not user_has_auto_approve_right and not is_intro_card:
            card_content['is_pending'] = True

    def _create_chatroom_with_contents(self, card_content):
        chatroom_instance = Collabcard(**card_content)
        self._save_chatroom_instance(chatroom_instance)

        return chatroom_instance

    def _save_chatroom_instance(self, chatroom_instance):
        chatroom_instance.save()

    def _add_preview_from_internal_link(self, chatroom_instance, req_body) -> None:
        preview_utilities = PreviewUtilities()
        preview_utilities.set_preview_object(chatroom_instance, req_body, self.get_member_id())

        self._save_chatroom_instance(chatroom_instance)

    def _create_chatroom_polls(self, user_instance, chatroom_instance, req_body) -> None:
        polls = req_body.get('polls', None)

        if polls is None:
            return

        poll_instances = [
            CollabcardPolls(
                card=chatroom_instance,
                user=user_instance,
                text=poll['text'],
                sub_text=poll['sub_text'] if ('sub_text' in poll) else None,
                image_url=poll['image_url'] if ('image_url' in poll) else None
            )
            for poll in polls
        ]
        self._bulk_create_polls(poll_instances)

    def _bulk_create_polls(self, poll_instances) -> None:
        CollabcardPolls.objects.bulk_create(poll_instances)

    def _delete_draft(self, req_body) -> None:
        if 'draft_id' in req_body:
            conversationEngage.objects.filter(draft_id=req_body['draft_id']).delete()
            draftChatroom.objects.filter(id=req_body['draft_id']).delete()
            draftPolls.objects.filter(draft=req_body['draft_id']).delete()

    def _send_follow_notifications_to_tagged_members(self, tagged_members_list):
        for user_id in tagged_members_list:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    def _send_follow_notifications_to_secret_room_participants(self, participants_list):
        for user_id in participants_list:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

    def _send_follow_notifications_to_event_co_hosts(self, req_body, chatroom_title, user_name):

        if 'co_hosts' not in req_body:
            return

        co_hosts = req_body.get('co_hosts', [])
        # making the co_host auto follow the card
        for user_id in co_hosts:
            req_dict = ChatroomHelper.get_follow_user_dict(user_id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

        send_notification_to_event_co_hosts.delay(co_hosts, self.get_chatroom_id(),
                                                  chatroom_title, user_name)

    def _send_chatroom_creation_notifications(self, user_instance, community_id, community_name,
                                              chatroom_instance, card_content, user_has_auto_approve_right,
                                              chatroom_type, is_intro_chatroom):

        if chatroom_type == card_types.CARD_POLL and user_has_auto_approve_right:
            # sending polls notification
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance)

        if user_has_auto_approve_right or is_intro_chatroom:
            # create relevant flags for first time conversation
            notification_list = [
                'mail_card_owner_inactivity'
            ]
            check_notification_flag(self.get_member_id(), notification_list,
                                    card_id=self.get_chatroom_id(), community_id=None)

        # send notification to new chatroom posted
        if card_content['has_been_named']:
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance)

    def _send_additional_notifications_and_tasks_after_room_creation(self, user_instance, community_instance,
                                                                     chatroom_instance, req_body,
                                                                     is_intro_chatroom, user_has_auto_approve_right,
                                                                     community_id):
        create_intro = 'create_intro' in req_body
        if create_intro:
            update_seen_status_for_new_user_in_chatroom(community_instance, user_instance)
            # intro room notification
            send_chatroom_creation_notifications_and_mails(chatroom_instance, user_instance)

        if user_has_auto_approve_right or is_intro_chatroom or create_intro:
            # following the user created chatroom

            req_dict = ChatroomHelper.get_follow_user_dict(self.get_member_id(), self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

            update_last_answer_id(self.get_chatroom_id(), "")

            # creating default conversation for chatroom creation
            create_chatroom(card_instance=chatroom_instance, user_instance=user_instance,
                            state=chatroom_states.CHATROOM_HEADER, current_user_id=self.get_member_id())

            send_ice_breaker_notification.delay(community_id, time.time(), day=0)

            # batch update for already existing users and saving their unseen count
            if not chatroom_instance.is_secret:
                set_chatroom_state_for_all_members_on_card_creation.delay(community_id,
                                                                          card_id=self.get_chatroom_id(),
                                                                          function_called="create_card_internal")
        else:
            update_pending_chatroom_count_for_promoters.delay(community_id)

    def _latest_conversations_user_data(self):

        conversation_users_meta = get_chatroom_user_images_for_web(self.get_chatroom_id())
        conversation_users = get_latest_conversation_members(conversation_users_meta['last_conversation_member'],
                                                             conversation_users_meta['second_last_conversation_member'],
                                                             conversation_users_meta['last_conversation_user'],
                                                             conversation_users_meta['second_last_conversation_user'])

        return conversation_users

    def fetch_chatroom(self) -> dict:

        card_instance = ChatroomHelper.fetch_card_instance(self.get_chatroom_id())

        if not card_instance:
            context = {
                'error_message': "invalid chatroom id"
            }
            return context

        user_instance = ChatroomHelper.fetch_user_instance(self.get_member_id())
        chatroom_data = self._fetch_chatroom_dict(card_instance)

        if self._is_user_guest(card_instance):
            guest_context = self._make_user_chatroom_guest(card_instance)
            chatroom_data.update(guest_context)

        preview = self._fetch_chatroom_internal_link(card_instance)

        if preview:
            chatroom_data['preview'] = preview
        chatroom_icons = self._fetch_icon_states_for_chatroom(card_instance, chatroom_data)
        chatroom_data.update(chatroom_icons)

        chatroom_obj = {}
        chatroom_obj['chatroom'] = chatroom_data
        chatroom_obj['chatroom_actions'] = self._fetch_chatroom_actions(card_instance, chatroom_data)
        chatroom_obj['total_response_count'] = self._fetch_total_response_count(card_instance)
        chatroom_obj['community'] = ChatroomHelper.fetch_serialized_community(card_instance, user_instance,
                                                                              self.get_member_id())
        chatroom_obj['unread_messages'] = self._fetch_number_of_unread_messages(card_instance, user_instance)
        chatroom_obj['participant_count'] = self._chatroom_participants_count(card_instance)
        chatroom_obj['conversation_users'] = self._latest_conversations_user_data()
        self._save_external_seen_in_chatroom_state(card_instance, user_instance)
        self._save_latest_conversation_on_screen(card_instance)

        return chatroom_obj

    def create_chatroom(self, req_body: dict) -> dict:

        community_id = req_body.get('community_id', None)

        if not community_id:
            response = {
                'success': False,
                'error_message': 'Send community id in body'
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        user_instance = ChatroomHelper.fetch_user_instance_or_raise_exception(self.get_member_id())
        community_instance = ChatroomHelper.fetch_community_instance(community_id=community_id)

        ChatroomHelper.is_user_community_member_or_raise_exception(community=community_instance,
                                                                   user=user_instance)

        member_state = ChatroomHelper.fetch_member_state_in_community(user=user_instance,
                                                                      community=community_instance)

        user_has_auto_approve_right = ChatroomHelper.check_user_auto_approve_right(user=user_instance,
                                                                                   community=community_instance)
        chatroom_name = req_body['title']

        tagged_members = get_tagged_members_list(chatroom_name)

        chatroom_type = int(req_body.get('type', card_types.CARD_NORMAL))
        is_intro_card = chatroom_type == card_types.CARD_INTRO

        card_content = {}

        self._fill_chatroom_basic_info(card_content, chatroom_name,
                                       community_instance, user_instance, chatroom_type)
        self._fill_chatroom_attachment_count(card_content, req_body)
        self._fill_chatroom_epoch_time(card_content, req_body)

        self._fill_chatroom_event_details(card_content=card_content, req_body=req_body)
        self._fill_chatroom_poll_details(card_content, req_body)
        self._fill_chatroom_header(card_content, req_body, chatroom_type, chatroom_name, tagged_members[1])

        self._add_og_tags(req_body=req_body, card_content=card_content)
        self._check_and_set_chatroom_pending_status(card_content, is_intro_card, user_has_auto_approve_right)
        self.fill_pinned_information(card_content)

        self._fill_secret_room_details(card_content, req_body, community_instance)

        card_content['member_state'] = member_state

        chatroom_instance = self._create_chatroom_with_contents(card_content=card_content)
        self.set_chatroom_id(chatroom_instance.id)

        self._add_preview_from_internal_link(chatroom_instance, req_body)
        self._create_chatroom_polls(user_instance, chatroom_instance, req_body)
        self._delete_draft(req_body)

        self._send_chatroom_creation_notifications(user_instance, community_id, community_instance.name,
                                                   chatroom_instance, card_content, user_has_auto_approve_right,
                                                   chatroom_type, is_intro_card)

        if user_has_auto_approve_right or is_intro_card:
            self._send_follow_notifications_to_tagged_members(tagged_members_list=tagged_members[0])

        if chatroom_instance.is_secret:
            participants_list = json.loads(chatroom_instance.secret_chatroom_participants)
            self._send_follow_notifications_to_secret_room_participants(participants_list)

        self._send_follow_notifications_to_event_co_hosts(req_body, chatroom_name,
                                                          user_instance.userinfo.name)

        self._send_additional_notifications_and_tasks_after_room_creation(user_instance, community_instance,
                                                                          chatroom_instance, req_body,
                                                                          is_intro_card, user_has_auto_approve_right,
                                                                          community_id)

        ChatroomHelper.update_time_for_community_members_on_card_creation(community_instance)

        send_sync_notification.delay({'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                      'community_id': community_id})

        if chatroom_instance.type == card_types.CARD_EVENT or\
                chatroom_instance.type == card_types.CARD_PUBLIC_EVENT:
            schedule_chatroom_unpinning_after_event_completion(chatroom_instance)

        context = {
            'chatroom': ChatroomHelper.fetch_serialized_chatroom(self.get_member_id(), chatroom_instance,
                                                                 community_instance, user_instance.userinfo),
            'room_instance': chatroom_instance
        }

        return context

    def set_chatroom_active_or_inactive(self, req_body: dict) -> dict:
        """api to make chatroom active or in-active"""

        chatroom_id = req_body['chatroom_id']
        duration = req_body.get('duration', HOURS_24)
        status = req_body['value']

        current_time = TimeUtilities.current_time_in_sec()

        updated_time = (current_time + int(duration)) if status else (current_time - HOURS_24)

        state_filter = collabcardState.objects.filter(card=chatroom_id, user=self.get_member_id())

        if state_filter.exists():
            update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                           {'card': chatroom_id, 'user': self.get_member_id()},
                                           {'expiry_time': updated_time, 'manual_set_active': updated_time})
        else:
            error = f"Chatroom state does not exist for this user {self.get_member_id()} in chatroom {chatroom_id}"
            error_logger.error(f"set_chatroom_active_or_inactive - {error}")

            response = {
                "success": False,
                'error_message': error
            }

            return response

        send_sync_notification.delay({'chatroom_id': chatroom_id,
                                      'member_id': self.get_member_id(),
                                      'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

        return {"success": True}

    def pin_or_unpin_chatroom(self, req_body: dict) -> dict:

        chatroom_id = self.get_chatroom_id()
        value = req_body['value']
        notify = req_body['notify']

        chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if not chatroom_instance:
            return {'error_message': "invalid chatroom id", 'success': False}

        community_instance = chatroom_instance.community

        if not ModelUtilities.is_model_filter_exists(Members, {'state': member_states.ADMIN,
                                                               'member_id': self.get_member_id(),
                                                               'community_id': community_instance}):
            return {'error_message': "You need to be promoter in order to pin unpin", 'success': False}

        pinned_status = chatroom_instance.is_pinned

        if pinned_status is value:
            return {'success': True}

        chatroom_instance.is_pinned = value

        if value:
            chatroom_instance.pinning_time = TimeUtilities.current_time_in_milliseconds()

        chatroom_instance.save()

        if notify is True and value is True:
            send_pin_chatroom_notification.delay(community_instance.id, self.get_member_id(), self.get_chatroom_id())

        return {'success': True}

    def leave_secret_chatroom(self, member_id: Union[int, str] = None) -> None:

        chatroom_instance = Collabcard.get_chatroom_with_joins_or_raise_exception(self.get_chatroom_id())

        chatroom_state = chatroom_states.REMOVED_FROM_CHATROOM
        if member_id is None:
            member_id = self.get_member_id()
            chatroom_state = chatroom_states.LEAVE_CHATROOM

        if NumberUtilities.get_integer_from_string(member_id) == chatroom_instance.user.id:
            response = {
                'success': False,
                'error_message': 'chatroom creator cannot leave chatroom'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        user_instance = ChatroomHelper.fetch_user_instance(member_id=member_id)

        member_instance = Members.objects.filter(community_id=chatroom_instance.community,
                                                 member_id=user_instance)

        if member_instance.exists():
            member_instance = member_instance[0]
            is_owner = member_instance.is_owner
            is_cm = member_instance.state == member_states.ADMIN

        else:
            response = {
                'success': False,
                'error_message': 'non member cannot leave secret chatroom or cannot be removed from secret chatroom'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        if is_cm or is_owner:
            response = {
                'success': False,
                'error_message': 'community manager or owner cannot leave secret chatroom or cannot be removed from secret chatroom'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        # removing member id from secret_chatroom_participants list
        existing_participants_list = json.loads(chatroom_instance.secret_chatroom_participants)
        existing_participants_list.remove(NumberUtilities.get_integer_from_string(member_id))

        chatroom_instance.secret_chatroom_participants = existing_participants_list

        self._save_chatroom_instance(chatroom_instance)

        filter_dict = {
            'card': chatroom_instance,
            'user': user_instance
        }

        update_dict = {
            'secret_chatroom_left': True,
            'follow_status': False,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)
        
        # deleting conversation engage for this chatroom for this user
        conversationEngage.objects.filter(card=chatroom_instance, user=user_instance).delete()

        ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user_instance,
                                     state=chatroom_state, current_user_id=self.get_member_id())

        if chatroom_state == chatroom_states.REMOVED_FROM_CHATROOM:
            send_notification_for_removed_secret_room_participant.delay(member_id, self.get_chatroom_id())

    def add_secret_chatroom_participant(self, req_body: dict) -> dict:

        secret_chatroom_participants = req_body.get('secret_chatroom_participants')

        chatroom_instance = Collabcard.get_chatroom_or_raise_exception(self.get_chatroom_id())

        existing_participants = json.loads(chatroom_instance.secret_chatroom_participants)

        final_participants_list = set(secret_chatroom_participants) | set(existing_participants)

        chatroom_instance.secret_chatroom_participants = json.dumps(list(final_participants_list))

        self._save_chatroom_instance(chatroom_instance)

        new_participants_list = set(secret_chatroom_participants) - set(existing_participants)

        new_participants = User.objects.filter(pk__in=new_participants_list)

        for user in new_participants:

            req_dict = ChatroomHelper.get_follow_user_dict(user.id, self.get_chatroom_id(),
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")
            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_SEEN)

            if user.id != NumberUtilities.get_integer_from_string(self.get_member_id()):
                ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user,
                                             state=chatroom_states.CHATROOM_ADD_PARTICIPANT,
                                             current_user_id=self.get_member_id())

            send_notification_for_new_secret_room_participant.delay(user.id, self.get_chatroom_id())

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)

        return {'success': True}


class ChatroomHelper:

    @staticmethod
    def fetch_card_instance(chatroom_id: Union[str, int]):
        return Collabcard.get_chatroom_or_None(chatroom_id=chatroom_id)

    @staticmethod
    def fetch_user_instance(member_id: Union[str, int]):
        return User.get_user_or_none(member_id)

    @staticmethod
    def fetch_serialized_community(card_instance: object, user_instance: object, current_user_id: str = None):

        context = CommunitySerializer(card_instance.community, current_user_id=current_user_id,
                                      current_user_instance=user_instance)
        return context

    @staticmethod
    def get_follow_user_dict(user_id: Union[str, int], chatroom_id: Union[str, int],
                             is_tagged: bool, status: bool, source: str):
        return {
            'member_id': user_id,
            'collabcard_id': chatroom_id,
            'status': status,
            'source': source,
            'is_tagged': is_tagged
        }

    @staticmethod
    def fetch_user_instance_or_raise_exception(user_id: Union[str, int]):
        return User.get_user_or_raise_exception(user_id)

    @staticmethod
    def fetch_user_info_instance(user_instance: User):
        return user_instance.userinfo

    @staticmethod
    def fetch_community_instance(community_id: Union[str, int]):
        return Community.get_community_or_raise_exception(community_id=community_id)

    @staticmethod
    def fetch_serialized_chatroom(member_id: Union[str, int], chatroom_instance: Collabcard,
                                  community_instance: Community, user_info_instance: object):
        chatroom = CollabcardSerializer(chatroom_instance,
                                        member_id,
                                        community_instance,
                                        current_user_id=member_id)

        chatroom['date'] = datetime.today().strftime('%d-%m-%Y')
        chatroom['member'] = ChatroomHelper.fetch_serialized_user_info(user_info_instance)
        return chatroom

    @staticmethod
    def fetch_serialized_user_info(user_info_instance: object):
        return UserinfoSerializer(user_info_instance)

    @staticmethod
    def check_user_auto_approve_right(user: User, community: Community) -> bool:
        return userMemberRights.check_member_auto_approve_right(user=user,
                                                                community=community)

    @staticmethod
    def fetch_member_state_in_community(community: Community, user: User) -> int:
        return Members.get_community_member_state(community,
                                                  user)

    @staticmethod
    def is_user_community_member_or_raise_exception(community: Community, user: User) -> bool:
        is_member = Members.is_community_member(community=community,
                                                member=user)
        if not is_member:
            response = {'success': False,
                        'error_message': "You cannot create a chatroom"
                        }
            raise CustomException(response, status_code=status_codes.HTTP_401_UNAUTHORIZED)
        return is_member

    @staticmethod
    def update_time_for_community_members_on_card_creation(community: Community) -> None:
        Collabcard.update_time_for_community_members(community)

    @staticmethod
    def create_answer(chatroom_instance, user_instance, state, answer=None, current_user_id=None):
        create_chatroom(chatroom_instance, user_instance, state,
                        current_user_id=current_user_id, answer=answer)
