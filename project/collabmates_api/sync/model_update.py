from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import card_answers, Member_Engage, Members, collabcardState, ModelUtilities
from utility.time_utilities import TimeUtilities
from utility.states import SyncTypes

error_logger = LoggingWrapper.get_instance()


def update_models_for_syncing_apis(sync_type, filter_dict, update_dict):

    if not SyncTypes.has_value(sync_type):
        error_logger.error("Invalid sync type %s" % sync_type)

        return

    update_count = 0

    if sync_type == SyncTypes.CONVERSATION:
        update_dict['last_updated'] = TimeUtilities.current_time_in_milliseconds()
        update_count = ModelUtilities.model_update(card_answers, filter_dict, update_dict)

    elif sync_type == SyncTypes.CHATROOM:
        update_dict['updated_at'] = TimeUtilities.current_time_in_sec()
        update_count = ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

    elif sync_type == SyncTypes.MEMBERS:
        update_dict['updated_at'] = TimeUtilities.current_time_in_sec()
        update_count = ModelUtilities.model_update(Members, filter_dict, update_dict)

    elif sync_type == SyncTypes.COMMUNITY:
        update_dict['updated_at'] = TimeUtilities.current_time_in_sec()
        update_count = ModelUtilities.model_update(Member_Engage, filter_dict, update_dict)

    return update_count

