import datetime
import csv
import gc
from django.db import transaction
from itertools import islice
from external_services.caching.cache_impl import CacheImpl
from collabmates_api.sdk.models import SdkClient
from collabmates_api.webhook.models import CommunityWebhook
from cms.models import PerDayRecordOverview, PerWeekRecordOverview, NewAnswer, userAcquition, MessageTemplate
from utility.cache_keys import CONVERSATION_COMMUNITY_PREVIEW, CONVERSATION_POLL_OPTIONS_CONVERSATION_ID, \
    CONVERSATION_POLL_VOTERS_CONVERSATION_ID, CONVERSATION_REACTIONS_CACHE_KEY, CHATROOM_REACTIONS_CACHE_KEY, \
    CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY, CHATROOM_TYPE_CONVERSION, COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY, \
    EVENT_INSTRUCTORS_CHATROOM, EVENT_HIGHLIGHTS_CHATROOM, EVENT_MEMBERTESTIMONIALS_CHATROOM, EVENT_FAQ_CHATROOM, \
    EVENT_ATTENDEES_CHATROOM, EVENT_ATTENDEES_CONVERSATION
from togther.models import Card_Attachment, EventRecordingsAttachments, ModelUtilities, Community, answerAttachment, communityToast, Members, Collabcard, collabcardState, \
    draftChatroom, deletedChatrooms, card_answers, conversationEngage, temp_admin, Community_LPIG, Community_Rank, \
    Member_Engage, Community_Legacy, Community_Profession, Community_Interest, Community_Geography, Referal, Report, \
    CollabcardStateBackup, collabcardTemp, communityQuestions, communityAnswers, communityExpire, questionFilters, \
    communityExpiryCodes, createCommunityAction, communityLevels, communityUpdate, membersEngagePilot, membersPilot, \
    memberNotificationFlag, userAdminRights, userMemberRights, moderationHistory, communityRightsSettings, blockedMembers, \
    userMemberRightsHistory, SubscriptionExpiredMembers, EventNudge, ContentDownloadSettings, Cohort, CommunitySettings, \
    CommunityToastV1, CommunityJoinEmail, CommunityGetStarted, UserEmailsSendStatus, CommunityDirectMessageSettings, \
    SDKClientUsersInfo, CommunityNotificationSettings, FeedNotificationSettings, CommunityBillingDates, CommunityConfigurations


CSV_FILENAME = "s3_url_list.csv"

def find_non_sdk_communities():
    sdk_client_community_ids = set(SdkClient.objects.values_list('community_id', flat=True))
    non_sdk_communities = Community.objects.exclude(id__in=sdk_client_community_ids).only('id').iterator()

    non_sdk_community_ids = [community.id for community in non_sdk_communities]

    print(f'non-sdk communities found: {len(non_sdk_community_ids)}, {non_sdk_community_ids}')

    return non_sdk_community_ids


def store_links_to_csv(community_id: int, batch_size=100):

    print(f'saving s3 links related to community with id: {community_id} in s3_url_list.csv')
    data = []

    # card attachment links
    collabcard_ids = ModelUtilities.get_model_filter(
        Collabcard,
        {
            'community': community_id
        }
    ).values_list('id', flat=True).iterator()

    while True:
        batch = list(islice(collabcard_ids, batch_size))
        print('preview_conversation_ids: ', batch)

        if not batch:
            break

        for collabcard_id in batch:

            card_attachment = ModelUtilities.get_model_filter(
                Card_Attachment,
                {
                    'collabcard_id': collabcard_id
                }
            ).first()

            if card_attachment:
                # print(f'community_id: {community_id} collabcard_id: {collabcard_id}', card_attachment.file_url)
                data.append({'community_id': community_id, 'collabcard_id': collabcard_id, 'url': card_attachment.file_url})

            # events recordings attachments
            event_recordings_attachments = ModelUtilities.get_model_filter(
                EventRecordingsAttachments,
                {
                    'chatroom_id': collabcard_id
                }
            ).values_list('url', 'thumbnail_url')


            if event_recordings_attachments:

                for attachment in event_recordings_attachments:
                    url, thumbnail_url = attachment  # Unpack the tuple into variables

                    if url:
                        # print(f'community_id: {community_id} collabcard_id: {collabcard_id} url: {url}')
                        data.append({'community_id': community_id, 'collabcard_id': collabcard_id,'url': url})

                    if thumbnail_url:
                        # print(f'community_id: {community_id} collabcard_id: {collabcard_id} thumbnail_url: {thumbnail_url}')
                        data.append({'community_id': community_id, 'collabcard_id': collabcard_id, 'url': thumbnail_url})

    # answer attachment links
    card_answers_ids: list = ModelUtilities.get_model_filter(
        card_answers,
        {
            'community': community_id
        }
    ).values_list('id', flat=True).iterator()

    while True:
        batch = list(islice(card_answers_ids, batch_size))

        if not batch:
            break

        for card_answers_id in batch:

            answer_attachment = ModelUtilities.get_model_filter(
                answerAttachment,
                {
                    'answer_id': card_answers_id
                }
            ).first()

            if answer_attachment:
                # print(f'community_id: {community_id} card_answers_id: {card_answers_id}', answer_attachment.file_url)
                data.append({'community_id': community_id, 'card_answers_id': card_answers_id, 'url': answer_attachment.file_url})

    # print('csv input: ', data)
    fields = ['community_id', 'collabcard_id', 'card_answers_id', 'url']
    filename = CSV_FILENAME

    with open(filename, 'a') as csvfile:
        # creating a csv dict writer object
        writer = csv.DictWriter(csvfile, fieldnames=fields)

         # If the file is empty, write headers (field names)
        if csvfile.tell() == 0:
            writer.writeheader()

        # writing data rows
        writer.writerows(data)



def delete_table_rows_in_batches(community_id: int, match_string, model, batch_size=500):
    rows_count_before_delete = model.objects.count()

    # Get all rows to delete in batches
    rows_to_delete = ModelUtilities.get_model_filter(
        model,
        {
            match_string: community_id
        }
    ).iterator()

    total_deleted = 0

    with transaction.atomic():
        while True:
            batch = list(islice(rows_to_delete, batch_size))
            if not batch:
                break
            model.objects.filter(pk__in=[obj.pk for obj in batch]).delete()
            total_deleted += len(batch)

            # Explicitly run garbage collection to free up memory
            # gc.collect()

    rows_count_after_delete = model.objects.count()

    if (rows_count_before_delete - total_deleted) != rows_count_after_delete:
        raise Exception(f"Delete operation for {model._meta.db_table} FAILED")

    print(f"{model._meta.db_table} : {total_deleted} rows deleted, {rows_count_after_delete} rows remaining, PASSED")



def delete_community_cache_in_batches(community_id: int, batch_size=100) -> None:

    print(f'deleting cache keys for community_id : {community_id} ...')

    # preview cache
    community_preview_conversation_ids: list = ModelUtilities.get_model_filter(
        card_answers,
        {
            'preview_community': community_id
        }
    ).values_list('id', flat=True).iterator()

    while True:
        batch = list(islice(community_preview_conversation_ids, batch_size))
        print('preview_conversation_ids: ', batch)

        if not batch:
            break

        for community_preview_conversation_id in batch:
            community_preview_cache_key: str = CONVERSATION_COMMUNITY_PREVIEW % (str(community_preview_conversation_id), str(community_id))
            cache_key_delete_status: bool = CacheImpl.delete_key(community_preview_cache_key)
            print(f'deleting key: {community_preview_cache_key}, status: {cache_key_delete_status}')


    # conversation cache
    conversation_ids = ModelUtilities.get_model_filter(
        card_answers,
        {
            'community': community_id
        }
    ).values_list('id', flat=True).iterator()

    while True:
        batch = list(islice(conversation_ids, batch_size))
        print('conversation_ids: ', batch)

        if not batch:
            break

        for conversation_id in batch:
            poll_options_cache_key: str = CONVERSATION_POLL_OPTIONS_CONVERSATION_ID % str(conversation_id)
            poll_options_cache_key_delete_status: bool = CacheImpl.delete_key(poll_options_cache_key)
            print(f'deleting cache key: {poll_options_cache_key}, status: {poll_options_cache_key_delete_status}')

            poll_voters_cache_key: str = CONVERSATION_POLL_VOTERS_CONVERSATION_ID % str(conversation_id)
            poll_voters_cache_key_delete_status: bool = CacheImpl.delete_key(poll_voters_cache_key)
            print(f'deleting cache key: {poll_voters_cache_key}, status: {poll_voters_cache_key_delete_status}')

            reaction_cache_key: str = CONVERSATION_REACTIONS_CACHE_KEY % str(conversation_id)
            reaction_cache_key_delete_status: bool = CacheImpl.delete_key(reaction_cache_key)
            print(f'deleting cache key: {reaction_cache_key}, status: {reaction_cache_key_delete_status}')

            conversation_event_attendees_cache_key = EVENT_ATTENDEES_CONVERSATION % str(conversation_id)
            conversation_event_attendees_cache_key_delete_status: bool = CacheImpl.delete_key(conversation_event_attendees_cache_key)
            print(f'deleting cache key: {conversation_event_attendees_cache_key}, status: {conversation_event_attendees_cache_key_delete_status}')


    # chatroom cache
    chatroom_ids = ModelUtilities.get_model_filter(
        Collabcard,
        {
            'community': community_id
        }
    ).values_list('id', flat=True).iterator()

    while True:
        batch = list(islice(chatroom_ids, batch_size))
        print('chatroom_ids: ', batch)

        if not batch:
            break

        for chatroom_id in batch:
            chatroom_reactions_cache_key: str = CHATROOM_REACTIONS_CACHE_KEY % str(chatroom_id)
            chatroom_reactions_cache_key_delete_status: bool = CacheImpl.delete_key(chatroom_reactions_cache_key)
            print(f'deleting cache key: {chatroom_reactions_cache_key}, status: {chatroom_reactions_cache_key_delete_status}')

            chatroom_participants_cache_key: str = CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY.format(chatroom_id)
            chatroom_participants_cache_key_delete_status: bool = CacheImpl.delete_key(chatroom_participants_cache_key)
            print(f'deleting cache key: {chatroom_participants_cache_key}, status: {chatroom_participants_cache_key_delete_status}')

            chatroom_type_conversion_cache_key: str = CHATROOM_TYPE_CONVERSION.format(chatroom_id)
            chatroom_type_conversion_cache_key_delete_status: bool = CacheImpl.delete_key(chatroom_type_conversion_cache_key)
            print(f'deleting cache key: {chatroom_type_conversion_cache_key}, status: {chatroom_type_conversion_cache_key_delete_status}')

            chatroom_list_cache_key: str = COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY.format(community_id)
            chatroom_list_cache_key_delete_status: bool = CacheImpl.delete_key(chatroom_list_cache_key)
            print(f'deleting cache key: {chatroom_list_cache_key}, status: {chatroom_list_cache_key_delete_status}')

            event_instructors_cache_key = EVENT_INSTRUCTORS_CHATROOM % str(chatroom_id)
            event_instructors_cache_key_delete_status: bool = CacheImpl.delete_key(event_instructors_cache_key)
            print(f'deleting cache key: {event_instructors_cache_key}, status: {event_instructors_cache_key_delete_status}')

            event_highlights_cache_key = EVENT_HIGHLIGHTS_CHATROOM % str(chatroom_id)
            event_highlights_cache_key_delete_status: bool = CacheImpl.delete_key(event_highlights_cache_key)
            print(f'deleting cache key: {event_highlights_cache_key}, status: {event_highlights_cache_key_delete_status}')

            event_membertestimonials_cache_key = EVENT_MEMBERTESTIMONIALS_CHATROOM % str(chatroom_id)
            event_membertestimonials_cache_key_delete_status: bool = CacheImpl.delete_key(event_membertestimonials_cache_key)
            print(f'deleting cache key: {event_membertestimonials_cache_key}, status: {event_membertestimonials_cache_key_delete_status}')

            event_faq_cache_key = EVENT_FAQ_CHATROOM % str(chatroom_id)
            event_faq_cache_key_delete_status: bool = CacheImpl.delete_key(event_faq_cache_key)
            print(f'deleting cache key: {event_faq_cache_key}, status: {event_faq_cache_key_delete_status}')

            event_attendees_cache_key = EVENT_ATTENDEES_CHATROOM % str(chatroom_id)
            event_attendees_cache_key_delete_status: bool = CacheImpl.delete_key(event_attendees_cache_key)
            print(f'deleting cache key: {event_attendees_cache_key}, status: {event_attendees_cache_key_delete_status}')

    print(f'deleted cache keys for community_id : {community_id} ...')



def delete_community(community_id: int):

    # store s3 links to a csv file
    store_links_to_csv(community_id)
    print(f'Upload the file: {CSV_FILENAME} to s3')

    # start delete operation
    print(f'starting delete operation for community with id : {community_id} at {datetime.datetime.now()}')

    # delete cache keys
    delete_community_cache_in_batches(community_id)

    # delete all tables
    delete_table_rows_in_batches(community_id, 'community_id', communityToast)
    delete_table_rows_in_batches(community_id, 'community_id_id', Members)
    delete_table_rows_in_batches(community_id, 'community_id', Collabcard)
    delete_table_rows_in_batches(community_id, 'community_id', collabcardState)
    delete_table_rows_in_batches(community_id, 'community_id', draftChatroom)
    delete_table_rows_in_batches(community_id, 'community_id', deletedChatrooms)
    delete_table_rows_in_batches(community_id, 'community_id', conversationEngage)
    delete_table_rows_in_batches(community_id, 'community_id', temp_admin)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_LPIG)
    delete_table_rows_in_batches(community_id, 'community_id_id', Member_Engage)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_Rank)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_Legacy)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_Profession)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_Interest)
    delete_table_rows_in_batches(community_id, 'community_id_id', Community_Geography)
    delete_table_rows_in_batches(community_id, 'community_id', Referal)
    delete_table_rows_in_batches(community_id, 'community_id', Report)
    delete_table_rows_in_batches(community_id, 'community_id', CollabcardStateBackup)
    delete_table_rows_in_batches(community_id, 'community_id', collabcardTemp)
    delete_table_rows_in_batches(community_id, 'community_id', communityQuestions)
    delete_table_rows_in_batches(community_id, 'community_id', communityAnswers)
    delete_table_rows_in_batches(community_id, 'community_id', communityExpire)
    delete_table_rows_in_batches(community_id, 'community_id', questionFilters)
    delete_table_rows_in_batches(community_id, 'community_id', communityExpiryCodes)
    delete_table_rows_in_batches(community_id, 'community_id', createCommunityAction)
    delete_table_rows_in_batches(community_id, 'community_id', communityLevels)
    delete_table_rows_in_batches(community_id, 'community_id', communityUpdate)
    delete_table_rows_in_batches(community_id, 'community_id', membersEngagePilot)
    delete_table_rows_in_batches(community_id, 'community_id_id', membersPilot)
    delete_table_rows_in_batches(community_id, 'community_id', memberNotificationFlag)
    delete_table_rows_in_batches(community_id, 'community_id', userAdminRights)
    delete_table_rows_in_batches(community_id, 'community_id', userMemberRights)
    delete_table_rows_in_batches(community_id, 'community_id', moderationHistory)
    delete_table_rows_in_batches(community_id, 'community_id', communityRightsSettings)
    delete_table_rows_in_batches(community_id, 'community_id', blockedMembers)
    delete_table_rows_in_batches(community_id, 'community_id', userMemberRightsHistory)
    delete_table_rows_in_batches(community_id, 'community_id', SubscriptionExpiredMembers)
    delete_table_rows_in_batches(community_id, 'community_id', EventNudge)
    delete_table_rows_in_batches(community_id, 'community_id_id', ContentDownloadSettings)
    delete_table_rows_in_batches(community_id, 'community_id', Cohort)
    delete_table_rows_in_batches(community_id, 'community_id', CommunitySettings)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityToastV1)
    delete_table_rows_in_batches(community_id, 'community_id_id', CommunityJoinEmail)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityGetStarted)
    delete_table_rows_in_batches(community_id, 'community_id', UserEmailsSendStatus)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityDirectMessageSettings)
    delete_table_rows_in_batches(community_id, 'community_id', SDKClientUsersInfo)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityNotificationSettings)
    delete_table_rows_in_batches(community_id, 'community_id', FeedNotificationSettings)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityBillingDates)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityConfigurations)
    delete_table_rows_in_batches(community_id, 'community_id', CommunityWebhook)
    delete_table_rows_in_batches(community_id, 'community_id', PerDayRecordOverview)
    delete_table_rows_in_batches(community_id, 'community_id', PerWeekRecordOverview)
    delete_table_rows_in_batches(community_id, 'community_id', NewAnswer)
    delete_table_rows_in_batches(community_id, 'community_id', userAcquition)
    delete_table_rows_in_batches(community_id, 'community_id', MessageTemplate)
    ModelUtilities.get_model_filter(
        Community,
        {
            'id': community_id
        }
    ).delete()

    gc.collect()
    print(f'community with id : {community_id} deleted along with related data at {datetime.datetime.now()}.')



def run(batch_size):
    communities_to_delete = find_non_sdk_communities()

    start_time = datetime.datetime.now()  # Record start time

    for i, community_id in enumerate(communities_to_delete):
        if i >= batch_size:
            break
        delete_community(community_id)

    end_time = datetime.datetime.now()  # Record end time
    print("Total time taken by script: ", end_time - start_time)
