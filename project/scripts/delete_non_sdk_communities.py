import datetime
import csv
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
    # Get a list of community IDs present in the SdkClient model
    sdk_client_community_ids = SdkClient.objects.values_list('community_id', flat=True)

    total_communities_count = len(Community.objects.values_list('id', flat=True))
    
    # Exclude communities whose IDs match any community_id in SdkClient
    non_sdk_communities = list(set(Community.objects.exclude(id__in=sdk_client_community_ids)))
    
    non_sdk_communities_count = len(non_sdk_communities)

    communities_left_after_delete = total_communities_count - non_sdk_communities_count
    
    print(f'non-sdk communities found: {non_sdk_communities_count}')
    print(f'communitites that should be left in togther_community table after delete operation: {communities_left_after_delete}')
    
    return non_sdk_communities


def store_links_to_csv(community_id):

    print(f'saving s3 links related to community with id: {community_id} in s3_url_list.csv')
    data = []
    
    # card attachment links
    collabcard_ids = ModelUtilities.get_model_filter(
        Collabcard,
        {
            'community': community_id
        }
    ).values_list(
        'id',
        flat=True
    )

    for collabcard_id in collabcard_ids:

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
    ).values_list(
        'id',
        flat=True
    )

    for card_answers_id in card_answers_ids:

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



def delete_table_rows(community_id: int, match_string, model):
    
    rows_count_before_delete = model.objects.count()
    
    rows_to_delete = ModelUtilities.get_model_filter(
        model,
        {
            match_string: community_id
        }
    )

    rows_to_delete_count = rows_to_delete.count()
    
    rows_to_delete.delete()

    rows_count_after_delete = model.objects.count()
    
    if (rows_count_before_delete - rows_to_delete_count) != rows_count_after_delete:
        raise Exception(f'delete operation for {model._meta.db_table} FAILED')

    print(f'{model._meta.db_table} : {rows_to_delete_count} rows deleted, {rows_count_after_delete} rows remaining, PASSED')



def delete_community_cache(community_id: int) -> None:

    print(f'deleting cache keys for community_id : {community_id} ...')
    
    # preview cache
    community_preview_conversation_ids: list = ModelUtilities.get_model_filter(
        card_answers,
        {
            'preview_community': community_id
        }
    ).values_list(
        'id',
        flat=True
    )
    print('preview_conversation_ids: ', list(community_preview_conversation_ids))

    for community_preview_conversation_id in community_preview_conversation_ids:
        community_preview_cache_key: str = CONVERSATION_COMMUNITY_PREVIEW % (str(community_preview_conversation_id), str(community_id))
        cache_key_delete_status: bool = CacheImpl.delete_key(community_preview_cache_key)
        print(f'deleting key: {community_preview_cache_key}, status: {cache_key_delete_status}')


    # conversation cache
    conversation_ids = ModelUtilities.get_model_filter(
        card_answers,
        {
            'community': community_id
        }
    ).values_list(
        'id',
        flat=True
    )
    print('conversation_ids: ', list(conversation_ids))
    
    for conversation_id in conversation_ids:
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
    ).values_list(
        'id',
        flat=True
    )
    print('chatroom_ids: ', list(chatroom_ids))

    for chatroom_id in chatroom_ids:
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
    delete_community_cache(community_id)
    # delete all tables
    delete_table_rows(community_id, 'community_id', communityToast)
    delete_table_rows(community_id, 'community_id_id', Members)
    delete_table_rows(community_id, 'community_id', Collabcard)
    delete_table_rows(community_id, 'community_id', collabcardState)
    delete_table_rows(community_id, 'community_id', draftChatroom)
    delete_table_rows(community_id, 'community_id', deletedChatrooms)
    delete_table_rows(community_id, 'community_id', conversationEngage)
    delete_table_rows(community_id, 'community_id', temp_admin)
    delete_table_rows(community_id, 'community_id_id', Community_LPIG)
    delete_table_rows(community_id, 'community_id_id', Member_Engage)
    delete_table_rows(community_id, 'community_id_id', Community_Rank)
    delete_table_rows(community_id, 'community_id_id', Community_Legacy)
    delete_table_rows(community_id, 'community_id_id', Community_Profession)
    delete_table_rows(community_id, 'community_id_id', Community_Interest)
    delete_table_rows(community_id, 'community_id_id', Community_Geography)
    delete_table_rows(community_id, 'community_id', Referal)
    delete_table_rows(community_id, 'community_id', Report)
    delete_table_rows(community_id, 'community_id', CollabcardStateBackup)
    delete_table_rows(community_id, 'community_id', collabcardTemp)
    delete_table_rows(community_id, 'community_id', communityQuestions)
    delete_table_rows(community_id, 'community_id', communityAnswers)
    delete_table_rows(community_id, 'community_id', communityExpire)
    delete_table_rows(community_id, 'community_id', questionFilters)
    delete_table_rows(community_id, 'community_id', communityExpiryCodes)
    delete_table_rows(community_id, 'community_id', createCommunityAction)
    delete_table_rows(community_id, 'community_id', communityLevels)
    delete_table_rows(community_id, 'community_id', communityUpdate)
    delete_table_rows(community_id, 'community_id', membersEngagePilot)
    delete_table_rows(community_id, 'community_id_id', membersPilot)
    delete_table_rows(community_id, 'community_id', memberNotificationFlag)
    delete_table_rows(community_id, 'community_id', userAdminRights)
    delete_table_rows(community_id, 'community_id', userMemberRights)
    delete_table_rows(community_id, 'community_id', moderationHistory)
    delete_table_rows(community_id, 'community_id', communityRightsSettings)
    delete_table_rows(community_id, 'community_id', blockedMembers)
    delete_table_rows(community_id, 'community_id', userMemberRightsHistory)
    delete_table_rows(community_id, 'community_id', SubscriptionExpiredMembers)
    delete_table_rows(community_id, 'community_id', EventNudge)
    delete_table_rows(community_id, 'community_id_id', ContentDownloadSettings)
    delete_table_rows(community_id, 'community_id', Cohort)
    delete_table_rows(community_id, 'community_id', CommunitySettings)
    delete_table_rows(community_id, 'community_id', CommunityToastV1)
    delete_table_rows(community_id, 'community_id_id', CommunityJoinEmail)
    delete_table_rows(community_id, 'community_id', CommunityGetStarted)
    delete_table_rows(community_id, 'community_id', UserEmailsSendStatus)
    delete_table_rows(community_id, 'community_id', CommunityDirectMessageSettings)
    delete_table_rows(community_id, 'community_id', SDKClientUsersInfo)
    delete_table_rows(community_id, 'community_id', CommunityNotificationSettings)
    delete_table_rows(community_id, 'community_id', FeedNotificationSettings)
    delete_table_rows(community_id, 'community_id', CommunityBillingDates)
    delete_table_rows(community_id, 'community_id', CommunityConfigurations)
    delete_table_rows(community_id, 'community_id', CommunityWebhook)
    delete_table_rows(community_id, 'community_id', PerDayRecordOverview)
    delete_table_rows(community_id, 'community_id', PerWeekRecordOverview)
    delete_table_rows(community_id, 'community_id', NewAnswer)
    delete_table_rows(community_id, 'community_id', userAcquition)
    delete_table_rows(community_id, 'community_id', MessageTemplate)
    delete_table_rows(community_id, 'id', Community)
    print(f'community with id : {community_id} deleted along with related data at {datetime.datetime.now()}.')



def run():
    communities_to_delete = find_non_sdk_communities()

    start_time = datetime.datetime.now()  # Record start time

    for community in communities_to_delete:
        delete_community(community.id)

    end_time = datetime.datetime.now()  # Record end time
    print("Total time taken by script: ", end_time - start_time)