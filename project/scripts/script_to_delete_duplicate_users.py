import json
from togther.models import User, SDKClientUsersInfo

def open_file_and_parse_json(file_name):

    try:
        with open(file_name) as json_file:
            data = json.load(json_file)
            return data
        
    except Exception as e:
        print("Error: ", e)
        return None
    
def write_json_to_file(file_name, data):

    try:
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    except Exception as e:
        print("Error: ", e)
        return None
    
def delete_duplicate_users(parsed_users_data: dict):

    # the 4 users with interaction with more than 2 accounts (uuid -> user_id)
    users_to_keep = {
        "373279" : "402902",
        "50419623" : "166450",
        "51230655" : "350021",
        "5143168" : "436619"
    }

    try:

        user_deletion_response = {}

        for uuid, users in parsed_users_data.items():

            user_deletion_response[uuid] = []
            user_id_to_keep = None

            if uuid in users_to_keep:
                user_id_to_keep = users_to_keep[uuid]

            for user in users:
                if user["chat_interaction"] == True:
                    user_id_to_keep = user["user_id"]
                    break

                if user["feed_interaction"] == True:
                    user_id_to_keep = user["user_id"]
                    break

            if user_id_to_keep == None:

                record = SDKClientUsersInfo.objects.filter(user_unique_id=uuid).last()
                user_id_to_keep = record.user_id

            # delete all the users with the same uuid except the one with the user_id_to_keep
            for user in users:
                if user["user_id"] != user_id_to_keep:
                    User.objects.filter(id=user["user_id"]).delete()
                    print(f"Deleted user with id: {user['user_id']} & community_id: {user['community_id']}" )

                    user["is_deleted"] = True

                
                else:
                    print(f"Kept user with id: {user['user_id']} & community_id: {user['community_id']}" )

                    user["is_deleted"] = False
                
                user_deletion_response[uuid].append(user)

        return user_deletion_response
    
    except Exception as e:
        print("Error: ", e)
        return None

    
def run_script():

    print("Script started")

    input_file_name = "project/scripts/users_interaction_data.json"
    output_file_name = "project/scripts/final_user_deletion_data.json"

    parsed_users_data = open_file_and_parse_json(input_file_name)
    user_deletion_data = delete_duplicate_users(parsed_users_data)
    write_json_to_file(output_file_name, user_deletion_data)

    print("Script completed successfully")

# run_script()