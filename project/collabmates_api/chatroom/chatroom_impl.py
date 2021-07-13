import json
from datetime import datetime
import time
from typing import Union
from rest_framework import status as status_codes
from django.contrib.auth.models import User
from django.db.models import Q, Max
from celery import shared_task

from django.conf import settings
from .constants import CHATROOM_EXPIRE_DURATION, INTRO_PLACEHOLDER_TEXT, INTRO_PLACEHOLDER_USER_ROUTE
from ..chatroom.chatroom_manager import ChatroomManager
from ..member_community.member_community_impl import MemberCommunityImpl, MemberCommunityHelper
from ..rest_api import GetChatroomInstanceSerializer
from ..serializers import (get_preview_for_url, get_chatroom_instance, CommunitySerializer,
                           CollabcardSerializer, UserinfoSerializer)
from ..sync.model_update import update_models_for_syncing_apis
from ..upload_attachments import get_user_image_based_on_community, save_chatroom_attachments
from ..views import (adding_guest_in_chatroom, get_chatroom_actions, get_expiry_time_of_chatroom,
                     create_chatroom_state_instance, get_icons_states_of_chatroom_version_1,
                     save_the_latest_conversation, collabcard_follow_internal,
                     send_chatroom_creation_notifications_and_mails, update_seen_status_for_new_user_in_chatroom,
                     create_chatroom, get_latest_conversation_members, )
from ..tasks import update_pending_chatroom_count_for_promoters
from ..notification import (get_tagged_members_list, send_notification_to_event_co_hosts,
                            send_ice_breaker_notification, send_sync_notification,
                            send_pin_chatroom_notification, send_notification_for_new_secret_room_participant,
                            send_notification_for_removed_secret_room_participant,
                            send_notification_for_auto_follow_chatroom_for_all_members)

from ..search.sync import ElasticSearchSync

from togther.models import (Members, Collabcard, card_answers, Community,
                            collabcardState, conversationEngage, userMemberRights,
                            CollabcardPolls, draftChatroom, draftPolls, ModelUtilities, Userinfo)
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.states import member_states, card_types, collabcard_states, SyncNotificationTypes, \
    SyncTypes, member_rights, conversation_states

from utility.utils import decode_meta_from_url, check_notification_flag
from utility.internal_link_preview_utilities import PreviewUtilities
from utility.celery_tasks import set_chatroom_state_for_all_members_on_card_creation, get_chatroom_user_images_for_web, \
    schedule_chatroom_unpinning_after_event_completion, update_last_unseen_in_engage, \
    update_preview_of_chatroom_in_cache
from utility.firebase import update_last_answer_id
from utility.exception_utilities import (CustomException)
from utility.time_utilities import TimeUtilities
from utility.number_utilities import NumberUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class ChatroomImpl(ChatroomManager):
    member_id = None
    chatroom_id = None
    source_id = None
    aj = None
    device_id = None
    request_platform = None

    def __init__(self, member_id: str, chatroom_id: str = None,
                 source_id: str = None, aj: str = None,
                 device_id: str = None, request_platform: str = None):
        self.member_id = member_id
        self.chatroom_id = chatroom_id
        self.source_id = source_id
        self.aj = aj
        self.device_id = device_id
        self.request_platform = request_platform

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
        chatroom_obj = get_chatroom_instance(card_instance, self.get_member_id(), return_topic=True)

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
                                                           state=conversation_states.ANSWER
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

        card_content['device_id'] = self.device_id
        card_content['platform'] = self.request_platform

    @staticmethod
    def fill_pinned_information(card_content):

        if card_content['type'] == card_types.CARD_PURPOSE or \
                card_content['type'] == card_types.CARD_MASTER_INTRO or \
                card_content['type'] == card_types.CARD_EVENT or \
                card_content['type'] == card_types.CARD_PUBLIC_EVENT:
            card_content['is_pinned'] = True
            card_content['pinning_time'] = TimeUtilities.current_time_in_milliseconds()

    def _fill_secret_room_details(self, card_content, req_body, community):

        card_content['is_secret'] = req_body.get("is_secret", False)

        if card_content['is_secret'] and \
                req_body.get("secret_chatroom_participants", None):
            card_content['is_secret'] = True

            secret_chatroom_participants = req_body.get("secret_chatroom_participants", None)

            if secret_chatroom_participants:
                member_id = NumberUtilities.get_integer_from_string(self.get_member_id())

                if member_id not in secret_chatroom_participants:
                    secret_chatroom_participants.append(member_id)

                card_content['secret_chatroom_participants'] = json.dumps(secret_chatroom_participants)

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

    def _fill_chatroom_header(self, card_content, req_body, chatroom_type, chatroom_name, decoded_chatroom_title=""):

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

            # creating default conversation for chatroom creation
            create_chatroom(card_instance=chatroom_instance, user_instance=user_instance,
                            state=conversation_states.CONVERSATION_HEADER, current_user_id=self.get_member_id())

            send_ice_breaker_notification.delay(community_id, time.time(), day=0)

            # batch update for already existing users and saving their unseen count
            if not chatroom_instance.is_secret:
                ChatroomHelper.run_async_tasks_related_to_member_for_chatroom_posting.delay(chatroom_instance.id,
                                                                                            user_instance.id,
                                                                                            community_instance.id)
            else:
                update_last_answer_id(chatroom_instance.id, "")

        else:
            update_pending_chatroom_count_for_promoters.delay(community_id)

    def _latest_conversations_user_data(self):

        conversation_users_meta = get_chatroom_user_images_for_web(self.get_chatroom_id())
        conversation_users = get_latest_conversation_members(conversation_users_meta['last_conversation_member'],
                                                             conversation_users_meta['second_last_conversation_member'],
                                                             conversation_users_meta['last_conversation_user'],
                                                             conversation_users_meta['second_last_conversation_user'])

        return conversation_users

    @staticmethod
    def compute_tagging_list_of_community_members(community_instance):

        member_list = MemberCommunityImpl.fetch_list_of_community_members(community_instance)
        member_data = MemberCommunityImpl.fetch_members_based_on_user_list(member_list, community_instance)
        tagging_list = MemberCommunityHelper.extract_member_tagging_data(member_data)

        return tagging_list

    @staticmethod
    def compute_tagging_list_of_guest_members(chatroom_instance):

        guest_user_list = list(collabcardState.objects.filter(is_guest=True,
                                                              card=chatroom_instance).values_list('user', flat=True))
        tag_list = []

        userinfo_filter = Userinfo.objects.filter(user_id__in=guest_user_list)

        for data in userinfo_filter:
            temp = dict()
            temp['id'] = data.user_id_id
            temp['name'] = data.name
            temp['image_url'] = data.image_link if data.image_link else ""

            tag_list.append(temp)

        return tag_list

    @staticmethod
    def compute_tagging_list_for_secret_participants(chatroom_instance, community_instance):

        try:
            member_list = json.loads(chatroom_instance.secret_chatroom_participants)

        except Exception as e:
            error_logger.error(e)
            member_list = []

        member_data = MemberCommunityImpl.fetch_members_based_on_user_list(member_list, community_instance)
        tagging_list = MemberCommunityHelper.extract_member_tagging_data(member_data)

        return tagging_list

    @staticmethod
    def compute_placeholder_for_intro_room(card_instance, user_instance):

        if not user_instance:
            return ""

        placeholder = ""

        if card_instance.type == card_types.CARD_INTRO \
                and card_instance.user_id != user_instance.id:
            last_seen_conversation_filter = ModelUtilities.get_model_filter(collabcardState,
                                                                            {'card': card_instance,
                                                                             'user': user_instance}
                                                                            ).only('last_seen_conversation')
            if last_seen_conversation_filter and \
                    not last_seen_conversation_filter[0].last_seen_conversation:
                card_creator_userinfo_instance = card_instance.user.userinfo
                community_instance = card_instance.community
                placeholder = ChatroomHelper.create_placeholder_for_introduction_card(community_instance,
                                                                                      card_creator_userinfo_instance)

        return placeholder

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

        can_access_secret_chatroom = False

        if self.get_member_id() is not None:
            member_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            if card_instance.is_secret:

                try:
                    can_access_secret_chatroom = member_id in json.loads(card_instance.secret_chatroom_participants)

                    if not can_access_secret_chatroom:
                        can_access_secret_chatroom = ModelUtilities.is_model_filter_exists(collabcardState,
                                                                                           {'card': card_instance,
                                                                                            'user': self.get_member_id(),
                                                                                            'remove': None,
                                                                                            'secret_chatroom_left': False})

                except Exception as e:
                    error_logger.error(f"fetch_chatroom - {e.args}")

                    response = {
                        'success': False,
                        'error_message': f"{e.args}"
                    }
                    raise CustomException(response, status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)

            elif card_instance.attachment_count > 0 and \
                    card_instance.attachments_uploaded is False:
                can_access_secret_chatroom = not ChatroomHelper.has_attachments_uploaded(card_instance,
                                                                                         member_id,
                                                                                         self.device_id)

        chatroom_obj['can_access_secret_chatroom'] = can_access_secret_chatroom
        placeholder = self.compute_placeholder_for_intro_room(card_instance, user_instance)

        if placeholder:
            chatroom_obj['placeholder'] = placeholder

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

        if card_content['is_secret'] and \
                not ChatroomHelper.check_user_secret_room_creation_right(user_instance, community_instance):
            response = {
                "success": False,
                "error_message": "Only CM or member with secret chatroom creation right can create secret chatroom"
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

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
            room_creator_id = NumberUtilities.get_integer_from_string(self.get_member_id())

            ChatroomHelper.make_secret_chatroom_relation_for_community_members.delay(participants_list,
                                                                                     self.get_chatroom_id(),
                                                                                     community_id,
                                                                                     room_creator_id=room_creator_id)

        self._send_follow_notifications_to_event_co_hosts(req_body, chatroom_name,
                                                          user_instance.userinfo.name)

        self._send_additional_notifications_and_tasks_after_room_creation(user_instance, community_instance,
                                                                          chatroom_instance, req_body,
                                                                          is_intro_card, user_has_auto_approve_right,
                                                                          community_id)

        ChatroomHelper.update_time_for_community_members_on_card_creation(community_instance)

        send_sync_notification.delay({'sync_notification_type': SyncNotificationTypes.ALL_MEMBERS.value,
                                      'community_id': community_id})

        if chatroom_instance.type == card_types.CARD_EVENT or \
                chatroom_instance.type == card_types.CARD_PUBLIC_EVENT:
            schedule_chatroom_unpinning_after_event_completion(chatroom_instance)

        context = {
            'success': True,
            'chatroom': ChatroomHelper.fetch_serialized_chatroom(self.get_member_id(), chatroom_instance,
                                                                 community_instance, user_instance.userinfo),
            'chatroom_local': ChatroomHelper.fetch_serialized_chtroom_for_local_db_sycing(self.get_member_id(),
                                                                                          chatroom_instance)
        }

        return context

    def set_chatroom_active_or_inactive(self, req_body: dict) -> dict:
        """api to make chatroom active or in-active"""

        chatroom_id = req_body['chatroom_id']
        duration = req_body.get('duration', CHATROOM_EXPIRE_DURATION)
        status = req_body['value']

        current_time = TimeUtilities.current_time_in_sec()

        updated_time = (current_time + int(duration)) if status else (current_time - CHATROOM_EXPIRE_DURATION)

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

        if chatroom_instance.is_secret:
            return {'error_message': "secret chatroom cannot be pinned", 'success': False}

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

        chatroom_state = conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM
        if member_id is None:
            member_id = self.get_member_id()
            chatroom_state = conversation_states.CONVERSATION_LEAVE_CHATROOM

        user_instance = ChatroomHelper.fetch_user_instance(member_id=member_id)

        # removing member id from secret_chatroom_participants list
        existing_participants_list = json.loads(chatroom_instance.secret_chatroom_participants)
        member_id = NumberUtilities.get_integer_from_string(member_id)

        if member_id in existing_participants_list:
            existing_participants_list.remove(member_id)
        else:
            response = {
                'success': False,
                'error_message': f'member with id {member_id} is not a participant of this secret chatroom'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        chatroom_instance.secret_chatroom_participants = existing_participants_list
        self._save_chatroom_instance(chatroom_instance)

        member_state = Members.get_community_member_state(chatroom_instance.community_id, user_instance)
        secret_chatroom_left = True

        if member_state == member_states.ADMIN:
            secret_chatroom_left = False

        filter_dict = {
            'card': chatroom_instance,
            'user': user_instance
        }

        update_dict = {
            'secret_chatroom_left': secret_chatroom_left,
            'follow_status': False,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
        }

        update_dict = {
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        # deleting conversation engage for this chatroom for this user
        conversationEngage.objects.filter(card=chatroom_instance, user=user_instance).delete()

        ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user_instance,
                                     state=chatroom_state, current_user_id=self.get_member_id())

        update_last_unseen_in_engage(user=member_id, community=chatroom_instance.community_id)

        if secret_chatroom_left:
            ElasticSearchSync.delete_chatroom_for_user.delay(chatroom_instance.id, user_instance.id)

        if chatroom_state == conversation_states.CONVERSATION_REMOVED_FROM_CHATROOM:
            send_notification_for_removed_secret_room_participant.delay(member_id, self.get_chatroom_id())

    def add_secret_chatroom_participant(self, req_body: dict) -> dict:

        secret_chatroom_participants = req_body.get('secret_chatroom_participants', None)

        if secret_chatroom_participants is None:
            response = {
                'success': False,
                'error_message': 'send secret_chatroom_participants in body'
            }
            raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

        if len(secret_chatroom_participants) <= 0:
            return {'success': True}

        chatroom_instance = Collabcard.get_chatroom_or_raise_exception(self.get_chatroom_id())

        existing_participants = json.loads(chatroom_instance.secret_chatroom_participants)

        final_participants_list = set(secret_chatroom_participants) | set(existing_participants)

        chatroom_instance.secret_chatroom_participants = json.dumps(list(final_participants_list))

        self._save_chatroom_instance(chatroom_instance)

        new_participants_list = list(set(secret_chatroom_participants) - set(existing_participants))

        if len(new_participants_list) <= 0:
            return {'success': True}

        # updating all secret chatroom participants
        filter_dict = {
            'card': chatroom_instance,
            'user__id__in': new_participants_list
        }

        update_dict = {
            'secret_chatroom_left': False,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       filter_dict=filter_dict,
                                       update_dict=update_dict)

        ChatroomHelper.add_new_secret_chatroom_participants.delay(new_participants_list,
                                                                  self.get_chatroom_id(),
                                                                  self.get_member_id())

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

    def get_tagging_list(self) -> dict:

        chatroom_instance = Collabcard.get_chatroom_or_None(self.get_chatroom_id())

        if not chatroom_instance:
            return {'error_message': "invalid chatroom id"}

        userinfo_instance = Userinfo.get_userinfo_or_None(self.get_member_id())

        if not userinfo_instance:
            return {'error_message': "invalid user id"}

        community_instance = chatroom_instance.community

        if chatroom_instance.is_secret:
            participant_list = self.compute_tagging_list_for_secret_participants(chatroom_instance, community_instance)

            return {'participants': participant_list, 'members': []}

        members = self.compute_tagging_list_of_community_members(community_instance)
        participant_list = self.compute_tagging_list_of_guest_members(chatroom_instance)

        return {'members': members, 'participants': participant_list}

    def create_introduction_card_in_community(self, community_instance, user_instance, req_body, member_state,
                                              master_intro_instance):

        card_content = {}
        chatroom_name = req_body.get('title')
        chatroom_type = card_types.CARD_INTRO

        self._fill_chatroom_basic_info(card_content, chatroom_name,
                                       community_instance, user_instance, chatroom_type)

        self._fill_chatroom_attachment_count(card_content, req_body)
        self._fill_chatroom_epoch_time(card_content, req_body)

        self._fill_chatroom_event_details(card_content=card_content, req_body=req_body)
        self._fill_chatroom_poll_details(card_content, req_body)
        self._fill_chatroom_header(card_content, req_body, chatroom_type, chatroom_name)

        self._add_og_tags(req_body=req_body, card_content=card_content)
        self._fill_secret_room_details(card_content, req_body, community_instance)

        card_content['member_state'] = member_state
        chatroom_instance = self._create_chatroom_with_contents(card_content=card_content)

        self.add_files_for_introduction_card(chatroom_instance, user_instance, community_instance)
        ChatroomHelper.update_time_for_community_members_on_card_creation(community_instance)
        ChatroomHelper.auto_follow_chatroom(chatroom_instance, user_instance,
                                            community_instance, member_state=member_state)
        create_chatroom(card_instance=chatroom_instance, user_instance=user_instance,
                        state=conversation_states.CONVERSATION_HEADER, current_user_id=self.get_member_id())

        # async task for posting introduction room
        ChatroomHelper.update_old_chatrooms_relation_and_post_introduction_conversation.delay(master_intro_instance.id,
                                                                                              user_instance.id,
                                                                                              chatroom_instance.id,
                                                                                              community_instance.id,
                                                                                              member_state)

        ChatroomHelper.run_async_tasks_related_to_member_for_chatroom_posting.delay(chatroom_instance.id,
                                                                                    user_instance.id,
                                                                                    community_instance.id,
                                                                                    is_intro_chatroom=True)
        send_ice_breaker_notification.delay(community_instance.id, TimeUtilities.current_time_in_sec(), day=0)

        return chatroom_instance

    def add_files_for_introduction_card(self, card_instance, user_instance, community_instance):

        image_url = get_user_image_based_on_community(user_instance.id, community_instance.id)

        if card_instance and image_url:
            save_chatroom_attachments(card_instance, body={
                'url': image_url,
                'type': "image",
                'index': 1
            })
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'has_files': True, 'attachment_count': 1,
                                         'attachments_uploaded': True})

    def follow_chatroom_automatically_for_all_members_of_community(self, member_id, chatroom_id) -> dict:
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return {'success': False, 'error_message': "invalid chatroom id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        community_id = chatroom_instance.community_id

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_id,
                                                                  'member_id': user_instance})

        user_list = []
        bulk_update_list = []

        if member_filter:
            member_instance = member_filter[0]
            is_cm = member_instance.state == member_states.ADMIN

            if is_cm:

                if not chatroom_instance.auto_follow_done:
                    community_members = list(Members.get_members_of_community(community_id).values_list('member_id',
                                                                                                        flat=True))

                    chatroom_state_dict = ChatroomHelper.pre_compute_chatroom_state_of_members(chatroom_instance,
                                                                                               community_members,
                                                                                               follow_status=False)

                    for community_member in community_members:
                        if chatroom_state_dict.get(community_member) is not None:
                            user_list.append(community_member)
                            collabcard_state = chatroom_state_dict.get(community_member)
                            collabcard_state.follow_status = True
                            collabcard_state.updated_at = TimeUtilities.current_time_in_sec()
                            bulk_update_list.append(collabcard_state)

                    ModelUtilities.bulk_update_instances(collabcardState, bulk_update_list,
                                                         ['follow_status', 'updated_at'])

                    ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list \
                        .delay(chatroom_id, user_list)

                    chatroom_instance.auto_follow_done = True
                    chatroom_instance.save()


                    #removing tag status for tagged users
                    ModelUtilities.model_update(collabcardState,
                                                {'card': chatroom_instance,
                                                 'is_tagged': True},
                                                {'is_tagged': False,
                                                 'updated_at': TimeUtilities.current_time_in_sec()})

                    from collabmates_api.conversation.conversation_impl import ConversationHelper
                    ConversationHelper.create_conversation_state(chatroom_instance, user_instance,
                                                                 conversation_states.CONVERSATION_ADD_ALL_MEMBERS)

                    if len(user_list) > 0:
                        send_notification_for_auto_follow_chatroom_for_all_members.delay(chatroom_id, user_instance.id,
                                                                                         user_list)

                    return {'success': True}

                else:
                    response = {
                        'success': False,
                        'error_message': 'All members of this community are already added to this chat room'
                    }
                    raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

            else:
                response = {
                    'success': False,
                    'error_message': 'You need to be Owner/CM of the community to enable auto follow'
                }
                raise CustomException(response, status_code=status_codes.HTTP_403_FORBIDDEN)

    def edit_chatroom(self, req_body) -> dict:

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('chatroom_id'))

        if not card_instance:
            return {'success': False, 'error_message': "Invalid chatroom id"}

        text = req_body.get('text')

        if not text:
            return {'success': False, 'error_message': "Empty text for edit"}

        if card_instance.user_id != user_instance.id:
            return {'success': False, 'error_message': "Only chat room creator can edit"}

        ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, {'title': text, 'is_edited': True})

        ChatroomHelper.run_async_tasks_related_to_chatroom_edit.delay(card_instance.id, text)

        return {'success': True}

    def fetch_participants_of_secret_chatroom(self):

        card_instance = Collabcard.get_chatroom_or_None(self.get_chatroom_id())

        if not card_instance:
            return {'error_message': "invalid chatroom id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'error_message': "invalid user id"}

        community_instance = card_instance.community
        can_edit_participant = False

        if card_instance.is_secret:

            if card_instance.user_id == user_instance.id:
                can_edit_participant = True
            else:
                member_filter = ModelUtilities.get_model_filter(Members,
                                                                {'community_id': community_instance,
                                                                 'member_id': user_instance})
                if member_filter:
                    member_state = member_filter[0].state

                    if member_state == member_states.ADMIN:
                        can_edit_participant = ModelUtilities.is_model_filter_exists(collabcardState, {
                            'card': card_instance,
                            'follow_status': True,
                            'remove': None,
                            'user': user_instance
                        })

            participant_list = self.compute_tagging_list_for_secret_participants(card_instance, community_instance)

            return {'participants': participant_list, 'can_edit_participant': can_edit_participant}

        return {'error_message': "Chatroom is not secret"}


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
    def fetch_serialized_chtroom_for_local_db_sycing(member_id, chatroom_instance):
        member_data = {'member_id': member_id, 'current_user_id': member_id, 'state_instance': None}
        chatroom_obj = GetChatroomInstanceSerializer(chatroom_instance, context=member_data, many=False)

        return chatroom_obj.data

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

    @staticmethod
    @shared_task
    def make_secret_chatroom_relation_for_community_members(user_list, chatroom_id, community_id,
                                                            room_creator_id):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not card_instance:
            return

        member_dict = ChatroomHelper.pre_compute_existence_of_members_in_chatroom_state(card_instance,
                                                                                        user_list)
        user_filter = ModelUtilities.get_model_filter(User,
                                                      {'id__in': user_list})
        bulk_create_list = []

        for user_instance in user_filter:

            if member_dict.get(user_instance.id) is False:

                expire_at = TimeUtilities.current_time_in_sec() + CHATROOM_EXPIRE_DURATION \
                    if user_instance.id == room_creator_id else None

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create \
                    (card_instance,
                     user_instance,
                     state=0,
                     follow_status=True,
                     community_instance=community_instance,
                     external_seen=user_instance.id == room_creator_id,
                     expire_at=expire_at)

                if instance:
                    bulk_create_list.append(instance)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list(
            card_instance.id, user_list)

        for user_id in user_list:
            update_last_unseen_in_engage(user=user_id, community=community_instance.id)

        ChatroomHelper.update_secret_chatroom_for_community_promoters(card_instance, community_instance, member_dict)
        ElasticSearchSync.update_chatroom(card_instance.id)

    @staticmethod
    def update_secret_chatroom_for_community_promoters(card_instance, community_instance, member_dict):

        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'community_id': community_instance,
                                                         'state': member_states.ADMIN}).select_related('member_id')
        bulk_create_list = []
        promoter_list = []
        for data in member_filter:

            if data.member_id_id not in member_dict:
                user_instance = data.member_id
                instance = collabcardState.create_chatroom_state_instances_for_bulk_create \
                    (card_instance,
                     user_instance,
                     follow_status=False,
                     state=0,
                     community_instance=community_instance,
                     external_seen=False,
                     expire_at=None)

                if instance:
                    bulk_create_list.append(instance)

                promoter_list.append(data.member_id_id)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)

        for user_id in promoter_list:
            update_last_unseen_in_engage(user=user_id, community=community_instance.id)

    @staticmethod
    @shared_task
    def add_new_secret_chatroom_participants(participants_list, chatroom_id, current_user_id):

        chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if chatroom_instance is None:
            return

        new_participants = User.objects.filter(pk__in=participants_list)

        for user in new_participants:

            req_dict = ChatroomHelper.get_follow_user_dict(user.id, chatroom_instance.id,
                                                           is_tagged=False, status=True,
                                                           source="create_chatroom")

            collabcard_follow_internal(req_dict, state=collabcard_states.COLLABCARD_STATE_UNSEEN,
                                       external_seen=False,
                                       set_expiry_time_none=True)

            if user.id != NumberUtilities.get_integer_from_string(current_user_id):
                ChatroomHelper.create_answer(chatroom_instance=chatroom_instance, user_instance=user,
                                             state=conversation_states.CONVERSATION_ADD_PARTICIPANT,
                                             current_user_id=current_user_id)

            update_last_unseen_in_engage(user=user.id, community=chatroom_instance.community_id)
            # update elastic search
            ElasticSearchSync.update_chatroom_for_user.delay(chatroom_instance.id, user.id)

            send_notification_for_new_secret_room_participant(user.id, chatroom_instance.id)

    @staticmethod
    def get_chatroom_expiry_time(chatroom_state_instance):

        expiry_time = TimeUtilities.current_time_in_sec() + CHATROOM_EXPIRE_DURATION

        if chatroom_state_instance:

            if chatroom_state_instance.expiry_time and chatroom_state_instance.expiry_time > expiry_time:
                expiry_time = chatroom_state_instance.expiry_time

            if chatroom_state_instance.manual_set_active and \
                    chatroom_state_instance.manual_set_active > expiry_time:
                expiry_time = chatroom_state_instance.manual_set_active

        return expiry_time

    @staticmethod
    def has_attachments_uploaded(chatroom, user_id, device_id=''):
        if chatroom.attachment_count > 0 and \
                chatroom.attachments_uploaded is False and \
                (user_id != chatroom.user_id or
                 device_id != chatroom.device_id):
            return True

        return False

    @staticmethod
    def create_placeholder_for_introduction_card(community_instance, card_creator_userinfo_instance):
        """function to create introduction card placeholder"""

        placeholder = INTRO_PLACEHOLDER_TEXT % community_instance.name
        user_name = card_creator_userinfo_instance.name
        user_route = INTRO_PLACEHOLDER_USER_ROUTE % str(card_creator_userinfo_instance.user_id_id)
        user_name = "<<" + user_name + "|" + user_route + ">>"
        placeholder = placeholder + user_name

        return placeholder

    @staticmethod
    def create_card_engagement_for_home_screen(card_instance, user_instance, community_instance, member_state=0):

        instance_list = ModelUtilities.get_model_filter(conversationEngage,
                                                        {'card': card_instance,
                                                         'user': user_instance})

        rights_list = None

        if member_state == member_states.ADMIN:
            rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)
        elif member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
            rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)

        if not instance_list:
            conversationEngage.create_instance({'card_instance': card_instance,
                                                'user_instance': user_instance,
                                                'community_instance': community_instance,
                                                'rights_list': rights_list})

        else:
            instance = instance_list[0]
            ModelUtilities.model_update(conversationEngage, {'id': instance.id},
                                        {'last_conversation': None,
                                         'updated_at': TimeUtilities.current_time_in_sec()})

        ChatroomHelper.update_rights_list_in_conversationEngage(user_instance, community_instance)

    @staticmethod
    def update_rights_list_in_conversationEngage(user_instance, community_instance):
        rights_list = list(userMemberRights.objects.filter(user=user_instance,
                                                           community=community_instance).values_list("right__state",
                                                                                                     flat=True))
        rights_list = json.dumps(rights_list)

        ModelUtilities.model_update(conversationEngage, {'user': user_instance,
                                                         'community': community_instance},
                                    {'rights_list': rights_list})

    @staticmethod
    def auto_follow_chatroom(card_instance, user_instance, community_instance, status=True, func_dict=None,
                             member_state=0):

        if func_dict is None:
            func_dict = {}

        is_guest = False
        is_tagged = False
        ref_instance = None
        mute_status = False

        if func_dict.get('is_guest') and func_dict.get('source_id'):
            is_guest = func_dict['is_guest']
            source_id = func_dict['source_id']
            ref_instance = ModelUtilities.get_model_instance_or_none(User, source_id)

            if not ref_instance:
                return

        elif func_dict.get('is_tagged'):
            is_tagged = True
            mute_status = True

        chatroom_state_instance = None

        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': card_instance,
                                                                                    'user': user_instance})

        if not collabcard_state_filter:

            expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
            card_state_instance = collabcardState.create_chatroom_state_instance(card_instance, user_instance,
                                                                                 state=collabcard_states.COLLABCARD_STATE_SEEN,
                                                                                 expire_at=expiry_time,
                                                                                 is_guest=is_guest,
                                                                                 source=ref_instance,
                                                                                 follow_status=status,
                                                                                 mute_status=mute_status,
                                                                                 is_tagged=is_tagged
                                                                                 )
        else:
            card_state_instance = collabcard_state_filter[0]
            expiry_time = ChatroomHelper.get_chatroom_expiry_time(chatroom_state_instance)
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.expiry_time = expiry_time
            card_state_instance.follow_status = status
            card_state_instance.mute_status = mute_status
            card_state_instance.is_guest = is_guest
            card_state_instance.is_tagged = is_tagged
            card_state_instance.save()

        if status:
            ChatroomHelper.create_card_engagement_for_home_screen(card_instance, user_instance, community_instance,
                                                                  member_state=member_state)

        # local imports for conversation helper
        from ..conversation.conversation_impl import ConversationHelper

        ConversationHelper.update_homescreen_meta_on_chatroom_follow(community_instance, card_instance,
                                                                     card_state_instance, user_instance)

        ElasticSearchSync.update_chatroom_for_user.delay(card_instance.id, user_instance.id)

    @staticmethod
    def pre_compute_existance_in_chatroom_state(chatroom_list, user_instance):

        state_filter = collabcardState.objects.filter(card__in=chatroom_list, user=user_instance)

        chatroom_state_dict = {chatroom_id: False for chatroom_id in chatroom_list}

        for data in state_filter:
            card_id = data.card_id

            if chatroom_state_dict.get(card_id) is False:
                chatroom_state_dict[card_id] = True

        return chatroom_state_dict

    @staticmethod
    def pre_compute_last_conversation_in_chatroom(chatroom_list):

        conversation_filter = card_answers.objects.filter(card__in=chatroom_list,
                                                          state=conversation_states.ANSWER).values('card'). \
            annotate(created_at=Max('created_at'))

        chatroom_set = set(chatroom_list)
        conversation_created_at = {}

        for data in conversation_filter:

            if data['card'] in chatroom_set:
                created_at = data['created_at']

                if TimeUtilities.is_epoch_in_milliseconds(created_at):
                    created_at = TimeUtilities.convert_milliseconds_to_sec(created_at)

                conversation_created_at['created_at'] = created_at

        return conversation_created_at

    @staticmethod
    def update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance):
        chatroom_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                       'is_pending': False,
                                                                       'is_deleted': False,
                                                                       'is_secret': False})

        chatroom_list = list(chatroom_filter.values_list('id', flat=True))

        chatroom_state_dict = ChatroomHelper.pre_compute_existance_in_chatroom_state(chatroom_list, user_instance)
        conversation_created_at = ChatroomHelper.pre_compute_last_conversation_in_chatroom(chatroom_list)
        bulk_create_list = []
        auto_follow_chatroom_list = []

        for card_instance in chatroom_filter:

            if chatroom_state_dict.get(card_instance.id) is False:
                expire_at = conversation_created_at.get(card_instance.id, card_instance.date_epoch) + \
                            CHATROOM_EXPIRE_DURATION

                if card_instance.auto_follow_done:
                    auto_follow_chatroom_list.append(card_instance.id)

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create(card_instance,
                                                                                           user_instance,
                                                                                           follow_status=card_instance.auto_follow_done,
                                                                                           expire_at=expire_at,
                                                                                           community_instance=community_instance)
                if instance:
                    bulk_create_list.append(instance)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
        ChatroomHelper.create_card_engagements_for_home_screen_for_auto_follow_all_members_with_chatroom_list(
            auto_follow_chatroom_list, user_instance.id, community_instance.id, member_state=member_states.MEMBER)

    @staticmethod
    def pre_compute_existence_of_members_in_chatroom_state(card_instance, member_list):
        state_filter = collabcardState.objects.filter(card=card_instance, user__in=member_list)

        member_dict = {user_id: False for user_id in member_list}

        for data in state_filter:
            user_id = data.user_id

            if member_dict.get(user_id) is False:
                member_dict[user_id] = True

        return member_dict

    @staticmethod
    def set_state_for_all_chatroom_members_in_community(card_instance, community_instance):

        member_filter = Members.get_members_of_community(community_instance).select_related('member_id')
        member_list = list(member_filter.values_list('member_id_id', flat=True))

        member_dict = ChatroomHelper.pre_compute_existence_of_members_in_chatroom_state(card_instance, member_list)
        bulk_create_list = []

        for data in member_filter:
            user_instance = data.member_id

            if member_dict.get(user_instance.id) is False:

                instance = collabcardState.create_chatroom_state_instances_for_bulk_create(card_instance,
                                                                                           user_instance,
                                                                                           follow_status=card_instance.auto_follow_done,
                                                                                           community_instance=community_instance)
                if instance:
                    bulk_create_list.append(instance)

        ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)

    @staticmethod
    def update_unseen_count_for_homescreen_communitites(card_instance, community_instance):
        # updating last unseen chatrooms for home screen
        member_filter = Members.get_members_of_community(community_instance)

        for data in member_filter:
            user_instance = data.member_id

            if card_instance.attachment_count != 0 and card_instance.attachments_uploaded is False:
                continue

            update_last_unseen_in_engage(user=user_instance.id, community=community_instance.id, is_seen=True)

    @staticmethod
    @shared_task
    def run_async_tasks_related_to_member_for_chatroom_posting(card_id, user_id, community_id,
                                                               is_intro_chatroom=False):

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not card_instance \
                or not user_instance \
                or not community_instance:
            return

        ChatroomHelper.set_state_for_all_chatroom_members_in_community(card_instance, community_instance)
        ChatroomHelper.update_unseen_count_for_homescreen_communitites(card_instance, community_instance)
        update_last_answer_id(card_instance.id, "")

        if is_intro_chatroom:
            ElasticSearchSync.update_all_community_chatrooms_for_user(community_instance.id, user_instance.id)

        ElasticSearchSync.update_chatroom(card_instance.id)

    @staticmethod
    @shared_task
    def update_old_chatrooms_relation_and_post_introduction_conversation(master_intro_id, user_id, card_id,
                                                                         community_id, member_state):

        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        master_intro_instance = ModelUtilities.get_model_instance_or_none(Collabcard, master_intro_id)

        ChatroomHelper.update_seen_status_for_older_chatrooms_for_new_member(community_instance, user_instance)

        preview_url = settings.URL + "/collabcard/" + str(card_instance.id)
        conversation_context = {'answer': card_instance.title, 'card': master_intro_instance, 'user': user_instance,
                                'community': community_instance, 'has_files': False, 'attachment_count': 0,
                                'attachments_uploaded': False, 'api_version': 1, 'preview_chatroom': card_instance,
                                'preview_community': community_instance, 'internal_link': preview_url,
                                'preview_type': "chatroom"}

        answer_instance = card_answers(**conversation_context)
        answer_instance.save()
        ChatroomHelper.auto_follow_chatroom(master_intro_instance, user_instance, community_instance,
                                            member_state=member_state)

        # local imports for conversation helper
        from ..conversation.conversation_impl import ConversationHelper
        ConversationHelper.update_the_activity_time_for_new_conversation_creation(master_intro_instance.id,
                                                                                  user_instance.id)

        ConversationHelper.update_homescreen_meta_on_conversation_creation(community_instance,
                                                                           master_intro_instance,
                                                                           answer_instance)

        update_preview_of_chatroom_in_cache({'chatroom_id': card_instance.id,
                                             'preview_url': preview_url,
                                             'conversation_id': answer_instance.id})
        ElasticSearchSync.update_chatroom_for_user(master_intro_instance.id, user_instance.id)

    @staticmethod
    def pre_compute_chatroom_state_of_members(card_instance, member_list, follow_status):
        state_filter = collabcardState.objects.filter(card=card_instance, user__in=member_list,
                                                      follow_status=follow_status)

        chatroom_state_dict = {user_id: None for user_id in member_list}

        for data in state_filter:
            user_id = data.user_id

            if chatroom_state_dict.get(user_id) is None:
                chatroom_state_dict[user_id] = data

        return chatroom_state_dict

    @staticmethod
    @shared_task
    def create_card_engagements_for_home_screen_for_auto_follow_all_members_with_user_list(chatroom_id, user_list):
        card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        community_instance = card_instance.community

        member_filter = Members.get_members_of_community(community_instance).select_related('member_id').filter(
            member_id__in=user_list)

        for data in member_filter:
            user_instance = data.member_id
            state = data.state
            ChatroomHelper.create_card_engagement_for_home_screen(card_instance, user_instance,
                                                                  community_instance, state)

    @staticmethod
    @shared_task
    def create_card_engagements_for_home_screen_for_auto_follow_all_members_with_chatroom_list(chatroom_ids, user_id,
                                                                                               community_id,
                                                                                               member_state):
        user_instance = ChatroomHelper.fetch_user_instance(user_id)

        if not user_instance:
            return

        community_instance = Community.get_community_or_None(community_id)

        if not community_instance:
            return

        chatroom_dict = ChatroomHelper.pre_compute_chatroom_instances_from_chatroom_list(chatroom_ids)

        for chatroom_id in chatroom_ids:

            if chatroom_dict.get(chatroom_id):
                chatroom_instance = chatroom_dict.get(chatroom_id)
                ChatroomHelper.create_card_engagement_for_home_screen(chatroom_instance, user_instance,
                                                                      community_instance,
                                                                      member_state)

    @staticmethod
    def pre_compute_chatroom_instances_from_chatroom_list(chatroom_id_list):
        card_filter = Collabcard.objects.filter(id__in=chatroom_id_list)

        chatroom_dict = {chatroom_id: None for chatroom_id in chatroom_id_list}

        for data in card_filter:
            chatroom_id = data.id

            if chatroom_dict.get(chatroom_id) is None:
                chatroom_dict[chatroom_id] = data

        return chatroom_dict

    @staticmethod
    @shared_task
    def run_async_tasks_related_to_chatroom_edit(card_id, text):

        ModelUtilities.model_update(collabcardState, {'card': card_id},
                                    {'updated_at': TimeUtilities.current_time_in_sec()})
        ElasticSearchSync.update_chatroom_title(card_id, text)

    @staticmethod
    def check_user_secret_room_creation_right(user_instance, community_instance) -> bool:

        return ModelUtilities.is_model_filter_exists(userMemberRights,
                                                     {'user': user_instance,
                                                      'community': community_instance,
                                                      'right__state': member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM})
