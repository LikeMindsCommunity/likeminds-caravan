import json
from django.db.models import Count, Q
from togther.models import SDKClientUsersInfo, card_answers, MessageReactions

def dump_json(data, file_name):
    print("______________________________ Dumping data to file name -> " , file_name, "  ______________________________")

    with open(file_name, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)

def find_duplicate_users() -> dict:
    print("______________________________ Finding Duplicate Users ______________________________")
    duplicate_user_uuids = SDKClientUsersInfo.objects.values('user_unique_id', 'community_id'
                                                             ).annotate(count=Count('user_unique_id')
                                                                        ).filter(count__gt=1
                                                                                 ).values_list('user_unique_id', 'community_id')
    uuid_map = {}

    # Make uuid -> users map
    for uuid, community_id in duplicate_user_uuids:
        users = SDKClientUsersInfo.objects.filter(user_unique_id=uuid, community_id=community_id
                                                  ).order_by('id'
                                                             ).values_list('user_unique_id', 'user_id', 'community_id', 'user__userinfo__user_unique_id')
        
        uuid_map[uuid] = list(users)

    return uuid_map

def user_interaction_map(uuid_map: dict):
    print("______________________________ Users Interaction ______________________________")
    user_interaction_map = {}
    unique_users_interaction_data = {}

    for uuid, users in uuid_map.items():   
        user_interaction_map[uuid] = []

        user_interaction_count = 0

        for user in users:

            # Parse tuple to User
            userData = {
                'client_uuid': user[0],
                'user_id': user[1],
                'community_id': user[2],
                'lm_uuid': user[3],
                'chat_interaction': False,
                'feed_interaction': False 
            }
            convs = card_answers.objects.filter(user_id=user[1], state__in=[0,10]).exists()
            reactions = MessageReactions.objects.filter(user_id=user[1]).exists()
            
            if convs or reactions:
                user_interaction_count += 1
                userData['chat_interaction'] = True
            
            user_interaction_map[uuid].append(userData)

        # Print no. of users interacted & Get users who have interacted from more than 1 account
        if user_interaction_count > 1:
            unique_users_interaction_data[uuid] = user_interaction_map[uuid]
            print("uuid -> ", uuid, " no. users interacted -> ", user_interaction_count, "users -> " , user_interaction_map[uuid])

    return user_interaction_map, unique_users_interaction_data

def runScript():
    duplicate_users_map = find_duplicate_users()
    user_interaction_data, unique_data = user_interaction_map(duplicate_users_map)

    # Data for all the duplicate users
    dump_json(user_interaction_data, 'duplicate_users_data.json')

    # Data for the users who have interacted from more than 1 account
    dump_json(unique_data, 'unique_users_data.json')

# runScript()
