from celery import shared_task

from collabmates_api.sync.model_update import update_models_for_syncing_apis
from external_services.caching.cache_impl import CacheImpl
from togther.models import Members, MessageReactions, card_answers, Collabcard, Userinfo
from utility.cache_keys import CONVERSATION_REACTIONS_CACHE_KEY, CHATROOM_REACTIONS_CACHE_KEY
from utility.states import SyncTypes

from togther.models import ModelUtilities
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


@shared_task
def update_chatroom_or_conversation_reactions_in_cache(chatroom_id=None, conversation_id=None,
                                                       member_profiles=None):
    """ function to update the preview of chatroom """

    if not conversation_id and not chatroom_id:
        return

    if conversation_id:
        key = CONVERSATION_REACTIONS_CACHE_KEY % str(conversation_id)

    else:
        key = CHATROOM_REACTIONS_CACHE_KEY % str(chatroom_id)

    if member_profiles is None:
        member_profiles = fetch_chatroom_or_conversation_reactions(chatroom_id, conversation_id)

    CacheImpl.set_cache(key, member_profiles)

    if conversation_id:
        update_models_for_syncing_apis(SyncTypes.CONVERSATION,
                                       {'id': conversation_id},
                                       {})
    else:
        update_models_for_syncing_apis(SyncTypes.CHATROOM,
                                       {'card__id': chatroom_id,
                                        'secret_chatroom_left': False},
                                       update_dict={})


def get_process_members_data_for_reactions(community, members_id_list):
    reacted_members_data = Members.objects\
        .filter(community_id=community,
                member_id__id__in=members_id_list)\
        .select_related('member_id__userinfo')

    members_data_list = {}

    for data in reacted_members_data:

        temp = {
            data.member_id_id: data.image_url
        }

        members_data_list.update(temp)

    return members_data_list


def get_members_profiles_for_reactions(community, members_id_list, reactions_map):

    members_profile_list = []

    members_data_list = get_process_members_data_for_reactions(community, members_id_list)

    member_profiles = Userinfo.objects.filter(user_id__id__in=members_id_list)

    from ..raw_queries import (get_users_sdk_meta_dict)

    users_meta = get_users_sdk_meta_dict(members_id_list)

    for profile in member_profiles:
        user_id = profile.user_id_id

        temp = users_meta.get(user_id)

        member_image = members_data_list.get(user_id, None)

        if member_image is not None:
            temp['image_url'] = member_image

        reaction_dict = {
            'member': temp,
            'reaction': reactions_map[temp['id']]['reaction'],
            'updated_at': reactions_map[temp['id']]['updated_at']
        }

        members_profile_list.append(reaction_dict)

    return sorted(members_profile_list, key=lambda i: i['updated_at'])


def process_message_reactions(reactions):
    reactions_map = {}

    for reaction in reactions:
        temp = {
            'id': reaction.id,
            'reaction': reaction.reaction,
            'updated_at': reaction.updated_at,
        }
        reactions_map[reaction.user_id] = temp

    return reactions_map


def fetch_chatroom_or_conversation_reactions(chatroom_id=None, conversation_id=None, update_cache=False):
    """ function to update the preview of chatroom """

    if not conversation_id and not chatroom_id:
        return []

    if conversation_id:
        key = CONVERSATION_REACTIONS_CACHE_KEY % str(conversation_id)

    else:
        key = CHATROOM_REACTIONS_CACHE_KEY % str(chatroom_id)

    reactions = None if update_cache else CacheImpl.get_cache(key)

    if not reactions:

        if conversation_id:
            reactions = MessageReactions.objects.filter(conversation__id=conversation_id)

            conversation = card_answers.get_conversation_or_None(conversation_id)

            if conversation is None:
                return []

            community_instance = conversation.community

        else:
            reactions = MessageReactions.objects.filter(chatroom__id=chatroom_id, conversation=None).order_by('-updated_at')

            chatroom = Collabcard.get_chatroom_or_None(chatroom_id)

            if chatroom is None:
                return []

            community_instance = chatroom.community

        if reactions.exists():

            reaction_users = list(reactions.values_list('user__id', flat=True))

            reactions = reactions.select_related('user').only("reaction", 'user')

            reactions_map = process_message_reactions(reactions)

            reactions = get_members_profiles_for_reactions(community_instance, reaction_users, reactions_map)

        else:
            reactions = []
        
        if update_cache:
            update_chatroom_or_conversation_reactions_in_cache.delay(chatroom_id=chatroom_id,
                                                                     conversation_id=conversation_id,
                                                                     member_profiles=reactions)
    return reactions


@shared_task
def backfill_all_chatroom_reactions_in_cache():
    """
        function to backfill all chatroom reactions in cache 
    """

    try:    

        info_logger.info("Starting backfilling of all chatroom reactions in cache")

        # fetch all chatroom reactions from MessageReactions table
        chatroom_reactions = ModelUtilities.get_model_filter(MessageReactions, {'conversation': None}
                                                             ).order_by('-updated_at'
                                                                        ).values('chatroom_id',
                                                                                 'user_id',
                                                                                 'reaction',
                                                                                 'updated_at')

        chatroom_reactions_dict = {}
        user_ids = []

        # create a dictionary of chatroom reactions with chatroom_id as key
        for reaction in chatroom_reactions:

            if reaction.get('chatroom_id') not in chatroom_reactions_dict:
                chatroom_reactions_dict[reaction.get('chatroom_id')] = []

            chatroom_reactions_dict[reaction.get('chatroom_id')].append(reaction)

            user_ids.append(reaction.get('user_id'))

        from collabmates_api.raw_queries import get_users_sdk_meta_dict

        # fetch user meta for all users
        users_meta = get_users_sdk_meta_dict(user_ids)

        # iterate over all chatroom_ids and check cache
        for chatroom_id, reactions in chatroom_reactions_dict.items():

            cache_key = CHATROOM_REACTIONS_CACHE_KEY % str(chatroom_id)

            cache_data = CacheImpl.get_cache(cache_key)

            # if cache data already exists, then do not update
            if cache_data:
                continue
            else:
                cache_data = []

            # Make reactions list in ascending order of updated_at
            for reaction in chatroom_reactions_dict[chatroom_id]:
                user_meta = users_meta.get(reaction.get('user_id'))

                reaction_dict = {
                    'member': user_meta,
                    'reaction': reaction.get('reaction'),
                    'updated_at': reaction.get('updated_at')
                }

                cache_data.append(reaction_dict)
    
            cache_data = sorted(cache_data, key=lambda i: i['updated_at'])

            # set cache data
            CacheImpl.set_cache(cache_key, cache_data)

            info_logger.info("Cache set for chatroom_id: %s" % str(chatroom_id))
    
    except Exception as e:
        error_logger.error("Error in backfill_chatroom_reactions_for_all_communities: %s" % str(e))


@shared_task
def backfill_all_conversation_reactions():

    try:
        
        info_logger.info("Starting backfilling of all conversation reactions in cache")

        # fetch all chatroom reactions from MessageReactions table
        conversation_reactions = ModelUtilities.get_model_filter(MessageReactions, {'conversation__isnull': False}
                                                                 ).order_by('-updated_at'
                                                                            ).values('conversation_id',
                                                                                     'chatroom_id',
                                                                                     'user_id',
                                                                                     'reaction',
                                                                                     'updated_at')
        
        conversation_reactions_dict = {}
        user_ids = []

        # create a dictionary of conversation reactions with conversation_id as key
        for reaction in conversation_reactions:
                
            if reaction.get('conversation_id') not in conversation_reactions_dict:
                conversation_reactions_dict[reaction.get('conversation_id')] = []

            conversation_reactions_dict[reaction.get('conversation_id')].append(reaction)

            user_ids.append(reaction.get('user_id'))

        from collabmates_api.raw_queries import get_users_sdk_meta_dict

        # fetch user meta for all users
        users_meta = get_users_sdk_meta_dict(user_ids)

        # iterate over all conversation_ids and check cache
        for conversation_id, reactions in conversation_reactions_dict.items():
                
            cache_key = CONVERSATION_REACTIONS_CACHE_KEY % str(conversation_id)

            cache_data = CacheImpl.get_cache(cache_key)

            # if cache data already exists, then do not update
            if cache_data:
                continue
            else:
                cache_data = []

            # Make reactions list in ascending order of updated_at
            for reaction in conversation_reactions_dict[conversation_id]:
                user_meta = users_meta.get(reaction.get('user_id'))

                reaction_dict = {
                    'member': user_meta,
                    'reaction': reaction.get('reaction'),
                    'updated_at': reaction.get('updated_at')
                }

                cache_data.append(reaction_dict)
    
            cache_data = sorted(cache_data, key=lambda i: i['updated_at'])

            # set cache data
            CacheImpl.set_cache(cache_key, cache_data)

            info_logger.info("Cache set for conversation_id: %s" % str(conversation_id))

    except Exception as e:
        error_logger.error("Error in backfill_all_conversation_reactions: %s" % str(e))

