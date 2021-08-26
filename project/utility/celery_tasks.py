from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings

from external_services.webflow.webflow_impl import WebflowImpl
from utility.string_utilities import StringUtilities
from utility.api_client import ApiClient
from collabmates_api.serializers import get_user_profile, get_preview_for_url, UserinfoSerializer
from collabmates_api.static_text import CHATROOM_PREVIW_CACHE_KEY
from collabmates_api.community.constants import *
from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from external_services.segment.segment_impl import SegmentImpl
from utility.routes import CHATROOM_LINK
from togther.models import *
import time
from django.db.models import Q
import json

from utility.cache_keys import CONVERSATION_POLL_OPTIONS_CONVERSATION_ID, CONVERSATION_POLL_VOTERS_CONVERSATION_ID, \
    CONVERSATION_COMMUNITY_PREVIEW, USER_MUTED_CHATROOM, EVENT_INSTRUCTORS_CHATROOM, EVENT_HIGHLIGHTS_CHATROOM, \
    EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_FAQ_CHATROOM, EVENT_ATTENDEES_CHATROOM
from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY, \
    SUBSCRIPTION_FETCH_EVENT_PLAN, COMMUNITY_PUBLIC_URL
from utility.firebase import update_my_chatrooms_on_homefeed_in_firebase
from utility.number_utilities import NumberUtilities
from utility.states import card_types, conversation_poll_types, conversation_states, community_level_states, \
    level_click_states, event_access, event_webflow_update_types

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
                collabcard_state_instance.expiry_time = None
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
        card__attachments_uploaded=True)).exclude(card__type=1).distinct('card_id').count()

    seen_chatrooms = collabcardState.objects.filter(community=community,
                                                    user=user, external_seen=True, card__is_deleted=False,
                                                    card__is_pending=False,
                                                    secret_chatroom_left=False).filter(Q(card__attachment_count=0)
                                                                                       | Q(
        card__attachments_uploaded=True)).exclude(card__type=1).distinct('card').count()

    diff = total_chatrooms - seen_chatrooms

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


def compute_conversation_polls_from_cache(poll_options, poll_voters, member_id, conversation_context):
    total_votes = poll_voters.get('total_votes', 0)
    total_user_set = poll_voters.get('total_user_set')
    chatroom_poll_members = poll_voters.get('conversation_poll_members', {})

    polls = []

    multi_select = conversation_context.get('multiple_select_no', None)
    poll_type = conversation_context.get('poll_type', 0)
    expiry_time = conversation_context.get('expiry_time', 0)

    for data in poll_options:

        poll_id = data['id']
        temp = dict()
        temp['id'] = data['id']
        temp['text'] = data['text']
        temp['is_selected'] = False

        if total_votes == 0:
            temp['no_votes'] = 0
            temp['percentage'] = 0
            polls.append(temp)
            continue

        if data.get('member'):
            temp['member'] = data.get('member')

        chatroom_votes = chatroom_poll_members.get(poll_id)

        if not chatroom_votes:
            chatroom_votes = []

        temp['is_selected'] = member_id in chatroom_votes
        count = len(chatroom_votes)

        if multi_select:
            total_votes = len(total_user_set)

        temp['no_votes'] = count

        temp['percentage'] = int((count / total_votes) * 100)

        if poll_type == conversation_poll_types.DEFERRED and \
                expiry_time >= TimeUtilities.current_time_in_milliseconds():
            del temp['no_votes']
            del temp['percentage']

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

        if conversation_info.get('poll_type') == conversation_poll_types.DEFERRED and \
                conversation_info.get('expiry_time') >= TimeUtilities.current_time_in_milliseconds():
            del temp['no_votes']
            del temp['percentage']

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

        if total_votes == 0:
            temp['no_votes'] = 0
            temp['percentage'] = 0
            polls.append(temp)
            continue

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

        temp['no_votes'] = count

        temp['percentage'] = int((count / total_votes) * 100)

        if conversation_instance.poll_type == conversation_poll_types.DEFERRED and \
                conversation_instance.expiry_time >= TimeUtilities.current_time_in_milliseconds():
            del temp['no_votes']
            del temp['percentage']

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
def save_users_with_muted_chatrooms(mute_info):
    user_id = mute_info.get('user_id')
    chatroom_id = mute_info.get('chatroom_id')
    mute_status = mute_info.get('mute_status')

    if not user_id:
        return

    key = USER_MUTED_CHATROOM % str(user_id)

    muted_key = CacheImpl.get_cache(key)

    if muted_key and chatroom_id:
        mute_list = muted_key.get('mute_list', [])

        if mute_status and \
                chatroom_id not in mute_list:
            mute_list.append(chatroom_id)

        elif not mute_status and \
                chatroom_id in mute_list:

            mute_list.remove(chatroom_id)

        CacheImpl.set_cache(key, {'mute_list': mute_list})

        return

    mute_list = mute_info.get('mute_list', [])

    if not mute_list:
        mute_list = list(collabcardState.objects.filter(user=user_id,
                                                        mute_status=True).values_list('card_id',
                                                                                      flat=True))

    CacheImpl.set_cache(key, {'mute_list': mute_list})


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

        is_user_present = user_id in event_attendees_list

        if not status and is_user_present:
            event_attendees_list.remove(user_id)

        if status and not is_user_present:

            if len(event_attendees_list) == 10:
                event_attendees_list.pop(0)

            event_attendees_list.append(user_id)

        CacheImpl.set_cache(EVENT_ATTENDEES_CHATROOM % str(card_instance.id), {
            'event_attendees_list': event_attendees_list
        })

        return

    event_attendees_list = attendees_info.get('event_attendees_list', [])

    if not event_attendees_list:
        event_attendees_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                                    {'card': card_instance,
                                                                     'attending_status': True}
                                                                    ).values_list('user', flat=True).
                                    order_by('created_at', 'id')[:10])

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
    cost_list = [data.get('cost') / 100 for data in response.get('event_plans', [])]

    return cost_list


def compute_event_metadata_for_analytics(card_instance, community_instance):
    cost_list = get_event_pricing(card_instance.id)

    if not cost_list:
        return

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
    SegmentImpl.track_event(user_id, "Event registered(Core Service)", event_metadata)


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

    task_begin_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_begin_epoch_time)
    task_expiry_date_time = TimeUtilities.convert_epoch_to_datetime_in_IST(task_expiry_epoch_time)
    send_analytics_on_event_reminders.apply_async(args=args, kwargs={},
                                                  eta=task_begin_date_time,
                                                  expires=task_expiry_date_time)


def create_event_request_meta_for_webflow_create(card_instance, community_instance):

    event_meta = {
        'fields': {
            'name': card_instance.header,
            'title': card_instance.title,
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


@shared_task
def create_event_in_webflow_service(card_id):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

    if not card_instance:
        return

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
        'event_web_page': event_meta.get('slug'),
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
        i = i+1

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
            break

        if data.type == 'video':
            fields['banner-video'] = data.file_url
            break

    return {'fields': fields}


def create_update_request_meta_of_webflow_for_event_meta(update_info):
    card_instance = update_info.get('card_instance')

    event_meta = {
        'fields': {
            'name': card_instance.header,
            'title': card_instance.title,
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

    if not event_meta.get('fields'):
        return

    ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                {'updated_at': TimeUtilities.current_time_in_sec()})
