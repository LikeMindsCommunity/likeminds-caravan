from celery import shared_task

from collabmates_api.sync.model_update import update_models_for_syncing_apis
from external_services.caching.cache_impl import CacheImpl
from togther.models import Members, MessageReactions, card_answers, Collabcard
from utility.cache_keys import CONVERSATION_REACTIONS_CACHE_KEY, CHATROOM_REACTIONS_CACHE_KEY
from utility.states import SyncTypes


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


def get_members_profiles_for_reactions(community, members_id_list, reactions_map):
    reacted_members = Members.objects\
        .filter(community_id=community,
                member_id__id__in=members_id_list)\
        .select_related('member_id__userinfo')

    members_list = []

    for member in reacted_members:
        userinfo = member.member_id.userinfo
        user_image = userinfo.image_link

        temp = {
            'id': member.member_id_id,
            'name': userinfo.name,
            'image_url': user_image if user_image else ''
        }

        member_image = member.image_url

        if member_image is not None:
            temp['image_url'] = member_image

        reaction_dict = {
            'member': temp,
            'reaction': reactions_map[temp['id']]['reaction']
        }

        members_list.append(reaction_dict)

    return members_list


def process_message_reactions(reactions):
    reactions_map = {}

    for reaction in reactions:
        temp = {
            'reaction': reaction.reaction,
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
                return

            community_instance = conversation.community

        else:
            reactions = MessageReactions.objects.filter(chatroom__id=chatroom_id, conversation=None)

            chatroom = Collabcard.get_chatroom_or_None(chatroom_id)

            if chatroom is None:
                return

            community_instance = chatroom.community

        if reactions.exists():

            reaction_users = list(reactions.values_list('user__id', flat=True))

            reactions = reactions.select_related('user').only("reaction", 'user')

            reactions_map = process_message_reactions(reactions)

            reactions = get_members_profiles_for_reactions(community_instance, reaction_users, reactions_map)

            update_chatroom_or_conversation_reactions_in_cache(chatroom_id=chatroom_id,
                                                                     conversation_id=conversation_id,
                                                                     member_profiles=reactions)
        else:
            reactions = []

    return reactions
