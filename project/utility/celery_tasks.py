from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from django.db import transaction

from collabmates_api.sync.model_update import update_models_for_syncing_apis
from external_services.webflow.webflow_impl import WebflowImpl
from project.celery import app
from utility.string_utilities import StringUtilities
from utility.api_client import ApiClient
from collabmates_api.serializers import get_user_profile, get_preview_for_url, UserinfoSerializer
from collabmates_api.static_text import CHATROOM_PREVIW_CACHE_KEY, MEMBER_LEFT_DM_CHATROOM_MESSAGE, \
    MEMBER_REMOVED_DM_CHATROOM_MESSAGE, CM_REMOVED_COMMUNITY_DM_CHATROOM_MESSAGE, \
    MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE, MEMBER_JOINING_COMMUNITY_DM_CHATROOM_MESSAGE
from collabmates_api.community.constants import *
from collabmates_api.chatroom.constants import *
from collabmates_api.upload_attachments import get_user_image_based_on_community, save_chatroom_attachments
from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.segment.segment_impl import SegmentImpl
from utility.routes import CHATROOM_LINK
from togther.models import *
import time
from django.db.models import Q, F
import json

from utility.cache_keys import CONVERSATION_POLL_OPTIONS_CONVERSATION_ID, CONVERSATION_POLL_VOTERS_CONVERSATION_ID, \
    CONVERSATION_COMMUNITY_PREVIEW, EVENT_INSTRUCTORS_CHATROOM, EVENT_HIGHLIGHTS_CHATROOM, \
    EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_FAQ_CHATROOM, EVENT_ATTENDEES_CHATROOM, EVENT_ATTENDEES_CONVERSATION, \
    COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY, \
    SUBSCRIPTION_FETCH_EVENT_PLAN, COMMUNITY_PUBLIC_URL, CONVERSATIONS_UNREAD_USER_CHATROOM_KEY, ONE_DAY_HOURS
from utility.firebase import update_my_chatrooms_on_homefeed_in_firebase
from utility.number_utilities import NumberUtilities
from utility.states import card_types, conversation_poll_types, conversation_states, community_level_states, \
    level_click_states, event_access, event_webflow_update_types, deleted_members, collabcard_states, SyncTypes, \
    community_setting_types, CollabcardTypes, poll_types, message_template_chatroom_types

from utility.validation_utilities import ValidationUtilities

from collabmates_api.search.sync import ElasticSearchSync

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


@shared_task
def set_chatroom_state_for_all_members_on_card_creation(community_id, card_id, **kwargs):
    card_instance = Collabcard.objects.get(id=card_id)
    all_members = Members.objects \
        .filter(community_id=community_id) \
        .filter(Q(state=member_states.ADMIN) |
                Q(state=member_states.MEMBER) |
                Q(state=member_states.PROFILE_UNAVAILABLE))

    for data in all_members:
        state_filter = collabcardState.objects.filter(user=data.member_id, card=card_instance)

        if not state_filter.exists():

            try:
                user_instance = data.member_id
                collabcard_state_instance = collabcardState()
                collabcard_state_instance.card = card_instance
                collabcard_state_instance.community = card_instance.community
                collabcard_state_instance.user = user_instance
                collabcard_state_instance.state = 0
                collabcard_state_instance.created_at = time.time()
                collabcard_state_instance.updated_at = time.time()
                collabcard_state_instance.external_seen = False
                collabcard_state_instance.save()

            except Exception as e:
                info_logger.info(e.args)

                if "function_called" in kwargs:
                    info_logger.info(
                        f"set_chatroom_state_for_all_members_on_card_creation called by function {kwargs['function_called']}")

                info_logger.info("Duplicate key creation in collabcardState table")

        if card_instance.attachment_count != 0 and card_instance.attachments_uploaded is False:
            continue

        update_last_unseen_in_engage(user=data.member_id.id, community=community_id, is_seen=True)


@shared_task
def update_last_unseen_in_engage_on_card_creation(community_id, is_seen=True):
    """function to update the unseen  collabcard in engage when a new collabcard is posted in community
       for all members in the community"""
    community_members = Members.objects \
        .filter(community_id=community_id) \
        .filter(Q(state=member_states.ADMIN) |
                Q(state=member_states.MEMBER) |
                Q(state=member_states.KNOWN_NOMINATED_PROMOTER) |
                Q(state=member_states.PROFILE_UNAVAILABLE))

    for member in community_members:
        update_last_unseen_in_engage(user=member.member_id_id, community=community_id, is_seen=is_seen)


def update_last_unseen_in_engage(user='', community='', is_seen=False):
    '''function to update the unseen  collabcard in engage'''

    total_chatrooms = collabcardState.objects.filter(community=community,
                                                     user=user, card__is_deleted=False, card__is_pending=False,
                                                     secret_chatroom_left=False).filter(Q(card__attachment_count=0)
                                                                                        | Q(
        card__attachments_uploaded=True)).exclude(card__type__in=[card_types.CARD_INTRO,
                                                                  card_types.CARD_EVENT,
                                                                  card_types.CARD_PUBLIC_EVENT]).distinct('card_id').count()

    seen_chatrooms_filter = collabcardState.objects.filter(community=community,
                                                           user=user, external_seen=True, card__is_deleted=False,
                                                           card__is_pending=False,
                                                           secret_chatroom_left=False).filter(
        Q(card__attachment_count=0) | Q(
            card__attachments_uploaded=True)).exclude(card__type__in=[card_types.CARD_INTRO,
                                                                      card_types.CARD_EVENT,
                                                                      card_types.CARD_PUBLIC_EVENT]).distinct('card')

    seen_chatrooms = seen_chatrooms_filter.count()

    excluded_card_ids_count = 0

    if user and community:
        user_id = user
        community_id = community

        if isinstance(user, User):
            user_id = user.id

        if isinstance(community, Community):
            community_id = community.id

        from collabmates_api.raw_queries import (get_card_ids_to_exclude_based_on_cohort_access,
                                                 get_chatrooms_of_user_with_follow_status)

        excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(user_id=user_id,
                                                                           community_id=community_id)

        followed_chatrooms = get_chatrooms_of_user_with_follow_status(user_id=user_id, community_id=community_id)

        seen_chatroom_list = list(seen_chatrooms_filter.values_list('card_id', flat=True))

        excluded_card_ids_count = len((set(excluded_card_ids) - set(followed_chatrooms)) - set(seen_chatroom_list))

    diff = total_chatrooms - seen_chatrooms - excluded_card_ids_count

    unseen_count = 0
    if diff <= 0:
        unseen_count = 0

    else:
        unseen_count = diff

    Member_Engage.objects.filter(community_id=community, member_id=user).update(
        last_unseen_count=unseen_count,
        updated_at=TimeUtilities.current_time_in_sec()
    )

    if unseen_count > 0:
        member_instances = fetch_new_chatroom_creater_images(user, community)

        if len(member_instances) > 0:
            Member_Engage.objects.filter(community_id=community, member_id=user).update(
                new_chatroom_users=json.dumps(member_instances),
                updated_at=time.time())
        else:
            Member_Engage.objects.filter(community_id=community, member_id=user).update(
                new_chatroom_users=None,
                updated_at=time.time())


def fetch_new_chatroom_creater_images(member_id, community_id):
    unseen_chatrooms = collabcardState.objects.filter(user=member_id, community_id=community_id,
                                                      external_seen=False,
                                                      card__is_deleted=False,
                                                      secret_chatroom_left=False).exclude(card__type=1).distinct('card')

    member_set = set()
    member_list = []

    for data in unseen_chatrooms:

        user_instance = data.card.user

        if user_instance not in member_set:

            member_filter = Members.objects.filter(member_id=user_instance, community_id=data.community)
            image_url = user_instance.userinfo.image_link if user_instance.userinfo.image_link else ''
            exists = member_filter.exists()

            if exists:
                member_instance = member_filter[0]

                if member_instance.image_url:
                    image_url = member_instance.image_url

            member = get_user_profile(user_instance, community_id, send_profile=False)
            member['image_url'] = image_url
            member_list.append(member)
            member_set.add(user_instance)

        if len(member_list) > 3:
            break

    return member_list


def compute_last_seen_conversations_of_user(chatroom_id, user_list):
    chatroom_user_filter = collabcardState.objects.filter(card=chatroom_id, user__in=user_list)

    user_data_dict = dict()

    for data in chatroom_user_filter:
        key = str(chatroom_id) + "$" + str(data.user_id)
        seen_id = data.last_seen_conversation_id

        if key not in user_data_dict:
            user_data_dict[key] = seen_id

    return user_data_dict


@shared_task
def update_my_chatrooms_for_users(chatroom_id, user_id=None):
    conversation_engage_filter = conversationEngage.objects.filter(card_id=chatroom_id)

    if not user_id:
        user_list = list(conversation_engage_filter.values_list('user_id', flat=True))

    else:
        user_list = [user_id]

    conversations = card_answers.objects \
        .filter(card_id=chatroom_id, state=0) \
        .filter(Q(attachment_count=0) |
                Q(attachments_uploaded=True) |
                Q(api_version=1)) \
        .order_by('id')
    last_conversation = conversations.last()
    second_last = None

    if last_conversation:
        second_last = card_answers.objects \
            .filter(card_id=chatroom_id, state=0) \
            .filter(Q(attachment_count=0) |
                    Q(attachments_uploaded=True) |
                    Q(api_version=1)) \
            .filter(~Q(user=last_conversation.user)) \
            .last()

    last_conversations = get_latest_conversation_members(chatroom_id)

    member_conversations = last_conversations[0]
    user_conversations = last_conversations[1]

    last_conversation_member = None
    second_last_conversation_member = None

    if len(member_conversations) > 1:
        last_conversation_member = member_conversations[0]
        second_last_conversation_member = member_conversations[1]

    elif len(member_conversations) == 1:
        last_conversation_member = member_conversations[0]

    last_conversation_user = None
    second_last_conversation_user = None

    if len(user_conversations) > 1:
        last_conversation_user = user_conversations[0]
        second_last_conversation_user = user_conversations[1]

    elif len(user_conversations) == 1:
        last_conversation_user = user_conversations[0]

    length = len(conversations)

    user_data_dict = compute_last_seen_conversations_of_user(chatroom_id, user_list)

    for user in user_list:

        key = str(chatroom_id) + "$" + str(user)
        seen_id = user_data_dict.get(key)

        if seen_id:
            unseen_count = card_answers.objects.filter(card_id=chatroom_id,
                                                       id__gt=seen_id).filter(Q(state=conversation_states.ANSWER)
                                                                              | Q(
                state=conversation_states.CONVERSATION_POLL)).count()
            conversation_engage_filter.filter(user=user).update(
                last_conversation=last_conversation,
                second_last_conversation=second_last,
                updated_at=time.time(),
                unseen_count=unseen_count,
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user

            )

        else:
            conversation_engage_filter.filter(user=user).update(
                last_conversation=last_conversation,
                second_last_conversation=second_last,
                updated_at=time.time(),
                unseen_count=length,
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user

            )

        conversation_id = str(last_conversation.id) if last_conversation else ""
        update_my_chatrooms_on_homefeed_in_firebase(chatroom_id, user, conversation_id)


def get_latest_conversation_members(chatroom_id):
    """function to get last conversation members"""

    card_instance = Collabcard.objects.get(id=chatroom_id)

    answer_filter = card_answers.objects.filter(card=card_instance, state=0).order_by('-id')

    user_set = set()

    member_conversarions = []
    user_conversations = []

    for data in answer_filter:

        if data.card.user.id == data.user.id:
            continue

        if data.user not in user_set:

            member_filter = Members.objects.filter(community_id=card_instance.community, member_id=data.user)

            if member_filter.exists():
                member_instance = member_filter[0]
                member_conversarions.append(member_instance)

            else:
                state_filter = collabcardState.objects.filter(card=card_instance, user=data.user)

                if state_filter.exists():
                    state_instance = state_filter[0]
                    user_conversations.append(state_instance)

            user_set.add(data.user)

        if len(user_set) > 1:
            break

    return member_conversarions, user_conversations


def get_chatroom_user_images_for_web(chatroom_id):
    last_conversations = get_latest_conversation_members(chatroom_id)

    member_conversations = last_conversations[0]
    user_conversations = last_conversations[1]

    last_conversation_member = None
    second_last_conversation_member = None

    if len(member_conversations) > 1:
        last_conversation_member = member_conversations[0]
        second_last_conversation_member = member_conversations[1]

    elif len(member_conversations) == 1:
        last_conversation_member = member_conversations[0]

    last_conversation_user = None
    second_last_conversation_user = None

    if len(user_conversations) > 1:
        last_conversation_user = user_conversations[0]
        second_last_conversation_user = user_conversations[1]

    elif len(user_conversations) == 1:
        last_conversation_user = user_conversations[0]

    conversation_meta = {
        'last_conversation_member': last_conversation_member,
        'second_last_conversation_member': second_last_conversation_member,
        'last_conversation_user': last_conversation_user,
        'second_last_conversation_user': second_last_conversation_user
    }

    return conversation_meta


@shared_task
def update_preview_of_chatroom_in_cache(preview_info):
    """ function to update the preview of chatroom """

    preview_url = preview_info.get('preview_url')
    chatroom_id = preview_info.get('chatroom_id')
    conversation_id = preview_info.get('conversation_id')

    if not conversation_id:
        return

    if not preview_url and not chatroom_id:
        return

    elif not preview_url:
        preview_url = settings.URL + "/collabcard/" + str(chatroom_id)

    key = CHATROOM_PREVIW_CACHE_KEY % (str(chatroom_id), str(conversation_id))
    preview_object = preview_info.get('preview_object')

    if not preview_object:
        try:
            preview_object = get_preview_for_url(preview_url=preview_url)
        except Exception as e:
            error_logger.error((str(e.args)))
            return

    if preview_object:
        CacheImpl.set_cache(key, preview_object)


@shared_task
def update_multiple_previews_in_chatroom(preview_info):
    preview_chatroom_id = preview_info.get('chatroom_id')

    if preview_chatroom_id:
        preview_filter = ModelUtilities.get_model_filter(card_answers, {'preview_chatroom': preview_chatroom_id,
                                                                        'preview_type': "chatroom"})

        for conversation in preview_filter:

            try:
                preview_dict = get_preview_for_url(preview_url=conversation.internal_link,
                                                   community_instance=conversation.preview_community,
                                                   chatroom_instance=conversation.preview_chatroom)
            except Exception as e:
                error_logger.error(str(e.args))
                continue

            if preview_dict:
                update_preview_of_chatroom_in_cache({'chatroom_id': conversation.preview_chatroom.id,
                                                     'preview_object': preview_dict,
                                                     'conversation_id': conversation.id})
            conversation.last_updated = TimeUtilities.current_time_in_milliseconds()
            conversation.save()


@shared_task
def update_preview_of_community_in_cache(preview_info):
    preview_url = preview_info.get('preview_url')
    community_id = preview_info.get('community_id')
    conversation_id = preview_info.get('conversation_id')

    if not conversation_id:
        return

    if not preview_url and not community_id:
        return

    elif not preview_url:
        preview_url = settings.URL + "/community/" + str(community_id)

    preview_object = preview_info.get('preview_object')

    if not preview_object:

        try:
            preview_object = get_preview_for_url(preview_url=preview_url)

        except Exception as e:
            error_logger.error((str(e.args)))
            return

    if preview_object:
        key = CONVERSATION_COMMUNITY_PREVIEW % (str(conversation_id), str(community_id))
        CacheImpl.set_cache(key, preview_object)


@shared_task
def update_multiple_previews_in_community(preview_info):
    preview_community_id = preview_info.get('community_id')

    if preview_community_id:
        preview_filter = card_answers.objects.filter(preview_community=preview_community_id). \
            filter(Q(preview_type='community') | Q(preview_type='directory'))

        for conversation in preview_filter:

            try:
                preview_dict = get_preview_for_url(preview_url=conversation.internal_link,
                                                   community_instance=conversation.preview_community,
                                                   )
            except Exception as e:
                error_logger.error(str(e.args))
                continue

            if preview_dict:
                update_preview_of_community_in_cache({'community_id': preview_community_id,
                                                      'preview_object': preview_dict,
                                                      'conversation_id': conversation.id})
            conversation.last_updated = TimeUtilities.current_time_in_milliseconds()
            conversation.save()


def update_member_images_for_account(member_filter, image_url):
    for data in member_filter:
        community_instance = data.community_id
        user_instance = data.member_id
        intro_filter = ModelUtilities.get_model_filter(Collabcard, {'community': community_instance,
                                                                    'type': card_types.CARD_INTRO,
                                                                    'user': user_instance})

        if intro_filter:
            card_instance = intro_filter[0]
            ModelUtilities.model_update(Card_Attachment,
                                        {'collabcard_id': card_instance.id},
                                        {'file_url': image_url})
            update_multiple_previews_in_chatroom({'chatroom_id': card_instance.id})
        data.image_url = image_url
        data.updated_at = TimeUtilities.current_time_in_sec()
        data.save()


@shared_task
def update_preview_for_account_image_change(preview_info):
    user_id = preview_info.get('user_id')
    image_url = preview_info.get('image_url')
    previous_image_url = preview_info.get('previous_image_url')

    if not user_id or not image_url:
        return

    member_filter = ModelUtilities.get_model_filter(Members, {'member_id_id': user_id,
                                                              'image_url': None})

    update_member_images_for_account(member_filter, image_url)

    member_filter = ModelUtilities.get_model_filter(Members, {'member_id_id': user_id,
                                                              'image_url': previous_image_url})
    update_member_images_for_account(member_filter, image_url)


@shared_task
def unpin_the_chatroom(card_id):
    ModelUtilities.model_update(Collabcard, {'id': card_id}, {'is_pinned': False})


def schedule_chatroom_unpinning_after_event_completion(card_instance):
    card_id = card_instance.id
    args = [card_id]

    card_end_time = TimeUtilities.convert_milliseconds_to_sec(card_instance.end_date)
    task_begin_epoch_time = card_end_time
    task_expiry_epoch_time = TimeUtilities.add_minutes_to_epoch_time(task_begin_epoch_time, minutes=5)

    task_begin_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_epoch_time)
    task_expiry_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_epoch_time)

    unpin_the_chatroom.apply_async(args=args, kwargs={},
                                   eta=task_begin_date_time,
                                   expires=task_expiry_date_time)


def update_chatroom_conversation_count_in_cache(count_info):
    chatroom_id = count_info.get('chatroom_id')

    if not chatroom_id:
        return

    key = CONVERSATIONS_COUNT_CACHE_KEY % str(chatroom_id)
    previous_count = CacheImpl.get_cache(key)

    if previous_count:
        total_responses_count = previous_count.get('total_responses_count', 0) + 1
        previous_count['total_responses_count'] = total_responses_count

    else:
        previous_count = {}
        conversations_count = count_info.get('total_responses_count')

        if not conversations_count:
            conversations_count = ModelUtilities.get_model_filter(card_answers,
                                                                  {'card': chatroom_id,
                                                                   'state': conversation_states.ANSWER}).filter(
                Q(attachment_count=0)
                | Q(attachments_uploaded=True)).count()

        previous_count['total_responses_count'] = conversations_count
    CacheImpl.set_cache(key, previous_count)


def update_chatroom_conversation_creators_in_cache(conversation_creator_info):
    chatroom_id = conversation_creator_info.get('chatroom_id')

    if not chatroom_id:
        return

    key = CONVERSATIONS_DISTINCT_CREATORS_KEY % str(chatroom_id)
    conversation_creator_dict = CacheImpl.get_cache(key)

    if conversation_creator_dict:
        user_id = conversation_creator_info.get('user_id')

        user_id = NumberUtilities.get_integer_from_string(user_id)

        if not user_id:
            return

        conversation_creator_list = conversation_creator_dict['conversation_creator_list']
        list_len = len(conversation_creator_list)

        if list_len and (user_id not in conversation_creator_list):

            if list_len == 5:
                conversation_creator_list.pop(0)

            conversation_creator_list.append(user_id)
            conversation_creator_dict['conversation_creator_list'] = conversation_creator_list
            CacheImpl.set_cache(key, conversation_creator_dict)

    else:

        conversation_creator_list = conversation_creator_info.get('conversation_creator_list')

        if not conversation_creator_list:
            conversation_creator_list = []
            conversation_filter = card_answers.objects \
                                      .filter(card=chatroom_id, state=conversation_states.ANSWER) \
                                      .filter(Q(attachment_count=0) |
                                              Q(attachments_uploaded=True)) \
                                      .distinct('user') \
                                      .order_by('user', '-id')[:5]

            for data in conversation_filter:
                user_id = data.user_id
                conversation_creator_list.append(user_id)

        if conversation_creator_list:
            conversation_creator_dict['conversation_creator_list'] = conversation_creator_list

            CacheImpl.set_cache(key, conversation_creator_dict)


def get_to_show_results_for_conversation_poll(conversation_context):

    try:
        conversation_id = conversation_context.get('conversation_id')
        member_id = NumberUtilities.get_integer_from_string(conversation_context.get('member_id'))
        conversation_instance = conversation_context.get('conversation_instance')
        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not conversation_instance:
            conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

        is_cm = Members.is_member_community_promoter(conversation_instance.community, user_instance)
        # If user is CM or Creator of POLL, to_show_results will be true

        if is_cm or user_instance == conversation_instance.user:
            return True

        if not conversation_instance.expiry_time:
            return True

        if TimeUtilities.current_time_in_milliseconds() >= conversation_instance.expiry_time:
            return True

        conversation_poll_options = ModelUtilities.get_model_filter(conversationPolls,
                                                                    {'conversation': conversation_instance})
        conversation_poll_members = ModelUtilities.get_model_filter(conversationPollMembers,
                                                                    {'conversation': conversation_instance})
        poll_members_dict = {}

        for data in conversation_poll_members:

            poll_id = data.poll_id
            user_id = data.user_id

            if poll_id not in poll_members_dict:
                poll_members_dict[poll_id] = [user_id]

            else:
                poll_members_dict[poll_id].append(user_id)

        for data in conversation_poll_options:
            poll_id = data.id
            chatroom_votes = poll_members_dict.get(poll_id)

            if not chatroom_votes:
                chatroom_votes = []

            is_selected = member_id in chatroom_votes

            if conversation_instance.poll_type == conversation_poll_types.INSTANT and is_selected is True:
                return True

        return False

    except Exception as e:
        error_logger.error(f'error in method=get_to_show_results_for_conversation_poll, error={e}')
        return False


def compute_conversation_polls_from_cache(poll_options, poll_voters, member_id, conversation_context):
    total_votes = poll_voters.get('total_votes', 0)
    total_user_set = poll_voters.get('total_user_set')
    chatroom_poll_members = poll_voters.get('conversation_poll_members', {})

    polls = []

    multi_select = conversation_context.get('multiple_select_no', None)

    for data in poll_options:

        poll_id = data['id']
        temp = dict()
        temp['id'] = data['id']
        temp['text'] = data['text']
        temp['is_selected'] = False
        temp['no_votes'] = 0
        temp['percentage'] = 0

        if data.get('member'):
            temp['member'] = data.get('member')

        chatroom_votes = chatroom_poll_members.get(poll_id)

        if not chatroom_votes:
            chatroom_votes = []

        temp['is_selected'] = member_id in chatroom_votes
        count = len(chatroom_votes)

        if multi_select:
            total_votes = len(total_user_set)

        if total_votes != 0:
            temp['no_votes'] = count
            temp['percentage'] = int((count / total_votes) * 100)

        polls.append(temp)

    return polls


def compute_conversation_poll_options_from_cache(poll_options, conversation_info):

    polls = []

    for data in poll_options:

        temp = dict()
        temp['id'] = data['id']
        temp['text'] = data['text']
        temp['is_selected'] = False
        temp['no_votes'] = 0
        temp['percentage'] = 0

        if data.get('member'):
            temp['member'] = data.get('member')

        polls.append(temp)

    return polls


def compute_conversation_polls(conversation_info):
    conversation_id = conversation_info.get('conversation_id')
    member_id = conversation_info.get('member_id')
    conversation_instance = conversation_info.get('conversation_instance')

    if not conversation_instance:
        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

    conversation_poll_options = ModelUtilities.get_model_filter(conversationPolls,
                                                                {'conversation': conversation_instance})
    conversation_poll_members = ModelUtilities.get_model_filter(conversationPollMembers,
                                                                {'conversation': conversation_instance})

    poll_members_dict = {}

    total_user_set = set()

    for data in conversation_poll_members:

        poll_id = data.poll_id
        user_id = data.user_id
        total_user_set.add(user_id)

        if poll_id not in poll_members_dict:
            poll_members_dict[poll_id] = [user_id]
        else:
            poll_members_dict[poll_id].append(user_id)

    if conversation_instance.multiple_select_no:
        is_multi = True
    else:
        is_multi = False

    total_votes = conversation_poll_members.count()

    polls = []
    user_dict = {}

    for data in conversation_poll_options:

        poll_id = data.id
        temp = dict()
        temp['id'] = poll_id
        temp['text'] = data.text
        temp['is_selected'] = False
        temp['no_votes'] = 0
        temp['percentage'] = 0

        if user_dict.get(data.user_id):
            temp['member'] = user_dict.get(data.user_id)

        else:
            temp['member'] = UserinfoSerializer(data.user.userinfo)
            user_dict[data.user_id] = temp['member']

        chatroom_votes = poll_members_dict.get(poll_id)

        if not chatroom_votes:
            chatroom_votes = []

        temp['is_selected'] = member_id in chatroom_votes
        count = len(chatroom_votes)

        if is_multi:
            total_votes = len(total_user_set)

        if total_votes != 0:
            temp['no_votes'] = count
            temp['percentage'] = int((count / total_votes) * 100)

        polls.append(temp)

    return polls


def get_conversation_poll(conversation_info):
    conversation_id = conversation_info.get('conversation_id')
    member_id = conversation_info.get('member_id')

    member_id = NumberUtilities.get_integer_from_string(member_id)
    option_key = CONVERSATION_POLL_OPTIONS_CONVERSATION_ID % (str(conversation_id))
    voters_key = CONVERSATION_POLL_VOTERS_CONVERSATION_ID % (str(conversation_id))

    poll_options = CacheImpl.get_cache(option_key)
    poll_voters = CacheImpl.get_cache(voters_key)

    if poll_options and poll_voters:
        polls = compute_conversation_polls_from_cache(poll_options, poll_voters, member_id, conversation_info)

    elif poll_options:
        polls = compute_conversation_poll_options_from_cache(poll_options, conversation_info)

    else:
        polls = compute_conversation_polls(conversation_info)

    return polls


def save_conversation_poll_options_in_cache(options_info):
    polls = options_info.get('polls')
    user_id = options_info.get('user_id')
    conversation_id = options_info.get('conversation_id')

    if not user_id or \
            not conversation_id:
        return

    if not polls:

        polls = []
        poll_filter = ModelUtilities.get_model_filter(conversationPolls,
                                                      {'conversation': conversation_id}).order_by('id')

        user_dict = {}

        for poll in poll_filter:

            temp = {
                'id': poll.id,
                'text': poll.text,
                'user_id': poll.user_id
            }

            if user_dict.get(poll.user_id):
                member = user_dict.get(poll.user_id)

            else:
                member = UserinfoSerializer(poll.user.userinfo)
                user_dict[poll.user_id] = member

            temp['member'] = member
            polls.append(temp)

    key = CONVERSATION_POLL_OPTIONS_CONVERSATION_ID % str(conversation_id)

    CacheImpl.set_cache(key, polls)


def save_conversation_poll_voters_in_cache(vote_info):
    conversation_instance = vote_info.get('conversation_instance')

    if not conversation_instance:
        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                          vote_info.get('conversation_id'))

        if not conversation_instance:
            return

    conversation_poll_members = ModelUtilities.get_model_filter(conversationPollMembers,
                                                                {'conversation': conversation_instance})

    poll_members_dict = {}

    total_user_set = set()

    for data in conversation_poll_members:

        poll_id = data.poll_id
        user_id = data.user_id
        total_user_set.add(user_id)

        if poll_id not in poll_members_dict:
            poll_members_dict[poll_id] = [user_id]

        else:
            poll_members_dict[poll_id].append(user_id)

    cache_context = dict()
    cache_context['conversation_poll_members'] = poll_members_dict
    cache_context['total_user_set'] = total_user_set
    cache_context['total_votes'] = conversation_poll_members.count()

    key = CONVERSATION_POLL_VOTERS_CONVERSATION_ID % (str(conversation_instance.id))
    CacheImpl.set_cache(key, cache_context)


@shared_task
def update_event_instructors_in_cache(instructors_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, instructors_info.get('chatroom_id'))

    if not card_instance:
        return

    instructors_list = instructors_info.get('instructors_list', [])

    if not instructors_list:
        return

    CacheImpl.set_cache(EVENT_INSTRUCTORS_CHATROOM % str(card_instance.id), {
        'instructors_list': instructors_list
    })


@shared_task
def update_event_highlights_in_cache(highlights_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, highlights_info.get('chatroom_id'))

    if not card_instance:
        return

    highlights_list = highlights_info.get('highlights_list', [])

    if not highlights_list:
        return

    CacheImpl.set_cache(EVENT_HIGHLIGHTS_CHATROOM % str(card_instance.id), {
        'highlights_list': highlights_list
    })


@shared_task
def update_event_member_testimonials_in_cache(testimonials_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, testimonials_info.get('chatroom_id'))

    if not card_instance:
        return

    testimonials_list = testimonials_info.get('testimonials_list', [])

    if not testimonials_list:
        return

    CacheImpl.set_cache(EVENT_MEMBERTESTIMONIALS_CHATROOM % str(card_instance.id), {
        'testimonials_list': testimonials_list
    })


@shared_task
def update_event_faq_in_cache(faqs_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, faqs_info.get('chatroom_id'))

    if not card_instance:
        return

    faqs_list = faqs_info.get('faqs_list', [])

    if not faqs_list:
        return

    CacheImpl.set_cache(EVENT_FAQ_CHATROOM % str(card_instance.id), {
        'faqs_list': faqs_list
    })


def status_based_add_or_remove_user_id_from_attendees_list(user_id, status, event_attendees_list):
    is_user_present = user_id in event_attendees_list

    if not status and is_user_present:
        event_attendees_list.remove(user_id)

    elif status and not is_user_present:
        event_attendees_list.append(user_id)

    return event_attendees_list


@shared_task
def update_event_attendees(attendees_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, attendees_info.get('chatroom_id'))

    if not card_instance:
        return

    user_id = attendees_info.get('user_id')
    status = attendees_info.get('status')

    event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CHATROOM % str(card_instance.id))

    if event_attendees_dict and user_id:
        event_attendees_list = event_attendees_dict.get('event_attendees_list', [])

        if isinstance(user_id, list):

            user_ids_list = user_id

            for user_id in user_ids_list:
                event_attendees_list = status_based_add_or_remove_user_id_from_attendees_list(user_id, status,
                                                                                              event_attendees_list)

        else:
            event_attendees_list = status_based_add_or_remove_user_id_from_attendees_list(user_id, status,
                                                                                          event_attendees_list)

        CacheImpl.set_cache(EVENT_ATTENDEES_CHATROOM % str(card_instance.id), {
            'event_attendees_list': event_attendees_list
        })

        return

    event_attendees_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                {'card': card_instance,
                                                                 'attending_status': True}
                                                                ).values_list('user', flat=True).
                                order_by('created_at', 'id'))

    CacheImpl.set_cache(EVENT_ATTENDEES_CHATROOM % str(card_instance.id), {
        'event_attendees_list': event_attendees_list
    })


@shared_task
def set_levels_on_ctc_celery(community_levels_info):
    '''updating levels based on different call to actions'''

    community_id = community_levels_info.get("community_id")
    level = community_levels_info.get("level")
    promoter = community_levels_info.get("promoter")

    if promoter:
        return

    community_level_filter = communityLevels.objects.filter(community_id=community_id).order_by('id')
    for instance in community_level_filter:

        if instance.level == level and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 3").update(title=LEVEL_3_TITLE,
                                                                      sub_title=LEVEL_3_SUB_TITLE,
                                                                      state=community_level_states.PENDING)

        elif instance.level == level and instance.state == community_level_states.PENDING:

            if instance.joined_members < instance.max_members:
                instance.joined_members = instance.joined_members + 1
                instance.save()

            if instance.joined_members >= instance.max_members:
                instance.state = community_level_states.COMPLETE
                instance.save()

                community_level_filter.filter(level="Level 4").update(title=LEVEL_4_TITLE,
                                                                      sub_title=LEVEL_4_SUB_TITLE,
                                                                      state=community_level_states.PENDING)


@shared_task
def set_level_click_state(level_click_state_info):
    community_id = level_click_state_info.get("community_id")
    is_promoter = level_click_state_info.get("is_promoter")

    # setting the level click state when the promoter set-up directory and update the click state

    if ModelUtilities.is_model_filter_exists(communityLevels,
                                             {'community_id': community_id,
                                              'level': "Level 3",
                                              'level_click_state': level_click_states.DIRECTORY_CREATED}):

        if is_promoter:
            ModelUtilities.model_update(communityLevels,
                                        {'community_id': community_id, 'level': "Level 3"},
                                        {'level_click_state': level_click_states.COMMUNITY_JOINED})


def get_event_pricing(card_id):
    client = ApiClient(host=settings.SUBSCRIPTION_SERVER_URL,
                       method='get',
                       path=SUBSCRIPTION_FETCH_EVENT_PLAN)

    client.add_url_param('chatroom_ids', [card_id])
    client.request()
    response = client.fetch_response()
    cost_list = [data.get('cost') for data in response.get('event_plans', [])]

    return cost_list


def compute_event_metadata_for_analytics(card_instance, community_instance):
    cost_list = get_event_pricing(card_instance.id)

    if not cost_list:
        cost_list = [0]

    event_metadata = {
        'event_id': card_instance.id,
        'community_id': community_instance.id,
        'community_name': community_instance.name,
        'event_name': card_instance.header,
        'event_date': TimeUtilities.convert_epoch_time_to_date_month_year(card_instance.date_time),
        'event_time': TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(card_instance.date_time),
        'event_type': "paid" if card_instance.is_paid else "free",
        'registered': True,
        'event_link': CHATROOM_LINK % (settings.URL, str(card_instance.id)),
        'event_cost': cost_list
    }

    return event_metadata


@shared_task
def send_analytics_on_event_attend_link_click(card_id, user_id):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return

    community_instance = card_instance.community

    event_metadata = compute_event_metadata_for_analytics(card_instance, community_instance)

    if not event_metadata:
        return

    SegmentImpl.track_event(user_id, "Event attended (Core Service)", event_metadata)


@shared_task
def send_analytics_on_event_registered_to_attend(card_id, user_id, attending_status):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return

    community_instance = card_instance.community

    event_metadata = compute_event_metadata_for_analytics(card_instance, community_instance)

    if not event_metadata:
        return

    event_metadata['attending'] = "true" if attending_status else "false"
    del event_metadata['registered']
    SegmentImpl.track_event(user_id, "Event registered (Subscription Service + Core Service)", event_metadata)


@shared_task
def send_event_analytics_on_event_creation(card_id, user_id):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return

    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not user_instance:
        return

    event_name = "Event added (Core Service)"
    community_instance = card_instance.community

    event_metadata = compute_event_metadata_for_analytics(card_instance, community_instance)

    if not event_metadata:
        return

    del event_metadata['registered']

    SegmentImpl.track_event(user_instance.id, event_name, event_metadata)


@shared_task
def send_analytics_on_event_reminders(card_id, event_name):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return

    community_instance = card_instance.community

    event_metadata = compute_event_metadata_for_analytics(card_instance, community_instance)

    if not event_metadata:
        return

    user_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                     {'card': card_instance,
                                                      'attending_status': True,
                                                      'remove': None}).values_list('user_id', flat=True))
    for user_id in user_list:
        SegmentImpl.track_event(user_id, event_name, event_metadata)


def schedule_event_analytics_on_event_start(card_instance):
    card_id = card_instance.id
    args = [card_id, "Event started (Core Service)"]

    task_begin_epoch_time = TimeUtilities.convert_milliseconds_to_sec(card_instance.date_time)
    task_expiry_epoch_time = TimeUtilities.add_minutes_to_epoch_time(task_begin_epoch_time, minutes=5)
    current_time = TimeUtilities.current_time_in_sec()

    if task_expiry_epoch_time <= current_time:
        return

    task_begin_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_epoch_time)
    task_expiry_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_epoch_time)
    send_analytics_on_event_reminders.apply_async(args=args, kwargs={},
                                                  eta=task_begin_date_time,
                                                  expires=task_expiry_date_time)


def schedule_event_analytics_daily_7AM(card_instance, n_hour, n_minute):
    card_id = card_instance.id
    args = [card_id, "Event day (Core Service)"]

    task_begin_epoch_time = TimeUtilities.get_epoch_from_datetime(card_instance.date_time,
                                                                  n_hour, n_minute)
    task_expiry_epoch_time = TimeUtilities.add_minutes_to_epoch_time(task_begin_epoch_time, minutes=5)
    current_time = TimeUtilities.current_time_in_sec()

    if task_expiry_epoch_time <= current_time:
        return

    task_begin_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_epoch_time)
    task_expiry_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_epoch_time)
    send_analytics_on_event_reminders.apply_async(args=args, kwargs={},
                                                  eta=task_begin_date_time,
                                                  expires=task_expiry_date_time)


def schedule_event_analytics_on_event_before_n_hour(card_instance, n):
    card_id = card_instance.id
    args = [card_id, "Event starting in %s hr (Core Service)" % str(n)]

    task_begin_epoch_time = TimeUtilities.subtract_hours_from_epoch_time(card_instance.date_time, n)
    task_expiry_epoch_time = TimeUtilities.add_minutes_to_epoch_time(task_begin_epoch_time, minutes=5)
    current_time = TimeUtilities.current_time_in_sec()

    if task_expiry_epoch_time <= current_time:
        return

    task_begin_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_epoch_time)
    task_expiry_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_epoch_time)
    send_analytics_on_event_reminders.apply_async(args=args, kwargs={},
                                                  eta=task_begin_date_time,
                                                  expires=task_expiry_date_time)


def create_event_request_meta_for_webflow_create(card_instance, community_instance):
    event_meta = {
        'fields': {
            'name': card_instance.header,
            'title': card_instance.about,
            'online-link': card_instance.online_link,
            'location': card_instance.location,
            'is-paid': card_instance.is_paid,
            'community-name': community_instance.name,
            '_draft': False,
            '_archived': False,
            'slug': StringUtilities.replace_character_in_string(card_instance.header, " ", "-"),
            'date-time': TimeUtilities.convert_epoch_time_to_webflow_time(card_instance.date_time),
            'end-date': TimeUtilities.convert_epoch_time_to_webflow_time(card_instance.end_date),
            'community-link': COMMUNITY_PUBLIC_URL % (settings.URL,
                                                      StringUtilities.get_string_from_integer(community_instance.id))
        }
    }

    return event_meta


def create_event_in_webflow_service(card_instance):
    if card_instance.type not in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
        return

    if card_instance.access == event_access.COMMUNITY_MEMBERS:
        return

    community_instance = card_instance.community
    request_meta = create_event_request_meta_for_webflow_create(card_instance, community_instance)
    event_meta = WebflowImpl.create_event_in_webflow(request_meta)

    if not event_meta:
        return

    ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, {
        'updated_at': TimeUtilities.current_time_in_milliseconds(),
        'event_web_page': settings.WEBFLOW_KEYS.get('web_url') + event_meta.get('slug', ""),
        'webflow_item_id': event_meta.get('_id')
    })

    ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                {'updated_at': TimeUtilities.current_time_in_sec()})


def create_update_request_meta_of_webflow_for_instructors(info_list):
    fields = {}
    i = 1

    for data in info_list:
        index = StringUtilities.get_string_from_integer(i)
        fields['instructors-image-' + index] = data.get('url', '')
        fields['instructors-about-' + index] = data.get('about', '')
        i = i + 1

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_highlights(info_list):
    fields = {}
    i = 1

    for data in info_list:
        index = StringUtilities.get_string_from_integer(i)
        fields['highlight-image-' + index] = data.get('url')
        fields['highlight-' + index] = data.get('highlight')
        i = i + 1

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_testimonials(info_list):
    fields = {}
    i = 1

    for data in info_list:
        index = StringUtilities.get_string_from_integer(i)
        fields['testimonial-image-' + index] = data.get('url')
        fields['testimonial-member-' + index] = data.get('member_name')
        fields['testimonial-' + index] = data.get('testimonial')
        i = i + 1

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_faq(info_list):
    fields = {}
    i = 1

    for data in info_list:
        index = StringUtilities.get_string_from_integer(i)
        fields['faq-question-' + index] = data.get('question')
        fields['faq-answer-' + index] = data.get('answer')
        i = i + 1

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_file(update_info):
    chatroom_id = update_info.get('chatroom_id')
    fields = {}
    file_filter = ModelUtilities.get_model_filter(Card_Attachment, {'collabcard': chatroom_id}).order_by('id')

    for data in file_filter:

        if data.type == 'image':
            fields['banner-img'] = data.file_url
            fields['banner-video'] = ''
            break

        if data.type == 'video':
            fields['banner-video'] = data.file_url
            fields['banner-img'] = ''
            break

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_event_meta(update_info):
    card_instance = update_info.get('card_instance')

    event_meta = {
        'fields': {
            'name': card_instance.header,
            'title': card_instance.about,
            'online-link': card_instance.online_link,
            'location': card_instance.location,
            'is-paid': card_instance.is_paid,
            'slug': StringUtilities.replace_character_in_string(card_instance.header, " ", "-"),
            'date-time': TimeUtilities.convert_epoch_time_to_webflow_time(card_instance.date_time),
            'end-date': TimeUtilities.convert_epoch_time_to_webflow_time(card_instance.end_date),
        }
    }

    return event_meta


def create_event_request_meta_for_webflow_update(update_info):
    req_meta = dict

    update_type = update_info.get('update_type')

    if update_type == event_webflow_update_types.FILE:
        req_meta = create_update_request_meta_of_webflow_for_file(update_info)

    elif update_type == event_webflow_update_types.INSTRUCTORS:
        req_meta = create_update_request_meta_of_webflow_for_instructors(update_info.get('instructors_list', []))

    elif update_type == event_webflow_update_types.HIGHLIGHTS:
        req_meta = create_update_request_meta_of_webflow_for_highlights(update_info.get('highlights_list', []))

    elif update_type == event_webflow_update_types.TESTIMONIALS:
        req_meta = create_update_request_meta_of_webflow_for_testimonials(update_info.get('testimonials_list', []))

    elif update_type == event_webflow_update_types.FAQ:
        req_meta = create_update_request_meta_of_webflow_for_faq(update_info.get('faqs_list', []))

    elif update_type == event_webflow_update_types.META:
        req_meta = create_update_request_meta_of_webflow_for_event_meta(update_info)

    return req_meta


@shared_task
def update_event_in_webflow_service(update_info):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, update_info.get('chatroom_id'))

    if not card_instance:
        return

    if card_instance.type not in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
        return

    if card_instance.access == event_access.COMMUNITY_MEMBERS:
        return

    update_info['card_instance'] = card_instance
    request_meta = create_event_request_meta_for_webflow_update(update_info)
    event_meta = WebflowImpl.update_event_in_webflow(request_meta, card_instance.webflow_item_id)

    if not event_meta:
        return

    ModelUtilities.model_update(Collabcard, {'id': card_instance.id}, {
        'updated_at': TimeUtilities.current_time_in_milliseconds(),
        'event_web_page': settings.WEBFLOW_KEYS.get('web_url') + event_meta.get('slug', ""),
    })

    ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                {'updated_at': TimeUtilities.current_time_in_sec()})


@shared_task
def update_event_attendees_for_micro_event(attendees_info):
    conversation_instance = attendees_info.get('conversation_instance')

    if not conversation_instance:
        conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers,
                                                                          attendees_info.get('conversation_id'))

        if not conversation_instance:
            return

    user_id = attendees_info.get('user_id')
    status = attendees_info.get('attending_status')

    event_attendees_dict = CacheImpl.get_cache(EVENT_ATTENDEES_CONVERSATION % str(conversation_instance.id))

    if event_attendees_dict and user_id:
        event_attendees_list = event_attendees_dict.get('event_attendees_list', [])

        is_user_present = user_id in event_attendees_list

        if not status and is_user_present:
            event_attendees_list.remove(user_id)

        if status and not is_user_present:

            if len(event_attendees_list) == 10:
                event_attendees_list.pop(0)

            event_attendees_list.append(user_id)

        CacheImpl.set_cache(EVENT_ATTENDEES_CONVERSATION % str(conversation_instance.id), {
            'event_attendees_list': event_attendees_list
        })

        return

    event_attendees_list = attendees_info.get('event_attendees_list', [])

    if not event_attendees_list:
        event_attendees_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                                    {'conversation': conversation_instance,
                                                                     'attending_status': True}
                                                                    ).values_list('user', flat=True).
                                    order_by('created_at')[:10])

    CacheImpl.set_cache(EVENT_ATTENDEES_CHATROOM % str(conversation_instance.id), {
        'event_attendees_list': event_attendees_list
    })


@shared_task
def member_left_removed_dm_chatroom(user_id, community_id, removed_members_id, removed_state, chatroom_ids_list=[]):
    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not user_instance:
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    instance = ModelUtilities.get_model_instance_or_none(removedMembers, removed_members_id)

    # Create Card Answer for all DM Chatroom
    dm_chatroom_instances = ModelUtilities.get_model_filter(Collabcard,
                                                            {"id__in": chatroom_ids_list})

    # Create Card Answer Instances
    message = MEMBER_LEFT_DM_CHATROOM_MESSAGE if removed_state == deleted_members.LEFT else \
        MEMBER_REMOVED_DM_CHATROOM_MESSAGE

    user_route = user_route = "<<" + str(user_instance.userinfo.name) + "|route://member/" + str(
        user_instance.id) + ">>"
    community_route = "<<" + str(community_instance.name) + "|route://community?community_id=" + str(
        community_instance.id) + ">>"

    message = message.format(user_route, community_route)

    conversation_engage_instances = ModelUtilities.get_model_filter(conversationEngage,
                                                                    {"card__in": dm_chatroom_instances})

    for dm_chatroom in dm_chatroom_instances:
        card_answer_instance = card_answers(card=dm_chatroom, user=user_instance, community=community_instance,
                                            answer=message,
                                            state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_REMOVED_OR_LEFT,
                                            remove=instance)

        card_answer_instance.save()

        # Update ConversationEngage
        conversation_engage_instance = conversation_engage_instances.filter(card=dm_chatroom)

        card_created_at = TimeUtilities.convert_milliseconds_to_sec(card_answer_instance.last_updated)

        conversation_engage_instance.update(last_conversation=card_answer_instance,
                                            updated_at=card_created_at)

        ModelUtilities.get_model_filter(collabcardState, {"card__in": dm_chatroom_instances})

        conversation_engage_instance.exclude(user=user_instance).update(unseen_count=F('unseen_count') + 1)


@shared_task
def cm_removed_dm_chatroom(user_id, community_id, is_m2cm_v2=False):
    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not user_instance:
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    member_ids_list = ModelUtilities.get_model_filter(Members,
                                                      {"community_id": community_instance,
                                                       "state": member_states.MEMBER}).exclude(
        member_id=user_instance).values_list("member_id_id", flat=True)

    # Create Card Answer for all DM Chatroom
    dm_chatroom_instances_ids_as_creator = ModelUtilities.get_model_filter(Collabcard,
                                                                           {"user": user_instance,
                                                                            "chatroom_with_user_id__in": member_ids_list,
                                                                            "community": community_instance,
                                                                            "is_private": True}). \
        exclude(chatroom_with_user=None).values_list("id", flat=True)

    dm_chatroom_instances_ids_as_user = ModelUtilities.get_model_filter(Collabcard,
                                                                        {"chatroom_with_user": user_instance,
                                                                         "user_id__in": member_ids_list,
                                                                         "community": community_instance,
                                                                         "is_private": True}). \
        exclude(chatroom_with_user=None).values_list("id", flat=True)

    dm_chatroom_instances = list(dm_chatroom_instances_ids_as_creator) + list(dm_chatroom_instances_ids_as_user)
    dm_chatroom_instances = ModelUtilities.get_model_filter(Collabcard, {"id__in": dm_chatroom_instances})

    # Create Card Answer Instances
    user_route = "<<" + str(user_instance.userinfo.name) + "|route://member/" + str(user_instance.id) + ">>"

    message = CM_REMOVED_COMMUNITY_DM_CHATROOM_MESSAGE

    message = message.format(user_route)

    conversation_engage_instances = ModelUtilities.get_model_filter(conversationEngage,
                                                                    {"card__in": dm_chatroom_instances})

    for dm_chatroom in dm_chatroom_instances:
        is_private_member = all([Members.get_community_member_state(dm_chatroom.community, dm_chatroom.user) ==
                                 member_states.MEMBER,
                                 Members.get_community_member_state(dm_chatroom.community,
                                                                    dm_chatroom.chatroom_with_user) ==
                                 member_states.MEMBER])

        if is_private_member != dm_chatroom.is_private_member:
            dm_chatroom.is_private_member = is_private_member
            dm_chatroom.save()

            update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': dm_chatroom}, {})

        card_answer_instance = card_answers(card=dm_chatroom, user=user_instance, community=community_instance,
                                            answer=message,
                                            state=conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_REMOVED)

        card_answer_instance.save()

        # Update ConversationEngage
        conversation_engage_instance = conversation_engage_instances.filter(card=dm_chatroom)

        card_created_at = TimeUtilities.convert_milliseconds_to_sec(card_answer_instance.last_updated)

        conversation_engage_instance.update(last_conversation=card_answer_instance,
                                            updated_at=card_created_at)

        ModelUtilities.get_model_filter(collabcardState, {"card__in": dm_chatroom_instances})

        conversation_engage_instance.exclude(user=user_instance).update(unseen_count=F('unseen_count') + 1)

    # Create DM chatroom for new member
    create_member_dm_chatroom(user_id, community_id, is_cm_member=True, is_m2cm_v2=is_m2cm_v2)


@shared_task
def member_becomes_cm_dm_chatroom(user_id, community_id, is_m2cm_v2=False):
    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not user_instance:
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    member_instance = ModelUtilities.get_model_filter(Members,
                                                      {"member_id": user_instance,
                                                       "community_id": community_instance})

    if not member_instance:
        return

    else:
        member_instance = member_instance[0]

    is_promoter = member_instance.state == member_states.ADMIN

    if is_promoter:
        cms_user_ids_list = list(ModelUtilities.get_model_filter(Members,
                                                                 {"state": member_states.ADMIN,
                                                                  "community_id": community_instance}).exclude(
            id=member_instance.id).values_list("member_id_id", flat=True))

        # Create Card Answer for all DM Chatroom
        dm_chatroom_instances_with_user = ModelUtilities.get_model_filter(Collabcard,
                                                                          {"chatroom_with_user": user_instance,
                                                                           "user_id__in": cms_user_ids_list,
                                                                           "community_id": community_id,
                                                                           "is_private": True}).values_list("id",
                                                                                                            flat=True)

        dm_chatroom_instances_with_user_as_creator = ModelUtilities.get_model_filter(Collabcard,
                                                                                     {
                                                                                         "chatroom_with_user_id__in": cms_user_ids_list,
                                                                                         "user": user_instance,
                                                                                         "community_id": community_id,
                                                                                         "is_private": True}).values_list(
            "id", flat=True)

        dm_chatroom_instances = list(dm_chatroom_instances_with_user) + list(dm_chatroom_instances_with_user_as_creator)
        dm_chatroom_instances = ModelUtilities.get_model_filter(Collabcard, {"id__in": dm_chatroom_instances})

        # Create Card Answer Instances
        user_route = "<<" + str(user_instance.userinfo.name) + "|route://member/" + str(user_instance.id) + ">>"

        message = MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE

        message = message.format(user_route)

        conversation_engage_instances = ModelUtilities.get_model_filter(conversationEngage,
                                                                        {"card__in": dm_chatroom_instances})

        for dm_chatroom in dm_chatroom_instances:
            is_private_member = all([Members.get_community_member_state(dm_chatroom.community, dm_chatroom.user) ==
                                     member_states.MEMBER,
                                     Members.get_community_member_state(dm_chatroom.community,
                                                                        dm_chatroom.chatroom_with_user) ==
                                     member_states.MEMBER])

            if is_private_member != dm_chatroom.is_private_member:
                dm_chatroom.is_private_member = is_private_member
                dm_chatroom.save()

                update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': dm_chatroom}, {})

            card_answer_instance = card_answers(card=dm_chatroom, user=user_instance, community=community_instance,
                                                answer=message,
                                                state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_DISABLE_CHAT)

            card_answer_instance.save()

            # Update ConversationEngage
            conversation_engage_instance = conversation_engage_instances.filter(card=dm_chatroom)

            card_created_at = TimeUtilities.convert_milliseconds_to_sec(card_answer_instance.last_updated)

            conversation_engage_instance.update(last_conversation=card_answer_instance,
                                                updated_at=card_created_at)

            ModelUtilities.get_model_filter(collabcardState, {"card__in": dm_chatroom_instances})

            conversation_engage_instance.exclude(user=user_instance).update(unseen_count=F('unseen_count') + 1)

        # Create DM chatroom for all members corresponding to this CM
        user_ids_list = ModelUtilities.get_model_filter(Members,
                                                        {"community_id": community_instance,
                                                         "state__in": [member_states.MEMBER]}).values_list(
            "member_id_id", flat=True)

        for user_id in user_ids_list:
            create_member_dm_chatroom(user_id, community_id, cm_list=[member_instance.id], is_member_cm=True,
                                      is_m2cm_v2=is_m2cm_v2)


def compute_member_images_for_homescreen_celery(chatroom_instance, community_instance):
    user_list = ModelUtilities.get_model_filter(card_answers, {"card": chatroom_instance}).exclude(
        user=chatroom_instance.user).values_list("user_id", flat=True)

    member_conversations = []
    user_conversations = []

    for user_id in user_list:

        member_filter = Members.objects.filter(community_id=community_instance, member_id=user_id)

        if member_filter:
            member_instance = member_filter[0]
            member_conversations.append(member_instance)

        else:
            state_filter = collabcardState.objects.filter(card=chatroom_instance, user=user_id)

            if state_filter:
                state_instance = state_filter[0]
                user_conversations.append(state_instance)

    last_conversation_member = None
    second_last_conversation_member = None

    if len(member_conversations) > 1:
        last_conversation_member = member_conversations[0]
        second_last_conversation_member = member_conversations[1]

    elif len(member_conversations) == 1:
        last_conversation_member = member_conversations[0]

    # if last conversation creators are users(can be guest or removed members)
    last_conversation_user = None
    second_last_conversation_user = None

    if len(user_conversations) > 1:
        last_conversation_user = user_conversations[0]
        second_last_conversation_user = user_conversations[1]

    elif len(user_conversations) == 1:
        last_conversation_user = user_conversations[0]

    return last_conversation_member, second_last_conversation_member, last_conversation_user, \
           second_last_conversation_user


def initial_message_dm_chatroom(chatroom_instance, member_instance, chatroom_user, community_instance,
                                user_instances_list, answer="", user_member_state=member_states.ADMIN,
                                member_state=None, conversation_state=None):
    is_guest = False
    is_tagged = False
    ref_instance = None
    mute_status = False
    attending_status = False
    status = True

    if not member_state:
        member_state = Members.get_community_member_state(community_instance, chatroom_user)

        if not member_state:
            return

    # Create Card Answers
    if not answer:
        answer = f"This is the very beginning of your direct message with " \
                 f"<<{member_instance.userinfo.name}|route://member/{member_instance.id}>>" \
                 f" <<{chatroom_user.userinfo.name}|route://member/{chatroom_user.id}>>"

    if conversation_state is None:
        dm_card_answer = card_answers(answer=answer, card=chatroom_instance, user=member_instance,
                                      community=community_instance,
                                      state=conversation_states.CONVERSATION_HEADER)

    else:
        dm_card_answer = card_answers(answer=answer, card=chatroom_instance, user=member_instance,
                                      community=community_instance,
                                      state=conversation_state)

    dm_card_answer.save()

    # Create Conversation Engage
    for user_instance in user_instances_list:
        collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': chatroom_instance,
                                                                                    'user': user_instance})

        if not collabcard_state_filter:

            expiry_time = TimeUtilities.current_time_in_sec() + CHATROOM_EXPIRE_DURATION
            card_state_instance = collabcardState.create_chatroom_state_instance(chatroom_instance, user_instance,
                                                                                 state=collabcard_states.COLLABCARD_STATE_SEEN,
                                                                                 expire_at=expiry_time,
                                                                                 is_guest=is_guest,
                                                                                 source=ref_instance,
                                                                                 follow_status=status,
                                                                                 mute_status=mute_status,
                                                                                 is_tagged=is_tagged,
                                                                                 attending_status=attending_status
                                                                                 )
        else:
            card_state_instance = collabcard_state_filter[0]
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.follow_status = status
            card_state_instance.mute_status = mute_status
            card_state_instance.is_guest = is_guest
            card_state_instance.is_tagged = is_tagged
            card_state_instance.attending_status = attending_status
            card_state_instance.save()

        if status:
            # Create Card Engagement for Home Screen
            instance_list = ModelUtilities.get_model_filter(conversationEngage,
                                                            {'card': chatroom_instance,
                                                             'user': user_instance})

            # Update rights list in conversation engage
            rights_list = list(userMemberRights.objects.filter(user=user_instance,
                                                               community=community_instance).values_list(
                "right__state",
                flat=True))

            if not rights_list:

                if user_member_state == member_states.ADMIN:
                    rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)

                elif user_member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
                    rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)

            else:
                rights_list = json.dumps(rights_list)

            if not instance_list:
                conversationEngage.create_instance({'card_instance': chatroom_instance,
                                                    'user_instance': user_instance,
                                                    'community_instance': community_instance,
                                                    'rights_list': rights_list})

            else:
                instance = instance_list[0]
                ModelUtilities.model_update(conversationEngage, {'id': instance.id},
                                            {'last_conversation': None,
                                             'updated_at': TimeUtilities.current_time_in_sec()})

        # Update Home screen meta on chatroom follow
        last_conversation_member, second_last_conversation_member, last_conversation_user, \
        second_last_conversation_user = compute_member_images_for_homescreen_celery(chatroom_instance,
                                                                                    community_instance)

        conversation_filter = card_answers.objects.filter(card=chatroom_instance).filter(
            Q(state=conversation_states.ANSWER) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_REMOVED_OR_LEFT) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_REMOVED) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_DISABLE_CHAT) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT) |
            Q(state=conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT)).filter(
            Q(attachment_count=0) | Q(attachments_uploaded=True) | Q(api_version=1)).order_by("created_at")

        last_conversation = conversation_filter.last()

        last_seen_conversation = card_state_instance.last_seen_conversation_id

        if not last_seen_conversation:
            unseen_count = conversation_filter.count()

        else:
            unseen_count = conversation_filter.filter(id__gt=last_seen_conversation).count()

        if user_instance:
            conversationEngage.objects.filter(card=chatroom_instance,
                                              user=user_instance.id).update(
                unseen_count=unseen_count,
                last_conversation=last_conversation,
                updated_at=TimeUtilities.current_time_in_sec(),
                last_conversation_member=last_conversation_member,
                second_last_conversation_member=second_last_conversation_member,
                last_conversation_user=last_conversation_user,
                second_last_conversation_user=second_last_conversation_user,
            )

        if unseen_count > 0:
            card_state_instance.updated_at = TimeUtilities.current_time_in_sec()
            card_state_instance.save()

    return dm_card_answer


def fill_chatroom_basic_info(card_content, chatroom_name, chatroom_type, community_instance, member_instance,
                             device_id=None, request_platform=None):
    card_content['title'] = chatroom_name
    card_content['community'] = community_instance
    card_content['user'] = member_instance
    card_content['type'] = chatroom_type

    card_content['device_id'] = device_id
    card_content['platform'] = request_platform

    return card_content


@shared_task
def create_member_dm_chatroom(member_id, community_id, device_id=None, request_platform=None, is_cm_member=False,
                              cm_list=[], is_script=False, is_joining=False, is_member_cm=False, is_m2cm_v2=False):
    user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

    if not user_instance:
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    member_state = Members.get_community_member_state(community_instance, user_instance)

    chatroom_user = user_instance

    user_member_state = member_states.ADMIN

    if member_state == member_states.MEMBER:

        if not cm_list:
            # Create DM Chatroom
            list_cms = ModelUtilities.get_model_filter(Members, {"community_id": community_id,
                                                                 "state": member_states.ADMIN})

        else:
            list_cms = ModelUtilities.get_model_filter(Members, {"id__in": cm_list})

        cm_user_ids = list(list_cms.values_list("member_id_id", flat=True))

        dm_chatrooms_filter = cm_user_ids + [user_instance.id]

        dm_chatroom_instances = ModelUtilities.get_model_filter(Collabcard,
                                                                {"user_id__in": dm_chatrooms_filter,
                                                                 "chatroom_with_user_id__in": dm_chatrooms_filter,
                                                                 "community": community_instance,
                                                                 "is_private": True})

        from collabmates_api.conversation.conversation_impl import ConversationImpl

        message_template_instances = ModelUtilities.get_model_filter(
            MessageTemplate, {'community_id': community_id,
                              'chatroom_type': message_template_chatroom_types.DM_CHATROOM})

        message_template_instance = None if not len(message_template_instances) else message_template_instances[0]

        for community_manager in list_cms:
            member_instance = community_manager.member_id

            # Auto Follow DM Chatroom
            user_instances_list = [member_instance, chatroom_user]

            # Check whether DM Chatroom already exists
            dm_chatroom = dm_chatroom_instances.filter(user__in=user_instances_list,
                                                       chatroom_with_user__in=user_instances_list)

            is_private_member = all([community_manager.state == member_states.MEMBER,
                                     member_state == member_states.MEMBER])

            if dm_chatroom:
                dm_chatroom.update(is_private_member=is_private_member)

                if not is_script:

                    user_route = "<<" + str(user_instance.userinfo.name) + "|route://member/" + str(
                        user_instance.id) + ">>"

                    if is_joining:
                        answer = MEMBER_JOINING_COMMUNITY_DM_CHATROOM_MESSAGE.format(user_route)

                        conv_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT

                    elif is_cm_member:
                        answer = CM_REMOVED_COMMUNITY_DM_CHATROOM_MESSAGE.format(user_route)

                        conv_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT

                    else:

                        if is_member_cm and list_cms:
                            member_cm_instance = list_cms[0].member_id
                            user_route = "<<" + str(member_cm_instance.userinfo.name) + "|route://member/" + str(
                                member_cm_instance.id) + ">>"

                        answer = MEMBER_BECOMES_CM_DM_CHATROOM_MESSAGE.format(user_route)

                        conv_state = conversation_states.CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT

                    # Initial Message
                    initial_message_dm_chatroom(dm_chatroom[0], member_instance, chatroom_user, community_instance,
                                                user_instances_list, answer, user_member_state, member_state,
                                                conversation_state=conv_state)

                    if message_template_instance and message_template_instance.cm_id == member_instance.id:
                        ConversationImpl.create_conversation_internally(message_template_instance.cm_id,
                                                                        dm_chatroom[0].id,
                                                                        message_template_instance.message)

            else:
                card_content = {}
                chatroom_name = "Direct Message"
                chatroom_type = card_types.CARD_DIRECT_MESSAGE

                card_content['chatroom_with_user'] = chatroom_user
                card_content['is_private'] = True

                # Fill chatroom basic Info
                card_content = fill_chatroom_basic_info(card_content, chatroom_name, chatroom_type, community_instance,
                                                        member_instance, device_id, request_platform)

                # Fill chatroom epoch time
                card_content['date_epoch'] = TimeUtilities.current_time_in_sec()

                # Fill chatroom header
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True

                card_content['member_state'] = user_member_state

                chatroom_instance = Collabcard(**card_content)
                chatroom_instance.save()

                # Set initial chatroom message
                initial_message_dm_chatroom(chatroom_instance, member_instance, chatroom_user, community_instance,
                                            user_instances_list)

                if message_template_instance and message_template_instance.cm_id == member_instance.id:
                    ConversationImpl.create_conversation_internally(message_template_instance.cm_id,
                                                                    chatroom_instance.id,
                                                                    message_template_instance.message)

                if not is_script:
                    # Update All community chatrooms for user
                    ElasticSearchSync.update_chatroom.delay(chatroom_instance.id)


@shared_task
def update_unread_message_count_in_cache(chatroom_id, conversation_creator_id=0):
    """ function to update the unread message count for chatroom """

    if not chatroom_id:
        return

    validation_params = {
        'chatroom_id': chatroom_id
    }

    validated_dict = ValidationUtilities.is_valid(validation_params)

    if validated_dict.get('error_message'):
        return

    card_instance = validated_dict.get('chatroom_id')

    unread_cache_data = {}

    from collabmates_api.chatroom.chatroom_impl import ChatroomImpl

    followed_members = ChatroomImpl('', chatroom_id=chatroom_id).get_chatroom_participants_list()

    keys_list = [CONVERSATIONS_UNREAD_USER_CHATROOM_KEY % (str(user_id), str(chatroom_id))
                 for user_id in followed_members]

    users_previous_counts_dict = CacheImpl.bulk_get_cache(keys_list)

    for user_id in followed_members:
        key = CONVERSATIONS_UNREAD_USER_CHATROOM_KEY % (str(user_id), str(chatroom_id))

        if user_id == conversation_creator_id:
            previous_count = {
                'unseen_count': 0
            }

        else:
            previous_count = users_previous_counts_dict.get(key)

            if previous_count:
                unseen_count = previous_count.get('unseen_count', 0) + 1
                previous_count['unseen_count'] = unseen_count

            else:
                previous_count = {}
                engage_filter = ModelUtilities.get_model_filter(conversationEngage,
                                                                {'card': card_instance,
                                                                 'user': user_id})
                unread_count_for_user = 1

                if engage_filter.exists():
                    unread_count_for_user = engage_filter[0].unseen_count
                previous_count['unseen_count'] = unread_count_for_user

        unread_cache_data[key] = previous_count

    CacheImpl.bulk_set_cache(unread_cache_data)

    update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                   {'card__id': chatroom_id,
                                    'user_id__in': followed_members},
                                   update_dict={})

    update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                   {'preview_chatroom': card_instance,
                                    'preview_type': "chatroom"},
                                   update_dict={})


@shared_task
def reset_unread_message_count_in_cache(chatroom_id, user_id):
    """ function to update the unread message count for chatroom """

    if not chatroom_id or not user_id:
        return

    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)
    user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

    if not card_instance or not user_instance:
        return

    key = CONVERSATIONS_UNREAD_USER_CHATROOM_KEY % (str(user_id), str(chatroom_id))

    reset_count = {
        'unseen_count': 0
    }

    CacheImpl.set_cache(key, reset_count)

    update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                   {'preview_chatroom': card_instance,
                                    'preview_type': "chatroom"},
                                   update_dict={})


def fetch_conversations_unread(chatroom_id, user_id):

    if not chatroom_id or not user_id:
        info_logger.info("Chatroom ID: {} - User ID: {}".format(chatroom_id, user_id))
        return 0

    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        info_logger.info("Chatroom ID: {} - Card does not exist".format(chatroom_id))
        return 0

    user_instance = ModelUtilities.get_user_instance_or_none(user_id)

    if not user_instance:
        info_logger.info("User ID: {} - User does not exist".format(user_id))
        return 0

    unseen_count = 1

    engage_filter = ModelUtilities.get_model_filter(conversationEngage, {'card': card_instance,
                                                                         'user': user_instance})

    if engage_filter.exists():
        unseen_count = engage_filter[0].unseen_count

    return unseen_count


@shared_task
def create_chatroom_cohort_instances(chatroom_id, cohort_ids):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    bulk_chatroom_cohort = []

    chatroom_cohorts_list = list(ModelUtilities.get_model_filter(
        ChatroomCohort, {'chatroom': chatroom_instance}).values_list('cohort_id', flat=True))

    cohort_filter = ModelUtilities.get_model_filter(Cohort,
                                                    {'id__in': cohort_ids,
                                                     'community': chatroom_instance.community}
                                                    ).exclude(id__in=chatroom_cohorts_list)

    for cohort_instance in cohort_filter:
        chatroom_cohort_context = {
            'cohort_instance': cohort_instance,
            'chatroom_instance': chatroom_instance
        }

        bulk_chatroom_cohort.append(ChatroomCohort.create_bulk_instance(chatroom_cohort_context))

    if bulk_chatroom_cohort:
        ModelUtilities.bulk_create_instances(ChatroomCohort, bulk_chatroom_cohort)


@shared_task
def add_new_participants_to_cohorts_secret_chatroom(cohort_id, member_id, member_ids):
    chatroom_cohorts = ModelUtilities.get_model_filter(ChatroomCohort, {'cohort_id': cohort_id,
                                                                        'chatroom__is_secret': True})

    for chatroom_cohort in chatroom_cohorts:
        # importing locally to resolve circular import issue.
        from collabmates_api.chatroom.chatroom_impl import ChatroomImpl

        chatroom_manager = ChatroomImpl(member_id, chatroom_id=chatroom_cohort.chatroom_id)

        req_body = {
            'chatroom_id': chatroom_cohort.chatroom_id,
            'secret_chatroom_participants': member_ids,
        }

        chatroom_manager.add_secret_chatroom_participant(req_body)


@shared_task
def create_intro_room_disabled_text_for_community_members(disabled_community_settings_context_list):
    for disabled_community_settings_context in disabled_community_settings_context_list:
        community_id = disabled_community_settings_context.get('community_id')
        setting_type = disabled_community_settings_context.get('setting_type')

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            continue

        if setting_type != community_setting_types.INTRO_ROOM:
            continue

        member_states_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]

        filter_dict = {
            'community_id': community_instance,
            'state__in': member_states_list,
        }

        community_members = ModelUtilities.get_model_filter(Members, filter_dict)

        bulk_create_list = []
        bulk_update_list = []

        # Creating intro room settings text.
        for member in community_members:
            toast_filter = ModelUtilities.get_model_filter(CommunityToastV1, {'community': community_instance,
                                                                              'user': member.member_id,
                                                                              'text': INTRO_ROOM_SETTING_DISABLED_TOAST})
            if toast_filter:
                toast_instance = toast_filter[0]

                if toast_instance.is_shown:
                    toast_instance.is_shown = False
                    toast_instance.updated_at = TimeUtilities.current_time_in_milliseconds()
                    bulk_update_list.append(toast_instance)

                continue

            community_toast_v1_dict = {
                'community_instance': community_instance,
                'user_instance': member.member_id,
                'text': INTRO_ROOM_SETTING_DISABLED_TOAST,
                'is_shown': False
            }

            bulk_create_list.append(CommunityToastV1.create_instance(community_toast_v1_dict))

        ModelUtilities.bulk_create_instances(CommunityToastV1, bulk_create_list)
        ModelUtilities.bulk_update_instances(CommunityToastV1, bulk_update_list, ['is_shown', 'updated_at'])


@shared_task
def update_deferred_conversation_poll_updated_at_value(conversation_id):
    conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

    if not conversation_instance or conversation_instance.state != conversation_states.CONVERSATION_POLL:
        return

    conversation_instance.last_updated = TimeUtilities.current_time_in_milliseconds()
    conversation_instance.save()


@shared_task
def update_deferred_card_poll_updated_at_value(chatroom_id):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance or chatroom_instance.type != CollabcardTypes.CARD_POLL:
        return

    chatroom_instance.updated_at = TimeUtilities.current_time_in_milliseconds()
    chatroom_instance.save()


@shared_task
@transaction.atomic()
def convert_chatroom_to_secret_chatroom(chatroom_id):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    chatroom_participants = ModelUtilities.get_model_filter(collabcardState, {'card_id': chatroom_id,
                                                                              'follow_status': True,
                                                                              'remove': None})

    chatroom_participants_ids = list(chatroom_participants.values_list('user_id', flat=True))

    chatroom_instance.secret_chatroom_participants = json.dumps(chatroom_participants_ids)
    chatroom_instance.is_secret = True
    chatroom_instance.updated_at = TimeUtilities.current_time_in_milliseconds()
    chatroom_instance.save()

    community_manager_list = list(ModelUtilities.get_model_filter(Members, {
        'state': member_states.ADMIN,
        'community_id': chatroom_instance.community_id
    }).values_list('member_id_id', flat=True))

    user_ids_not_to_be_removed = chatroom_participants_ids + community_manager_list
    chatroom_state_list = ModelUtilities.get_model_filter(collabcardState, {'card_id': chatroom_instance})
    chatroom_state_list.filter(~Q(user_id__in=user_ids_not_to_be_removed)).delete()
    log_chatroom_secret_type_conversion_activity(chatroom_id, is_secret=True)
    update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': chatroom_instance}, {})

    from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
    ChatroomHelper.set_chatroom_conversion_type_status_key_in_cache(chatroom_id, is_converting=False)


@shared_task
@transaction.atomic()
def convert_chatroom_to_open_chatroom(chatroom_id):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    chatroom_participants = json.loads(chatroom_instance.secret_chatroom_participants)
    chatroom_instance.secret_chatroom_participants = None
    chatroom_instance.is_secret = False
    chatroom_instance.updated_at = TimeUtilities.current_time_in_milliseconds()
    chatroom_instance.save()

    community_members = ModelUtilities.get_model_filter(Members, {
        'state__in': [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE],
        'community_id': chatroom_instance.community_id
    }).select_related('member_id')

    bulk_create_instances = []

    for member in community_members:

        if member.member_id_id in chatroom_participants:
            continue

        chatroom_state_instance = collabcardState.create_chatroom_state_instances_for_bulk_create(
            chatroom_instance, member.member_id, state=collabcard_states.COLLABCARD_STATE_SEEN,
            follow_status=False, community_instance=chatroom_instance.community, external_seen=True
        )

        bulk_create_instances.append(chatroom_state_instance)

    ModelUtilities.bulk_create_instances(collabcardState, bulk_create_instances)
    log_chatroom_secret_type_conversion_activity(chatroom_id, is_secret=False)
    update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': chatroom_instance}, {})

    from collabmates_api.chatroom.chatroom_impl import ChatroomHelper
    ChatroomHelper.set_chatroom_conversion_type_status_key_in_cache(chatroom_id, is_converting=False)


@shared_task
def log_chatroom_secret_type_conversion_activity(chatroom_id, is_secret):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    ModelUtilities.update_or_create_model(ChatroomSecretTypeConversion, {
        'chatroom': chatroom_instance
    }, {
        'is_secret': False,
        'converted_at': TimeUtilities.current_time_in_milliseconds()
    })


@shared_task
def send_chatroom_creation_analytics_data(chatroom_id, user_id, event_name=None):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    if not event_name:
        event_name = "Chatroom created (Core service)"

    event_data = {
        'community_id': chatroom_instance.community.id,
        'community_name': chatroom_instance.community.name,
        'title': chatroom_instance.title,
        'has_description': True if chatroom_instance.header else False,
        'is_secret': chatroom_instance.is_secret
    }
    SegmentImpl.track_event(user_id, event_name, event_data)


@shared_task
def send_participants_added_in_chatroom_analytics_data(chatroom_id, user_id):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    chatroom_cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort, {'chatroom': chatroom_instance})

    total_participants_list = list(ModelUtilities.get_model_filter(collabcardState, {
        'card': chatroom_instance,
        'follow_status': True,
        'is_tagged': False,
        'remove': None
    }).values_list('user_id', flat=True))

    event_data = {
        'community_id': chatroom_instance.community.id,
        'community_name': chatroom_instance.community.name,
        'chatroom_id': chatroom_instance.id,
        'has_groups': True if chatroom_cohort_filter else False,
        'has_members': True if total_participants_list else False,
        'no_of_members': len(total_participants_list),
        'added_all_members': chatroom_instance.auto_follow_done,
        'added_future_members': chatroom_instance.include_members_later and chatroom_instance.auto_follow_done
    }
    SegmentImpl.track_event(user_id, "Participants added (Core service)", event_data)


@shared_task
def send_chatroom_deleted_analytics_data(chatroom_id, user_id):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    event_data = {
        'community_id': chatroom_instance.community.id,
        'community_name': chatroom_instance.community.name,
        'chatroom_id': chatroom_instance.id,
    }
    SegmentImpl.track_event(user_id, "Chatroom deleted (Core service)", event_data)


@shared_task
def send_chatroom_updated_analytics_data(chatroom_id, user_id, update_dict):
    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return

    event_data = {
        'community_id': chatroom_instance.community.id,
        'community_name': chatroom_instance.community.name,
        'chatroom_id': chatroom_instance.id,
    }
    event_data.update(update_dict)
    SegmentImpl.track_event(user_id, "Chatroom updated (Core service)", event_data)


@shared_task
def update_community_pin_chatrooms_list_in_cache(pin_info):
    chatroom_id = pin_info.get('chatroom_id')
    community_id = pin_info.get('community_id')
    pin_value = pin_info.get('pin_value')

    if not community_id:
        return []

    key = COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY.format(community_id)
    pin_chatrooms_object = CacheImpl.get_cache(key)

    if pin_chatrooms_object and chatroom_id:
        pinned_chatrooms_list = pin_chatrooms_object.get('pinned_chatrooms', [])

        if (not pin_value) and (chatroom_id in pinned_chatrooms_list):
            pinned_chatrooms_list.remove(chatroom_id)

        elif pin_value and (chatroom_id not in pinned_chatrooms_list):
            pinned_chatrooms_list = list(set(pin_chatrooms_object.get('pinned_chatrooms', []) + [chatroom_id]))
            pin_chatrooms_object['pinned_chatrooms'] = pinned_chatrooms_list

    else:
        pin_chatrooms_object = {}
        pinned_chatrooms_list = pin_info.get('pinned_chatrooms_list', [])

        if not pinned_chatrooms_list:
            pinned_chatrooms_list = list(
                set(ModelUtilities.get_model_filter(Collabcard,
                                                    {'community': community_id, 'is_pinned': True,
                                                     'is_deleted': False}).exclude(type=card_types.CARD_FEED_GROUP).
                    values_list('id', flat=True)))

        pin_chatrooms_object['pinned_chatrooms'] = pinned_chatrooms_list
    CacheImpl.set_cache(key, pin_chatrooms_object)

    return pinned_chatrooms_list


@shared_task
def update_unseen_count_based_on_cohort_access(cohort_id=None, user_id=None, community_id=None):

    if not (cohort_id or (user_id and community_id)):
        return

    user_id_list = []

    if cohort_id:
        cohort_member_filter = ModelUtilities.get_model_filter(CohortMember, {'cohort': cohort_id})

        for cohort_member_instance in cohort_member_filter:
            user_id_list.append(cohort_member_instance.user_id)
            community_id = cohort_member_instance.cohort.community_id

    else:
        user_id_list.append(user_id)

    for user_id in user_id_list:
        update_last_unseen_in_engage(user=user_id, community=community_id)


