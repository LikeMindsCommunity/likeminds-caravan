import time

from togther.models import (ModelUtilities, Community, CommunityBillingDates)
from utility.version_utilities import (VersionUtilities)
from collabmates_api.sdk.models import (SdkClient)


def backfill_community_billing_dates_for_mau_tracking(community_id):

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

    if not community_instance:
        return
        
    for sdk_source in VersionUtilities.SdkSource.get_sdk_source_list():

        ModelUtilities.update_or_create_model(CommunityBillingDates, {'community': community_instance, 
                                                                        'sdk': sdk_source, 
                                                                        'start_date': 1
                                                                        }, {})
    
        print(f"Successfully added billing date for community {community_id} for MAU tracking for {sdk_source}")

    return

def backfill_billing_date_for_all_sdk_communities():

    existing_community_filter = ModelUtilities.get_model_filter(CommunityBillingDates, {}).values_list('community_id', flat=True)

    community_ids = ModelUtilities.get_model_filter(SdkClient, {"is_deleted": False}).exclude(community_id__in=existing_community_filter).values_list('community_id', flat=True)

    for community_id in community_ids:
        backfill_community_billing_dates_for_mau_tracking(community_id)
    
    return

start_time = time.time()
print("Starting script!")
backfill_billing_date_for_all_sdk_communities()
print("Script completed in: ", time.time() - start_time)