import time
import uuid

import requests

from collabmates_api.sdk.models import (SdkClient)
from togther.models import (ModelUtilities, SDKClientUsersInfo, Community, Members)
from collabmates_api.user.user_impl import UserImpl
from collabmates_api.member_community.member_community_impl import MemberCommunityHelper

community_id = None
project_creator_id = None
transfer_ownership_otp = None
transfer_ownership_url = 'http://localhost:8000/api/transfer_ownership'
enable_join_form = True
firebase_server_key = None


def generate_api_key_for_community():
    return str(uuid.uuid4())


def migrate_non_sdk_to_sdk_community():
    print("Checking if community ID is ok or not!")
    community_instance = ModelUtilities.get_model_filter(Community, {'id': community_id}).first()

    if not community_instance:
        print("Community ID is invalid!")
        return

    print(f"Checking if {community_id} community is already SDK community!")

    sdk_filter = ModelUtilities.get_model_filter(SdkClient, {'community_id': community_id})

    if sdk_filter:
        return

    project_creator_instance = ModelUtilities.get_user_instance_or_none(project_creator_id)

    if not project_creator_instance:
        print("Error getting project creator instance!")
        return

    api_key = generate_api_key_for_community()

    while ModelUtilities.get_model_filter(SdkClient, {'api_key': api_key}).exists():
        api_key = generate_api_key_for_community()

    print(f"Checking if bot exists in {community_id} community!")

    bot_user_instance = ModelUtilities.get_model_filter(SDKClientUsersInfo,
                                                        {'community_id': community_id,
                                                         'user__userinfo__is_bot': True}).first()

    if not bot_user_instance:
        print(f"Bot not exists in {community_id} community, so creating it!")
        user_impl = UserImpl(user_id=None, api_key=api_key)

        bot_response = user_impl.create_user_bot({'name': community_instance.name})

        if bot_response.get('error_message'):
            print(bot_response.get('error_message'))
            return

        else:
            user_object = bot_response.get('user')

            if not user_object:
                print("Some error occurred in fetching user object")
                return

            bot_user_instance = ModelUtilities.get_user_instance_or_none(user_object.get('user_unique_id'),
                                                                         community_id)

            if not bot_user_instance:
                print(f"Error fetching bot user instance from {user_object}")
                return

            if community_instance and bot_user_instance:
                sdk_client_user_info_instance = SDKClientUsersInfo()
                sdk_client_user_info_instance.community = community_instance
                sdk_client_user_info_instance.user = bot_user_instance
                sdk_client_user_info_instance.user_unique_id = user_object.get('user_unique_id')
                sdk_client_user_info_instance.save()

    else:
        bot_user_instance = bot_user_instance.user

    # Create SDK client record
    print(f"Creating SDK record for {community_id} community!")
    sdk_client = SdkClient(community_id=community_id, api_key=api_key, project_creator=project_creator_instance,
                           firebase_server_key=firebase_server_key, is_join_form_enabled=enable_join_form)
    sdk_client.save()

    print("Bot instance", bot_user_instance)

    # Make bot as member of community
    print("Checking whether bot is member of community or not!")

    if not Members.is_community_member(community_instance, bot_user_instance):
        print(f"Making bot as member of {community_id} community!")
        MemberCommunityHelper.make_requesting_user_as_member_of_community(bot_user_instance, community_instance,
                                                                          req_body={}, platform='an-sdk',
                                                                          version_code=9999)

    # Make bot as owner and current owner as CM
    print(f"Transferring ownership from current owner to bot in {community_id} community!")

    current_owner_instance = Members.get_community_owner_user_instance_or_none(community_instance)

    if not current_owner_instance:
        print(f"No owner exists in {community_id} community!")
        return

    print(f"Current owner of {community_id} community is {current_owner_instance.id}")

    payload = f'community_id={community_id}&user_id={bot_user_instance.id}&otp={transfer_ownership_otp}'
    headers = {
        'x-member-id': str(current_owner_instance.id),
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", transfer_ownership_url, headers=headers, data=payload)

    print("Response of transfer ownership API", response.json())


start = time.time()
print("Starting script!")
migrate_non_sdk_to_sdk_community()
print("Script completed in:", time.time() - start)
