import time
import json

from togther.models import (ModelUtilities, card_answers, collabcardState, conversationEngage, userMemberRights,
                            Members)
from collabmates_api.sdk.models import (SdkClient)
from collabmates_api.conversation.conversation_impl import ConversationHelper
from utility.states import (conversation_states, member_states, member_rights)
from utility.time_utilities import TimeUtilities


def backfill_conversation_engage_followed_members_in_sdk():
    all_sdk_communities = ModelUtilities.get_model_filter(SdkClient, {})
    community_ids_list = list(all_sdk_communities.values_list('community_id', flat=True))

    state_filter = ModelUtilities.get_model_filter(collabcardState,
                                                   {'community__in': community_ids_list,
                                                    'follow_status': True})

    bulk_conversation_engage = []
    user_community_rights = {}
    chatroom_last_conversation = {}
    last_conversation_user_member = {}

    count = len(state_filter)

    for state_instance in state_filter:
        print('Records left:', count)

        engage_filter = ModelUtilities.get_model_filter(conversationEngage,
                                                        {'card': state_instance.card,
                                                         'user': state_instance.user})

        if engage_filter:
            count -= 1
            continue

        engage_params = {
            'card': state_instance.card,
            'user': state_instance.user,
            'community': state_instance.community
        }

        user_community_key = '___'.join([str(state_instance.user_id), str(state_instance.community_id)])

        if not user_community_rights.get(user_community_key):
            rights_list = list(ModelUtilities.get_model_filter(userMemberRights,
                                                               {'user': state_instance.user,
                                                                'community': state_instance.community}).
                               values_list("right__state", flat=True))

            if not rights_list:
                member_state = Members.get_community_member_state(state_instance.community, state_instance.user)

                if member_state == member_states.ADMIN:
                    rights_list = json.dumps(member_rights.ALL_MEMBER_RIGHTS)

                elif member_state == member_states.MEMBER or member_state == member_states.PROFILE_UNAVAILABLE:
                    rights_list = json.dumps(member_rights.DEFAULT_MEMBER_RIGHTS)

            user_community_rights[user_community_key] = rights_list

        engage_params['rights_list'] = user_community_rights.get(user_community_key)

        unseen_count_filter = {
            'card': state_instance.card,
            'state__in': [conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]
        }

        if state_instance.last_seen_conversation_id:
            unseen_count_filter['id__gt'] = state_instance.last_seen_conversation_id

        engage_params['unseen_count'] = ModelUtilities.get_model_filter(card_answers, unseen_count_filter).count()

        if not chatroom_last_conversation.get(state_instance.card_id):
            last_conversation = ModelUtilities.get_model_filter(card_answers, {'card': state_instance.card}).last()
            chatroom_last_conversation[state_instance.card_id] = last_conversation

        engage_params['last_conversation'] = chatroom_last_conversation.get(state_instance.card_id)

        if not last_conversation_user_member.get(user_community_key):
            (last_conversation_member, second_last_conversation_member, last_conversation_user,
             second_last_conversation_user) = ConversationHelper.compute_member_images_for_homescreen(
                state_instance.card, state_instance.community)

            last_conversation_user_member[user_community_key] = {
                'last_conversation_member': last_conversation_member,
                'second_last_conversation_member': second_last_conversation_member,
                'last_conversation_user': last_conversation_user,
                'second_last_conversation_user': second_last_conversation_user,
            }

        engage_params = {**engage_params, **last_conversation_user_member.get(user_community_key)}

        engage_params['created_at'] = TimeUtilities.current_time_in_sec()
        engage_params['updated_at'] = TimeUtilities.current_time_in_sec()

        bulk_conversation_engage.append(conversationEngage(**engage_params))

        count -= 1

    print('Creating engage instances number:', len(bulk_conversation_engage))
    ModelUtilities.bulk_create_instances(conversationEngage, bulk_conversation_engage)


start = time.time()
print("Starting script")
backfill_conversation_engage_followed_members_in_sdk()
print("Script completed in:", time.time() - start)
