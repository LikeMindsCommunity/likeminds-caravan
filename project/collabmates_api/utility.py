# file to use utility functions
import re
from django.core.paginator import Paginator

from .static_text import SINGLE_COMMUNITY_VIEW_VERSION_CODE, LM_PLATFORM_CODES, FREE_LINK_VERSION_CODE, \
    DM_CHATROOMS_VERSION_CODE_ANDROID, DM_CHATROOMS_VERSION_CODE_IOS, DM_CHATROOMS_VERSION_CODE_WEB

from external_services.caching.cache_impl import CacheImpl
from utility.cache_keys import (WIDGET_CONFIGURATIONS_CACHE_KEY)

from utility.version_utilities import VersionUtilities
from utility.constants import (WIDGETS_METADATA_CONFIGURATION, FEED_METADATA_CONFIGURATION)


def get_member_id_from_headers(request):
    '''function to get member id from headers'''
    headers = request.META

    member_id = None
    if 'HTTP_X_MEMBER_ID' in headers and 'HTTP_X_VERSION_CODE' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']
    elif 'HTTP_X_MEMBER_ID' in headers:
        member_id = headers['HTTP_X_MEMBER_ID']

    return member_id


def get_platform_code_from_headers(request):
    headers = request.META

    platform_code = 0
    if 'HTTP_X_PLATFORM_CODE' in headers:
        platform_code = headers['HTTP_X_PLATFORM_CODE']

    return platform_code


def is_platform_ios(request):
    platform = get_platform_code_from_headers(request)

    if isinstance(platform, str):
        return platform.lower() == "ios"
    return False


def is_request_web(request):
    '''function to tell if the request is web or not'''

    platform_code = get_platform_code_from_headers(request)
    platform_code = str(platform_code)
    if platform_code == "0" or platform_code.lower() == "web":
        return True

    return False


def get_version_code_from_headers(request):
    headers = request.META

    version_code = None

    if 'HTTP_X_VERSION_CODE' in headers:
        version_code = headers['HTTP_X_VERSION_CODE']

    return version_code


def pagination(queryset, page_number, paginate_by=10):
    '''function to create pagination and return a query set for page number'''
    paginator = Paginator(queryset, paginate_by)
    max_page = len(paginator.page_range)

    return [] if (max_page < int(page_number) or not queryset.exists()) else paginator.get_page(page_number)


def list_pagination(list, page_number, paginate_by=10):
    '''function to create pagination and return a query set for page number'''
    paginator = Paginator(list, paginate_by)
    max_page = len(paginator.page_range)

    return [] if max_page < int(page_number) else paginator.get_page(page_number)


def get_paginated_queryset_with_maxpages(queryset, page_number, paginate_by=10):
    paginator = Paginator(queryset, paginate_by)
    max_page = len(paginator.page_range)
    page_list = [] if (max_page < int(page_number) or not queryset.exists()) else paginator.get_page(page_number)

    temp = {}
    temp['page_list'] = page_list
    temp['last_page'] = paginator.num_pages
    return temp


def get_total_pages(count, limit=10):
    last_digit = count % limit
    if last_digit == 0:
        page_count = int(count / limit)
    else:
        page_count = int(count / limit) + 1

    return page_count


def paginate_list(queryset, page_number, paginate_by=10):
    '''function to create pagination and return a query set for page number'''
    paginator = Paginator(queryset, paginate_by)
    max_page = len(paginator.page_range)

    paginated_queryset = [] if (max_page < int(page_number) or not queryset) else paginator.get_page(page_number)
    total_pages = paginator.num_pages
    total_count = paginator.count

    return paginated_queryset, total_pages, total_count


def single_community_view_version_check(platform_code: str, version_code: int) -> bool:
    if not platform_code or platform_code.lower() not in LM_PLATFORM_CODES:
        return False

    elif platform_code == "an" and version_code >= SINGLE_COMMUNITY_VIEW_VERSION_CODE[platform_code]:
        return True

    elif platform_code == "ios" and version_code >= SINGLE_COMMUNITY_VIEW_VERSION_CODE[platform_code]:
        return True

    elif platform_code == "web" and version_code >= SINGLE_COMMUNITY_VIEW_VERSION_CODE[platform_code]:
        return True

    return False


def free_link_and_freemium_community_version_check(platform_code: str, version_code: int) -> bool:
    if not platform_code or platform_code.lower() not in LM_PLATFORM_CODES:
        return False

    if platform_code in FREE_LINK_VERSION_CODE.keys() and version_code >= FREE_LINK_VERSION_CODE[platform_code]:
        return True

    return False


def create_chatroom_revamp_version_check(platform_code: str, version_code: int) -> bool:
    return VersionUtilities.check_version(platform_code, version_code, VersionUtilities.create_chatroom_revamp)


def m2cm_v2_version_check(platform_code, version_code, is_sdk=False, api_version_code=0):

    if is_sdk:
        platform_code = VersionUtilities.PlatformCode.convert_platform_code_to_sdk(platform_code)

    return VersionUtilities.check_version(platform_code, version_code, VersionUtilities.m2cm_v2,
                                          api_version_code=api_version_code, sdk_source=VersionUtilities.SdkSource.CHAT)


def m2cm_v1_version_check(platform_code, version_code):
    is_enabled = False

    if any([((platform_code == 'ios') and (version_code >= DM_CHATROOMS_VERSION_CODE_IOS)),
            ((platform_code == 'an') and (version_code >= DM_CHATROOMS_VERSION_CODE_ANDROID)),
            ((platform_code == 'web') and (version_code >= DM_CHATROOMS_VERSION_CODE_WEB))]):
        is_enabled = True

    return is_enabled


def is_community_widget_enabled(community_instance, widget_type):
    cache_key = WIDGET_CONFIGURATIONS_CACHE_KEY.format(community_instance.id)

    widget_configurations = CacheImpl.get_cache(cache_key)

    if not widget_configurations:

        from collabmates_api.community.community_impl import CommunityHelper

        widget_configurations_data_list = CommunityHelper.fetch_or_return_default_community_configurations(
            community_instance, [WIDGETS_METADATA_CONFIGURATION])

        widget_configurations_data = widget_configurations_data_list[0] if len(widget_configurations_data_list) else {}

        if widget_configurations_data.get('value'):
            CacheImpl.set_cache(cache_key, widget_configurations_data.get('value'))
            widget_configurations = widget_configurations_data.get('value')

    if widget_configurations.get(widget_type):
        return widget_configurations.get(widget_type)

    return False


def get_feed_metadata_from_community_configurations(community_instance):
    from collabmates_api.community.community_impl import CommunityHelper

    feed_configurations_data_list = CommunityHelper.fetch_or_return_default_community_configurations(
        community_instance, [FEED_METADATA_CONFIGURATION])

    feed_configurations_data = feed_configurations_data_list[0] if len(feed_configurations_data_list) else {}

    if feed_configurations_data.get('value'):
        return feed_configurations_data.get('value')

    return {}


def replace_substring_with_new_words(text, keyword, new_word):
    # Find all occurrences of the old word with re.IGNORECASE flag
    matches = re.finditer(re.escape(keyword), text, re.IGNORECASE)

    # Iterate through matches
    replaced_str = text

    for match in matches:
        # Get the matched word
        matched_word = match.group(0)

        # Determine if the matched word is capitalized
        is_capitalized = matched_word[0].isupper()

        # Replace the matched word with the new word while maintaining capitalization
        if is_capitalized:
            new_word = new_word.capitalize()

        replaced_str = replaced_str[:match.start()] + new_word + replaced_str[match.end():]

    return replaced_str
