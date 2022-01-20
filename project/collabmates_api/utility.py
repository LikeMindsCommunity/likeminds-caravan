#file to use utility functions

from django.core.paginator import Paginator

from .static_text import SINGLE_COMMUNITY_VIEW_VERSION_CODE, LM_PLATFORM_CODES, FREE_LINK_VERSION_CODE


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


def get_paginated_queryset_with_maxpages(queryset,page_number,paginate_by=10):

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

    return [] if (max_page < int(page_number) or not queryset) else paginator.get_page(page_number)


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

    elif platform_code == "an" and version_code >= FREE_LINK_VERSION_CODE[platform_code]:
        return True

    elif platform_code == "ios" and version_code >= FREE_LINK_VERSION_CODE[platform_code]:
        return True

    elif platform_code == "web" and version_code >= FREE_LINK_VERSION_CODE[platform_code]:
        return True

    return False
