from typing import List

from models.user import UserModel
from ..constants import LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE

from collabmates_api.community.community_impl import CommunityImpl
from togther.models import SDKClientUsersInfo, Members, Userinfo, ModelUtilities
from utility.time_utilities import TimeUtilities


class MigrateUsers:

    def __init__(self, bot_id: int, community_id: int, users_data: List[UserModel]):
        self.member_id = bot_id
        self.community_id = community_id
        self.users_data = users_data

    def _add_member_to_community(self, req_body):
        community_manager = CommunityImpl(
            member_id=self.member_id,
            api_key=LIKEMINDS_API_KEY,
            request_platform=PLATFORM_CODE,
            version_code=VERSION_CODE,
        )
        community_data = community_manager.add_community_member(req_body)

        if community_data.get("error_message"):
            raise ValueError(community_data.get("error_message"))

        return community_data

    def add_all_members_data(self):
        print("*" * 50)
        print(f"Total users to be added: {len(self.users_data)}")

        sdk_instances_list = []
        userinfo_instances_list = []
        member_instances_list = []

        for user_data in self.users_data:
            # TODO: Add code to upload image url to S3 and replace the image_url with the new one

            request_body = user_data.model_dump(
                include=["uuid", "user_name", "image_url"]
            )

            print(
                f"Calling api/community/member POST with request body: {request_body}"
            )
            response = self._add_member_to_community(request_body)

            # Update the created_at for Users, SdkClientUsersInfo, Members schema
            sdk_user_instance: SDKClientUsersInfo = ModelUtilities.get_model_filter(
                SDKClientUsersInfo,
                {"user_unique_id": user_data.uuid, "community": self.community_id},
            ).first()

            if sdk_user_instance:
                created_at = TimeUtilities.convert_sec_to_milliseconds(
                    user_data.created_at
                )

                sdk_user_instance.created_at = created_at
                sdk_user_instance.user.userinfo.created_at = user_data.created_at

                sdk_instances_list.append(sdk_user_instance)
                userinfo_instances_list.append(sdk_user_instance.user.userinfo)

                member_instance: Members = ModelUtilities.get_model_filter(
                    Members,
                    {
                        "community_id": self.community_id,
                        "member_id": sdk_user_instance.user,
                    },
                ).first()

                if member_instance:
                    member_instance.created_at = user_data.created_at
                    member_instance.became_member_at = user_data.created_at
                    member_instances_list.append(member_instance)

        ModelUtilities.bulk_update_instances(
            SDKClientUsersInfo, sdk_instances_list, fields=["created_at"]
        )
        ModelUtilities.bulk_update_instances(
            Userinfo, userinfo_instances_list, fields=["created_at"]
        )
        ModelUtilities.bulk_update_instances(
            Members, member_instances_list, fields=["created_at", "became_member_at"]
        )
