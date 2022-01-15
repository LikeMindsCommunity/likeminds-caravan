from togther.models import ModelUtilities, Community, Collabcard, Report_Tags, conversationEngage
from utility.states import card_types, SyncTypes
from collabmates_api.static_text import GENERAL_CHAT_TITLE_TEXT, GENERAL_CHAT_HEADER
from collabmates_api.sync.model_update import update_models_for_syncing_apis
from collabmates_api.search.sync import ElasticSearchSync
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
                'is_deleted': False,
                'created_at__gte': 1642096800000  # As this was created at 13-01-2022 23:30
            }

            card_filter = ModelUtilities.get_model_filter(Collabcard, filter_dict)

            if not card_filter:
                continue

            card_instance = card_filter[0]

            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'is_deleted': True,
                                         'deleted_by_user': card_instance.user,
                                         'tag': ModelUtilities.get_model_filter(Report_Tags, {'tag_id': 11})[0],
                                         'reason': 'SCRIPT',
                                         'updated_at': TimeUtilities.current_time_in_milliseconds()})

            # Delete conversation engage
            ModelUtilities.get_model_filter(conversationEngage, {'card': card_instance}).delete()

            update_models_for_syncing_apis(SyncTypes.CHATROOM, {'card': card_instance}, {})

            # Update Elastic search
            ElasticSearchSync.delete_chatroom.delay(card_instance.id)


print("Started")
start = TimeUtilities.current_time_in_sec()
remove_general_chatroom_in_previous_communitites()
print("Time taken", TimeUtilities.current_time_in_sec() - start)
