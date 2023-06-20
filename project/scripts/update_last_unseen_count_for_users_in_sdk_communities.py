import time
from utility.celery_tasks import (update_last_unseen_in_engage_on_card_creation)
from collabmates_api.sdk.models import(SdkClient)

def update_unseen_chatroom_count_for_all_members_in_all_sdk_communities():

    community_ids = SdkClient.objects.filter(is_deleted=False).values_list('community_id', flat=True)
    count = len(community_ids)
    print('Community ids:', count)

    for community_id in community_ids:
        count -= 1

        print('Updating last seen for community:', community_id)
        
        update_last_unseen_in_engage_on_card_creation(community_id)

        print('communities left:', count)
 
start = time.time()
print('Starting script!')
update_unseen_chatroom_count_for_all_members_in_all_sdk_communities()
print('Script completed in', time.time() - start)

