import time, json

from togther.models import (ModelUtilities, Collabcard, collabcardState)
from utility.celery_tasks import (convert_chatroom_to_secret_chatroom)


def convert_secret_chatroom_again_to_secret_for_bugfix(chatroom_id):

    chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not chatroom_instance:
        return False

    # Get secret chatroom participants of the chatroom
    try:
        secret_chatroom_participants = json.loads(chatroom_instance.secret_chatroom_participants)

    except Exception as e:
        print("Error: ", e)
        return False
    
    # Get all participants of the chatroom with follow_status = True
    participants_filter = ModelUtilities.get_model_filter(collabcardState, 
                                                              { "card_id" : chatroom_id,
                                                               "follow_status": True}
                                                               )
    
    # Exclude secret chatroom participants from the participants_filter
    participants_filter = participants_filter.exclude(user__id__in=secret_chatroom_participants)
    
    # set follow_status to False for all participants not in secret_chatroom_participants key
    participants_filter.update(follow_status=False)

    start_time = time.time()
    print("Converting chatroom to secret chatroom")

    # Convert chatroom to secret chatroom and delete collabcard states for users with follow_status : false
    convert_chatroom_to_secret_chatroom(chatroom_id)

    print("Time taken to convert chatroom to secret chatroom: ", time.time() - start_time)

    return True


def run_script():

    # Chatroom id to convert (change this to the chatroom id you want to convert)
    chatroom_id = 0

    convert_secret_chatroom_again_to_secret_for_bugfix(chatroom_id)

    
if __name__ == "__main__":
    run_script()