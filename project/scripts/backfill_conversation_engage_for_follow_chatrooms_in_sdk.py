import json
import time

from togther.models import (collabcardState, conversationEngage, ModelUtilities, Members, userMemberRights)
from collabmates_api.sdk.models import (SdkClient)
from utility.time_utilities import TimeUtilities


def backfill_conversation_engage_for_followed_chatrooms_in_sdk():
    sdk_communities = ModelUtilities.get_model_filter(SdkClient, {})

    conversation_engage_instances_list = []

    for community_instance in sdk_communities:
        community_instance = community_instance.community

        user_ids_list = list(ModelUtilities.get_model_filter(
            Members, {'community_id': community_instance}).values_list('member_id_id', flat=True))

        state_filter = ModelUtilities.get_model_filter(collabcardState, {'user_id__in': user_ids_list,
                                                                         'community': community_instance,
                                                                         'follow_status': True,
                                                                         'remove': None})

        rights_dict = {}

        for state_instance in state_filter:
            instance_list = ModelUtilities.get_model_filter(conversationEngage, {'card': state_instance.card,
                                                                                 'user': state_instance.user})

            if instance_list:
                continue

            if not rights_dict.get(state_instance.user_id):
                rights_list = list(userMemberRights.objects.filter(
                    user=state_instance.user, community=state_instance.community).values_list("right__state", flat=True))

                rights_dict[state_instance.user_id] = json.dumps(rights_list)

            rights_list = rights_dict.get(state_instance.user_id)

            instance = conversationEngage.create_instance_for_bulk_create(community_instance=state_instance.community,
                                                                          chatroom_instance=state_instance.card,
                                                                          user_instance=state_instance.user,
                                                                          rights_list=rights_list,
                                                                          created_at=TimeUtilities.current_time_in_sec(),
                                                                          updated_at=TimeUtilities.current_time_in_sec())

            conversation_engage_instances_list.append(instance)

    ModelUtilities.bulk_create_instances(conversationEngage, conversation_engage_instances_list)


start_time = time.time()
print("Starting script!")
backfill_conversation_engage_for_followed_chatrooms_in_sdk()
print("Script completed in", time.time() - start_time)
