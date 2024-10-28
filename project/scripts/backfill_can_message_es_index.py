import time

from collabmates_api.search.sync import ElasticSearchSync
from collabmates_api.sdk.models import SdkClient
from togther.models import ModelUtilities


def backfill_can_message_es_index():
    sdk_communities = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False})

    count = sdk_communities.count()

    for sdk_community in sdk_communities:
        print(f"Communities left: {count}")
        ElasticSearchSync.update_all_community_chatrooms(sdk_community.community_id)
        count -= 1


print("Starting the script")
start = time.time()
backfill_can_message_es_index()
print(f"Script completed in: {time.time() - start}")
