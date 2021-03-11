from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings

from collabmates_api.serializers import get_user_profile, get_preview_for_url
from collabmates_api.static_text import CHATROOM_PREVIW_CACHE_KEY
from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import *
import time
from django.db.models import Q
import json

from utility.constants import CONVERSATIONS_COUNT_CACHE_KEY, CONVERSATIONS_DISTINCT_CREATORS_KEY
from utility.states import card_types, chatroom_states

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


@shared_task
def save_community_purpose_card(community_id, card_id):
    time.sleep(2)
    community = Community.objects.get(id=community_id)
    community.purpose_collabcard = card_id
    community.save()


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
        update_last_unseen_in_engage(user=member.member_id.id, community=community_id, is_seen=is_seen)


def update_last_unseen_in_engage(user='', community='', is_seen=False):
    '''function to update the unseen  collabcard in engage'''

    total_chatrooms = collabcardState.objects.filter(community=community, user=user,
                                                     card__is_deleted=False).exclude(card__type=1).distinct(
        'card_id').count()
    seen_chatrooms = collabcardState.objects.filter(community=community, user=user, external_seen=True,
                                                    card__is_deleted=False).exclude(card__type=1).distinct(
        'card').count()

    diff = total_chatrooms - seen_chatrooms

    unseen_count = 0
    if diff <= 0:
        unseen_count = 0

    else:
        unseen_count = diff

    if not is_seen:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(last_unseen_count=unseen_count,
                                                                                    updated_at=time.time())

    else:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(
            last_unseen_count=unseen_count,
            updated_at=time.time()
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


def get_new_chatroom_members(member_id, community_id):
    """ to get the member objects for new chatrooms created """

    last_instance = collabcardState.objects.filter(user=member_id, community=community_id,
                                                   card__is_deleted=False).filter(~Q(state=0)).last()

    if last_instance:
        last_card = last_instance.card
        unseen_chatrooms = Collabcard.objects.filter(community=community_id, id__gt=last_card.id).distinct('user_id')

    else:
        unseen_chatrooms = Collabcard.objects.filter(community=community_id).distinct('user_id')

    member_list = []
    for card in unseen_chatrooms:

        member_filter = Members.objects.filter(member_id=card.user, community_id=community_id)
        image_url = card.user.userinfo.image_link if card.user.userinfo.image_link else ''
        exists = member_filter.exists()

        if exists:
            member_instance = member_filter[0]

            if member_instance.image_url:
                image_url = member_instance.image_url

        member = get_user_profile(card.user.id, community_id, send_profile=False)
        member['image_url'] = image_url
        member_list.append(member)

        if len(member_list) > 3:
            break

    return member_list


def fetch_new_chatroom_creater_images(member_id, community_id):
    unseen_chatrooms = collabcardState.objects.filter(user=member_id, community_id=community_id,
                                                      external_seen=False,
                                                      card__is_deleted=False).exclude(card__type=1).distinct('card')

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

    for user in user_list:

        has_seen = conversationMemberState.objects.filter(card_id=chatroom_id, user_id=user)

        if has_seen.exists():
            seen_id = has_seen[0].conversation.id
            unseen_count = card_answers.objects.filter(card_id=chatroom_id, state=0, id__gt=seen_id).count()
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

            update_preview_of_chatroom_in_cache({'chatroom_id': conversation.preview_chatroom.id,
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

        if intro_filter.exists():
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
    ModelUtilities.model_update(Collabcard, {'id': card_id}, {'pinned': False})


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
        previous_count['conversations_count'] = previous_count['conversations_count'] + 1

    else:

        conversations_count = count_info.get('conversations_count')

        if not conversations_count:
            conversations_count = ModelUtilities.get_model_filter(card_answers,
                                                                  {'card': chatroom_id,
                                                                   'state': chatroom_states.ANSWER}).filter(
                Q(attachment_count=0)
                | Q(attachments_uploaded=True)).count()

        CacheImpl.set_cache(key, {'total_responses_count': conversations_count})


def update_chatroom_conversation_creators_in_cache(conversation_creator_info):
    chatroom_id = conversation_creator_info.get('chatroom_id')

    if not chatroom_id:
        return

    key = CONVERSATIONS_DISTINCT_CREATORS_KEY % str(chatroom_id)
    conversation_creator_dict = CacheImpl.get_cache(key)

    if conversation_creator_dict:
        user_id = conversation_creator_info.get('user_id')

        if not user_id:
            return

        conversation_creator_list = conversation_creator_dict['conversation_creator_list']

        list_len = len(conversation_creator_list)

        if list_len and (user_id not in conversation_creator_list):

            if list_len == 5:
                conversation_creator_list.pop(0)

            conversation_creator_list.append(user_id)

    else:

        conversation_creator_list = conversation_creator_info.get('conversation_creator_list')

        if not conversation_creator_list:
            conversation_creator_list = []
            conversation_filter = card_answers.objects \
                                      .filter(card=chatroom_id, state=chatroom_states.ANSWER) \
                                      .filter(Q(attachment_count=0) |
                                              Q(attachments_uploaded=True)) \
                                      .distinct('user') \
                                      .order_by('user', '-id')[:5]

            for data in conversation_filter:
                user_id = data.user.id
                conversation_creator_list.append(user_id)

        if conversation_creator_list:
            conversation_creator_dict['conversation_creator_list'] = conversation_creator_list
            CacheImpl.set_cache(key, conversation_creator_dict)
