import time

from collabmates_api.sdk.models import (SdkClient)
from togther.models import (ModelUtilities, CommunityIntegrationStatus)
from utility.time_utilities import TimeUtilities

STATUS_TYPES_LIST = ["COPY_INTEGRATION_CODE", "COPY_API_KEY", "FINISH"]
DEFAULT_STATUS = True


def backfill_integration_status_for_all_sdks():

    for status_type in STATUS_TYPES_LIST:
        integration_instances_list = []
        print(f"Start backfilling for status type: {status_type}")

        existing_status_filter = ModelUtilities.get_model_filter(CommunityIntegrationStatus,
                                                                 {'status_type': status_type})
        existing_status_communities = list(existing_status_filter.values_list('community', flat=True))

        remaining_sdk_communities = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False}).exclude(
            community__in=existing_status_communities)

        for sdk_community in remaining_sdk_communities:
            integration_instances_list.append(CommunityIntegrationStatus(
                community=sdk_community.community, status_type=status_type, status=DEFAULT_STATUS,
                created_at=TimeUtilities.current_time_in_milliseconds(),
                updated_at=TimeUtilities.current_time_in_milliseconds()))

            print(f"Total {len(remaining_sdk_communities)} communities added for status type: {status_type}")

        # Bulk create the integration status instances
        ModelUtilities.bulk_create_instances(CommunityIntegrationStatus, integration_instances_list)


print("Starting script!")
start = time.time()
backfill_integration_status_for_all_sdks()
print("Script completed in: ", time.time() - start)
