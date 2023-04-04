import time
from togther.models import (ModelUtilities, collabcardState, Collabcard, Members, User)
from collabmates_api.sdk.models import (SdkClient)
from utility.states import (card_types, member_states)


def backfill_collabcardstate_for_cm_secret_chatrooms():
    sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False})
    sdk_communities_list = sdk_client_filter.values_list('community_id', flat=True)

    filter_dict = {
        'community__in': sdk_communities_list,
        'is_secret': True,
        'is_deleted': False,
        'type': card_types.CARD_NORMAL
    }

    chatrooms_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

    community_cms_map = {}
    bulk_create_list = []

    chatroom_count = chatrooms_filter.count()

    for chatroom in chatrooms_filter:
        print("Chatrooms yet to be processed:", chatroom_count)

        chatroom_count -= 1

        if chatroom.community_id not in community_cms_map:
            cms_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom.community,
                                                                   'state': member_states.ADMIN})

            community_cms_map[chatroom.community_id] = list(set(cms_filter.values_list('member_id_id', flat=True)))

        cms_list = community_cms_map.get(chatroom.community_id)

        card_state_filter = ModelUtilities.get_model_filter(collabcardState, {'card': chatroom,
                                                                              'user__in': cms_list})

        new_cms = set(cms_list) - set(card_state_filter.values_list('user_id', flat=True))

        if len(new_cms) <= 0:
            continue

        else:

            user_instances = ModelUtilities.get_model_filter(User, {'id__in': list(new_cms)})

            for user_instance in user_instances:
                instance = collabcardState.create_chatroom_state_instances_for_bulk_create(
                    chatroom, user_instance, follow_status=False, state=0, community_instance=chatroom.community,
                    external_seen=False, expire_at=None)

                if instance:
                    bulk_create_list.append(instance)

                if len(bulk_create_list) >= 1000:
                    print("Creating collabcard states!")
                    ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)
                    bulk_create_list = []

    print("Creating collabcard states!")
    ModelUtilities.bulk_create_instances(collabcardState, bulk_create_list)


start = time.time()
print("Starting script!")
backfill_collabcardstate_for_cm_secret_chatrooms()
print("Script completed in:", time.time() - start)
