from typing import List
from pathlib import Path

from ..models.user import UserModel
from ..constants import LIKEMINDS_API_KEY, PLATFORM_CODE, VERSION_CODE, USER_PROFILE_IMAGE_S3_PATH

from collabmates_api.community.community_impl import CommunityImpl
from togther.models import SDKClientUsersInfo, Members, Userinfo, ModelUtilities
from utility.time_utilities import TimeUtilities

from ..utils.lambda_utilities import LambdaUtilities


class MigrateUsers:

    def __init__(self, bot_id: int, community_id: int, users_data: List[UserModel]):
        self.member_id = bot_id
        self.community_id = community_id
        self.users_data = users_data

    @staticmethod
    def _create_s3_path_to_save_profile(url: str, uuid: str):
        url_path = Path(url)

        return USER_PROFILE_IMAGE_S3_PATH.format(uuid, url_path.stem, "".join([
            str(TimeUtilities.current_time_in_milliseconds()), url_path.suffix]))

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
            s3_path = self._create_s3_path_to_save_profile(user_data.image_url, user_data.uuid)
            s3_url = LambdaUtilities.migrate_to_s3(user_data.image_url, s3_path, is_prod=False)

            if not s3_url:
                raise ValueError(f"Error in uploading file to s3: {s3_url} for user uuid: {user_data.uuid}")

            request_body = user_data.model_dump(
                include=["uuid", "user_name", "image_url"]
            )

            print(
                f"Calling api/community/member POST with request body: {request_body}"
            )
            self._add_member_to_community(request_body)

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
