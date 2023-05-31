import time

from togther.models import (ModelUtilities, SDKClientUsersInfo, Userinfo)

community_id = None


def remove_user_records_created_during_bug():

    if not community_id:
        return

    sdk_client_user_info_filter = ModelUtilities.get_model_filter(SDKClientUsersInfo, {'community_id': community_id})

    count = sdk_client_user_info_filter.count()
    records_processed = 0

    for sdk_user_instance in sdk_client_user_info_filter:
        user_info_instance = ModelUtilities.get_model_filter(
            Userinfo, {'user_unique_id': sdk_user_instance.user_unique_id}).exclude(
            user_id=sdk_user_instance.user).first()

        if user_info_instance:
            filter_dict = {
                'community': community_id,
                'user': user_info_instance.user_id
            }

            sdk_client_user_info_instance = ModelUtilities.get_model_filter(SDKClientUsersInfo, filter_dict).first()

            if sdk_client_user_info_instance:
                print(records_processed, sdk_client_user_info_instance.user_unique_id)

                sdk_user_instance.user_unique_id = sdk_client_user_info_instance.user_unique_id
                sdk_user_instance.save()

                ModelUtilities.delete_record_in_model(SDKClientUsersInfo, {'id': sdk_client_user_info_instance.id})
                ModelUtilities.delete_record_in_model(Userinfo, {'id': user_info_instance.id})

                records_processed += 1

                print("Records left", count)

        count -= 1

    print("{} records successfully updated!".format(records_processed))


start = time.time()
print("Starting script!")
remove_user_records_created_during_bug()
print("Script completed in", time.time() - start)
