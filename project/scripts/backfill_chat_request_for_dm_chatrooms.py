import time
from togther.models import (ModelUtilities, collabcardState)
from utility.states import DMChatRequestStates
from collabmates_api.notification import get_connection
from collabmates_api.raw_queries import convert_sql_query_result_to_dict

COMMUNITY_ID = 49928
COMMUNITY_ID_QUERY = ""

if COMMUNITY_ID:
    COMMUNITY_ID_QUERY = f" AND togther_collabcard.community_id = {COMMUNITY_ID}"

SQL_RAW_QUERY = f"""
SELECT * FROM (SELECT 
togther_card_answers.card_id, 
togther_card_answers.user_id, 
togther_card_answers.created_at,
togther_collabcard.user_id AS card_user_id,
togther_collabcard.chatroom_with_user_id AS card_chatroom_with_user_id,
Row_number() 
OVER(
partition BY togther_card_answers.card_id ORDER BY  togther_card_answers.created_at) AS row_number 
FROM togther_card_answers
INNER JOIN togther_collabcard
ON 
(togther_card_answers.card_id = togther_collabcard.id 
AND togther_collabcard.is_private_member = False 
AND togther_collabcard.is_private = true
AND togther_collabcard.type = 10 {COMMUNITY_ID_QUERY})
INNER JOIN togther_collabcardstate
ON (togther_collabcardstate.card_id = togther_card_answers.card_id and chat_request_state IS NULL)
WHERE togther_card_answers.state = 0) AS partitioned_data
WHERE partitioned_data.row_number = 1;
"""


def get_list_of_chatrooms_to_update():
    conn = get_connection()
    curr = conn.cursor()

    curr.execute(SQL_RAW_QUERY)
    answer_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
    curr.close()

    answer_dict = {}
    card_ids_list = []

    for answer in answer_data:
        card_id = answer.get("card_id")
        answer_dict[card_id] = {
            "user_id": answer.get("user_id"),
            "created_at": answer.get("created_at"),
            "card_user_id": answer.get("card_user_id"),
            "card_chatroom_with_user_id": answer.get("card_chatroom_with_user_id")
        }
        card_ids_list.append(card_id)

    card_ids_list = list(set(card_ids_list))

    return len(card_ids_list), card_ids_list, answer_dict


def backfill_chat_request_for_dm_chatrooms():
    _, card_ids_list, answer_dict = get_list_of_chatrooms_to_update()

    if not card_ids_list:
        print(f"No list to update!")
        return

    chatroom_state_dict = {}

    filter_dict = {
        "card_id__in": card_ids_list,
        "chat_request_state": None
    }

    state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)
    count = state_filter.count()

    chat_request_state = DMChatRequestStates.ACCEPTED

    bulk_update_list = []

    for state_instance in state_filter:
        card_id = state_instance.card_id

        print(f"Records left: {count}, processing card id: {card_id}")

        if card_id in chatroom_state_dict:
            chatroom_state_card_dict = chatroom_state_dict.get(card_id)
            chat_request_created_at = chatroom_state_card_dict.get("chat_request_created_at")
            chat_requested_by = chatroom_state_card_dict.get("chat_requested_by")
            chat_request_initiated_by = chatroom_state_card_dict.get("chat_request_initiated_by")

        else:
            answer_data = answer_dict.get(card_id)

            if not answer_data:
                print(f"No answer data left for card_id: {card_id}")
                continue

            chat_request_created_at = answer_data.get("created_at")

            if answer_data.get("user_id") == answer_data.get("card_user_id"):
                chat_requested_by = state_instance.card.chatroom_with_user
                chat_request_initiated_by = state_instance.card.user

            else:
                chat_requested_by = state_instance.card.user
                chat_request_initiated_by = state_instance.card.chatroom_with_user

            chatroom_state_dict[card_id] = {
                "chat_request_created_at": chat_request_created_at,
                "chat_requested_by": chat_requested_by,
                "chat_request_initiated_by": chat_request_initiated_by
            }

        state_instance.chat_request_created_at = chat_request_created_at
        state_instance.chat_requested_by = chat_requested_by
        state_instance.chat_request_state = chat_request_state
        state_instance.chat_request_initiated_by = chat_request_initiated_by

        bulk_update_list.append(state_instance)

    ModelUtilities.bulk_update_instances(collabcardState,
                                         bulk_update_list,
                                         ["chat_request_created_at",
                                          "chat_requested_by",
                                          "chat_request_state",
                                          "chat_request_initiated_by"])


print(f"Starting the script!")
start = time.time()
get_list_of_chatrooms_to_update()
print(f"Script completed in: {time.time() - start}")
