from togther.models import ModelUtilities, Community, Collabcard, collabcardState
from utility.states import card_types
from collabmates_api.static_text import GENERAL_CHAT_TITLE_TEXT, GENERAL_CHAT_HEADER
from utility.time_utilities import TimeUtilities


def remove_general_chatroom_in_previous_communitites():

    all_communities_filter = ModelUtilities.get_model_filter(Community, {})

    communities_count = len(all_communities_filter)

    for community_instance in all_communities_filter:

        print("Communities left", communities_count)
        communities_count -= 1

        filter_dict = {
            'community': community_instance,
            'type': card_types.CARD_NORMAL,
            'include_members_later': True,
            'auto_follow_done': True,
            'created_at__lt': 1642096800000
        }

        if ModelUtilities.is_model_filter_exists(Collabcard, filter_dict):

            filter_dict = {
                'community': community_instance,
                'type': card_types.CARD_NORMAL,
                'include_members_later': True,
                'auto_follow_done': True,
                'title': GENERAL_CHAT_TITLE_TEXT,
                'header': GENERAL_CHAT_HEADER,
                'created_at__gte': 1642096800000  # As this was created at 13-01-2022 23:30
            }

            card_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

            if not card_filter:
                continue

            card_instance = card_filter[0].id

            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'is_deleted': True,
                                         'updated_at': TimeUtilities.current_time_in_milliseconds()})

            ModelUtilities.model_update(collabcardState, {'card': card_instance},
                                        {'updated_at': TimeUtilities.current_time_in_sec()})
