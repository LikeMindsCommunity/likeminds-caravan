from togther.models import CommunityConfigurations, CommunitySettings, Members
from utility.constants import COMMUNITY_CONFIGURATIONS, FEED_SETTINGS_CONFIGURATION
from utility.states import community_setting_types
from collabmates_api.community.community_impl import CommunityHelper

COMMUNITY_CONFIGURATION_TYPE = ""

# Function to backfill default community configuration values for a specific type
def backfill_community_configurations():
    
    print("Starting the backfill_community_configurations script")
    
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

# Function to backfill auto_approve_post configurations where post_approval settings is enabled
def backfill_auto_approve_post_configurations_for_enabled_communities():

    # Fetch all the records from community settings where type = 'auto_approve_post' and enabled = True
    records = CommunitySettings.objects.filter(
        setting_type=community_setting_types.POST_APPROVAL_NEEDED, enabled=True
    )

    for record in records:

        user_id = record.enabled_by.id

        if not user_id:

            # Fetch bot id
            bot_id = Members.get_community_owner_user_instance_or_none(record.community_id)

            if not bot_id:
                print(f"Could not find bot id for community_id: {record.community_id}")
                continue
            else:
                user_id = bot_id.id

        update_values = {
            "auto_approve_post": "no_one"
        }

        CommunityHelper.update_configuration_of_community(
            community_id=record.community_id,
            user_id=user_id,
            configuration_type=FEED_SETTINGS_CONFIGURATION,
            update_values=update_values
        )
