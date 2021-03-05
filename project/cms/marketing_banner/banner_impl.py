import json
from typing import Union

from django.conf import settings
from django.http import JsonResponse
from rest_framework import status as status_codes

from collabmates_api.multimedia_operations.mm_operations_impl import MultimediaOperationsImpl
from .banner_manager import BannerManager
from ..models import MarketingBanner
from .serializers import BannerSerializer
from ..constants import *
from .constants import *
from togther.models import Members

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities
from utility.states import platform_codes
from utility.number_utilities import NumberUtilities
from utility.exception_utilities import JsonDecodeException, ResourceNotFoundException
from ..utils import get_error_context

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class BannerImpl(BannerManager):
    member_id = None
    platform_code = None
    app_version = 0

    def __init__(self, member_id: str = None, platform_code: str = None, app_version: int = 0):
        self.set_member_id(member_id)
        self.set_platform_code(platform_code)
        self.set_app_version(app_version)

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def set_member_id(self, member_id: Union[str, int]) -> None:

        if isinstance(member_id, int):
            self.member_id = member_id

        else:
            self.member_id = NumberUtilities.get_integer_from_string(member_id)

    def get_platform_code(self) -> str:
        return self.platform_code

    def set_platform_code(self, platform_code: str) -> None:
        self.platform_code = platform_code

    def get_app_version(self) -> int:
        return self.app_version

    def set_app_version(self, app_version: Union[str, int]) -> None:

        if isinstance(app_version, int):
            self.app_version = app_version

        else:
            self.app_version = NumberUtilities.get_integer_from_string(app_version)

    def _serialize_banners(self, queryset, many=True):
        return BannerSerializer(queryset, many=many).data

    def _create_banner_content(self, req_body):

        content = {
            "icon": req_body.get('icon', None),
            "heading": req_body.get('heading', None),
            "description": req_body.get('description', None),
            "cta": req_body.get('cta', None),
            "cta_route": req_body.get('cta_route', None),
            "min_app_version_an": req_body.get('min_app_version_an', 0),
            "min_app_version_ios": req_body.get('min_app_version_ios', 0),

            "hide_time": req_body.get('hide_time', BANNER_DEFAULT_HIDE_TIME),
            "start_epoch_time": req_body.get('start_epoch_time', 0),
            "end_epoch_time": req_body.get('end_epoch_time', 0),

            "overlap_id": req_body.get('overlap_id', None),
        }

        platform = req_body.get('platform', None)

        if platform:
            content["platform"] = json.dumps(platform)

        user_ids = req_body.get('user_ids', None)

        if user_ids:
            content["user_ids"] = json.dumps(user_ids)

        community_ids = req_body.get('community_ids', None)

        if community_ids:
            content["community_ids"] = json.dumps(community_ids)

        return content

    def _create_banner(self, content):
        banner = MarketingBanner(**content)
        self._save_banner(banner)

    def _save_banner(self, banner):
        banner.save()

    def _update_banner(self, banner_id, content):
        MarketingBanner.objects.filter(pk=banner_id).update(**content)

    def _delete_banner(self, banner_id):
        MarketingBanner.objects.filter(pk=banner_id).delete()

    def _fetch_live_banners(self, start_time, end_time):
        return MarketingBanner.objects.filter(start_epoch_time__lte=start_time,
                                              end_epoch_time__gt=end_time).order_by('-id')

    def _fetch_all_live_banners(self):
        current_time = TimeUtilities.current_time_in_milliseconds()

        return MarketingBanner.objects.filter(end_epoch_time__gt=current_time).order_by('id')

    def _fetch_banner_in_between_time_interval(self, start_time, end_time):
        return MarketingBanner.objects.filter(start_epoch_time__gte=start_time,
                                              end_epoch_time__lte=end_time).order_by('-id')

    def _replace_overlapped_banners(self, banner_list, over_lap_id):

        final_banner_list = []

        for banner in banner_list:

            if banner['id'] == over_lap_id:
                final_banner_list.append(banner)

                return final_banner_list

        return banner_list

    def _is_user_member_of_any_community_in_list(self, banner) -> bool:

        community_id_list = BannerImplUtilities\
            .get_json_from_string_or_raise_exception(banner.community_ids,
                                                     BANNER_JSON_TYPE_COMMUNITY_IDS)
        
        return Members.is_user_community_member_in_community_list(member=self.get_member_id(),
                                                                  community_id_list=community_id_list)

    def _is_user_in_user_ids_list(self, banner) -> bool:
        user_ids = BannerImplUtilities.get_json_from_string_or_raise_exception(banner.user_ids,
                                                                               BANNER_JSON_TYPE_USER_IDS)

        return self.get_member_id() in user_ids

    def _check_platform(self, platform_list) -> bool:
        return self.get_platform_code() in platform_list

    def _fetch_min_app_version(self, banner) -> int:
        min_app_version = 0

        if self.get_platform_code() == platform_codes.ANDROID:
            min_app_version = banner.min_app_version_an

        elif self.get_platform_code() == platform_codes.IOS:
            min_app_version = banner.min_app_version_ios

        return min_app_version

    def _filter_banner_for_user(self, queryset) -> dict:

        over_lap_id = None
        banner_list = []

        for banner in queryset:
            platform_list = BannerImplUtilities.get_json_from_string_or_raise_exception(banner.platform,
                                                                                        BANNER_JSON_TYPE_PLATFORM)

            if self._check_platform(platform_list):
                min_app_version = self._fetch_min_app_version(banner)

                if min_app_version > 0 and\
                        self.get_app_version() < min_app_version:
                    continue

                if banner.user_ids and\
                        not self._is_user_in_user_ids_list(banner):
                    continue

                elif banner.community_ids and\
                        not self._is_user_member_of_any_community_in_list(banner):
                    continue

                if over_lap_id is None:
                    over_lap_id = banner.overlap_id if banner.overlap_id is not None else 0

                banner_list.append(self._serialize_banners(banner, many=False))

        if over_lap_id is not None:
            banner_list = self._replace_overlapped_banners(banner_list, over_lap_id)

        if len(banner_list) > 0:
            return {'banner': banner_list[0]}

        return {}

    def fetch_banner(self) -> dict:
        current_time = TimeUtilities.current_time_in_milliseconds()

        queryset = self._fetch_live_banners(current_time, current_time)

        data = self._filter_banner_for_user(queryset)

        return data

    def fetch_banner_for_cms(self) -> dict:

        queryset = self._fetch_all_live_banners()
        banner_data = self._serialize_banners(queryset)

        return {'banners': banner_data}

    def create_or_update_banner(self, req_body) -> dict:

        content = self._create_banner_content(req_body)

        if 'id' in req_body:
            self._update_banner(req_body['id'], content)

        else:
            self._create_banner(content)

        response = {
            'success': True
        }

        return response

    def remove_banner(self, banner_id) -> dict:

        self._delete_banner(banner_id)

        response = {
            'success': True
        }

        return response

    def check_banner(self, start_time, end_time) -> dict:

        queryset = self._fetch_banner_in_between_time_interval(start_time=start_time,
                                                               end_time=end_time)
        banner_data = self._serialize_banners(queryset)

        return {'banners': banner_data}

    @staticmethod
    def get_upload_uri(path: str) -> dict:

        s3_bucket_name = 'media_bucket'
        bucket = settings.S3_BUCKETS.get(s3_bucket_name)
        if not bucket:
            message = str('RESOURCE_NOT_FOUND cannot find S3 bucket: {bucket_name}')\
                .format(bucket_name=s3_bucket_name)
            error_logger.error(message)
            raise ResourceNotFoundException(status_code=status_codes.HTTP_404_NOT_FOUND,
                                            detail=message)

        multimedia_operations_manager = MultimediaOperationsImpl(bucket)

        return multimedia_operations_manager.generate_presigned_post(path)


class BannerImplUtilities:
    @staticmethod
    def get_json_from_string_or_raise_exception(json_string, json_string_type):
        try:
            return json.loads(json_string)
        except Exception as e:
            response = {
                'success': False,
                'error_message': f' {e.__class__.__name__} - {e.__str__()} in {json_string_type} list'
            }
            raise JsonDecodeException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)
