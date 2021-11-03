import time

from togther.models import ModelUtilities, conversationEngage, collabcardState


def delete_duplicate_conversation_engage():
    state_filter = ModelUtilities.get_model_filter(collabcardState, {})
    total_duplicate_count = 0
    duplicate_for_count = 0
    invalid_chatroom_count = 0
    invalid_user_count = 0
    deleted_engages_so_far_count = 0

    for state_instance in state_filter:
        chatroom_instance = state_instance.card
        user_instance = state_instance.user

        if not chatroom_instance or chatroom_instance.is_deleted:
            print("Invalid Chatroom")
            invalid_chatroom_count += 1
            continue

        if not user_instance or not user_instance.is_active:
            print("Invalid User")
            invalid_user_count += 1
            continue

        engage_filter = ModelUtilities.get_model_filter(conversationEngage, {'card': chatroom_instance,
                                                                             'user': user_instance})

        if len(engage_filter) > 1:
            duplicate_for_count += 1
            engage_filter = engage_filter[1:]
            total_duplicate_count += len(engage_filter)
            print('Deleted Engage instances so far', deleted_engages_so_far_count)
            deleted_engages_so_far_count += len(engage_filter)
            engage_filter.delete()

    print('total_duplicate_count', total_duplicate_count)
    print('duplicate_for_count', duplicate_for_count)
    print('invalid_chatroom_count', invalid_chatroom_count)
    print('invalid_user_count', invalid_user_count)


start_time = time.time()
print(">>>>>> Started >>>>>>>>   ", start_time)
delete_duplicate_conversation_engage()
end_time = time.time()
print(">>>>>> Ended >>>>>>>>   ", end_time)

print("Time Taken", end_time - start_time)
