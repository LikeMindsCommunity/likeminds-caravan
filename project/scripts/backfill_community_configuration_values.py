from togther.models import CommunityConfigurations
from utility.constants import COMMUNITY_CONFIGURATIONS

COMMUNITY_CONFIGURATION_TYPE = ""

def backfill_community_configurations():
    
    if not COMMUNITY_CONFIGURATION_TYPE:
        print("Please set the COMMUNITY_CONFIGURATION_TYPE variable")
        return
    
    # Fetch the default values from COMMUNITY_CONFIGURATIONS
    default_values = COMMUNITY_CONFIGURATIONS.get(COMMUNITY_CONFIGURATION_TYPE, {}).get("value", {})
    
    if not default_values:
        print(f"Could not find default values for type: '{COMMUNITY_CONFIGURATION_TYPE}'")
        return

    # Fetch all records where type = COMMUNITY_CONFIGURATION_TYPE
    records = CommunityConfigurations.objects.filter(type=COMMUNITY_CONFIGURATION_TYPE)

    for record in records:
        # Update only missing keys
        for key, value in default_values.items():
            if key not in record.value:
                record.value[key] = value
        record.save()

    print(f"Backfilled {records.count()} records for type '{COMMUNITY_CONFIGURATION_TYPE}'")

print("Starting the script")
backfill_community_configurations()
print("Script completed")
