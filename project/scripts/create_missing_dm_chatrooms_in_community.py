import time

from django.conf import settings
from togther.models import (ModelUtilities, Members, Collabcard, Community)
from utility.states import (member_states, card_types)
from utility.celery_tasks import (fill_chatroom_basic_info, initial_message_dm_chatroom)
from utility.time_utilities import TimeUtilities
from collabmates_api.search.sync import ElasticSearchSync


if settings.IS_BETA:
    community_id = 50430

else:
    community_id = 0


def create_missing_dm_chatrooms_in_community():
    admins_filter = ModelUtilities.get_model_filter(Members,
                                                    {"community_id": community_id,
                                                     "state": member_states.ADMIN})

    if not admins_filter.exists():
        return

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return

    total_users_count = admins_filter.count()

    for admin_instance in admins_filter:

        members_filter = ModelUtilities.get_model_filter(Members, {"community_id": community_id}).exclude(
            id=admin_instance.id)

        print("User left ->", total_users_count)

        for member_instance in members_filter:

            chatroom_user = member_instance.member_id
            user_instances_list = [admin_instance.member_id, chatroom_user]

            dm_chatroom_filter = ModelUtilities.get_model_filter(Collabcard,
                                                                 {"user__in": user_instances_list,
                                                                  "chatroom_with_user__in": user_instances_list,
                                                                  "community": community_id,
                                                                  "is_private": True,
                                                                  "type": card_types.CARD_DIRECT_MESSAGE})

            if not dm_chatroom_filter:
                card_content = {}
                chatroom_name = "Direct Message"
                chatroom_type = card_types.CARD_DIRECT_MESSAGE

                card_content['chatroom_with_user'] = chatroom_user
                card_content['is_private'] = True

                # Fill chatroom basic Info
                card_content = fill_chatroom_basic_info(card_content, chatroom_name, chatroom_type, community_instance,
                                                        admin_instance.member_id)

                # Fill chatroom epoch time
                card_content['date_epoch'] = TimeUtilities.current_time_in_sec()

                # Fill chatroom header
                card_content['header'] = chatroom_name
                card_content['has_been_named'] = True

                card_content['member_state'] = member_states.ADMIN

                chatroom_instance = Collabcard(**card_content)
                chatroom_instance.save()

                # Set initial chatroom message
                initial_message_dm_chatroom(chatroom_instance, admin_instance.member_id, chatroom_user,
                                            community_instance, user_instances_list)

                # Update All community chatrooms for user
                ElasticSearchSync.update_chatroom.delay(chatroom_instance.id)

        total_users_count -= 1


start = time.time()
print("Starting script!")
create_missing_dm_chatrooms_in_community()
print("Script completed in ->", time.time() - start)
