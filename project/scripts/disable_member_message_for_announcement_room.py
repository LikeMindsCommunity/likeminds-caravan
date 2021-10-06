import time

from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import Collabcard, ModelUtilities
from utility.states import card_types
from utility.time_utilities import TimeUtilities

info_logger = LoggingWrapper.get_instance()


def disable_member_can_message_for_announcement_room():
    chatroom_list = ModelUtilities.get_model_filter(Collabcard, {'type': card_types.CARD_PURPOSE})

    bulk_update_list = []
    fields_to_update = ['member_can_message', 'updated_at']

    for chatroom in chatroom_list:
        print("ID: ", chatroom.id)
        info_logger.info("ID: {}".format(chatroom.id))
        chatroom.member_can_message = False
        chatroom.updated_at = TimeUtilities.current_time_in_sec()
        bulk_update_list.append(chatroom)

    ModelUtilities.bulk_update_instances(Collabcard, bulk_update_list, fields_to_update)


print("Disabling member_can_message for Existing Announcement Rooms")
info_logger.info("Disabling member_can_message for Existing Announcement Rooms")
start_time = time.time()
disable_member_can_message_for_announcement_room()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
