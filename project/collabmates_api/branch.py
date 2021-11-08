import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from urllib.parse import urlparse

from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import Community
from .static_files import *
from utility.constants import (BRANCH_QUICKLINK_URI, DIRECTORY_FEATURE,
                               BRANCH_FEATURE_DIRECTORY_LINK, BRANCH_FEATURE_PRIVATE_LINK, BRANCH_FEATURE_PUBLIC_LINK,
                               BRANCH_FEATURE_COMMUNITY_OTL_URL, BRANCH_FEATURE_PAYMENT_PAGE_URL)
from utility.api_client import ApiClient

info_logger = LoggingWrapper.get_instance()


def strip_scheme(url):
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1)


host_url = strip_scheme(settings.URL)
web_host_url = strip_scheme(settings.WEB_URL)
api_endpoint = BRANCH_QUICKLINK_URI % settings.BRANCH_KEY


def create_community_branch_links(community_id, member_id, aj=None):
    """
    This will return 2 links in case of member and 3 in case of a owner or promoter
    For public
        0 => public community share link
        1 => public member directory share link
        2 => public community share link to download app
    For owner/promoter
        0 => public community share link
        1 => private community share link
        2 => private member directory share link
    """

    if isinstance(community_id, Community):
        community_instance = community_id
    else:
        community_instance = get_object_or_404(Community, pk=community_id)

    data = []

    base_url = f'{host_url}/community/{community_instance.id}'

    # create public url
    if member_id:
        public_url = base_url + f'?shared_by={member_id}'

        if community_instance.is_paid and community_instance.website_url:
            website_url = strip_scheme(community_instance.website_url)
            public_url = website_url + f'?shared_by={member_id}'

    else:
        public_url = base_url

    long_url_item = create_link_item(public_url, community_instance, "AppBackend", "CommunityPublic")
    data.append(long_url_item)

    if aj:
        # if the user is owner or promoter
        # create private link
        if member_id:
            private_url = base_url + f'?shared_by={member_id}&aj={aj}'

        else:
            private_url = base_url + f'?aj={aj}'

        long_url_item = create_link_item(private_url, community_instance, "AppBackend", "CommunityPrivate", private=True)
        data.append(long_url_item)

        directory_url = base_url + f'?aj={aj}&source=members_directory'

        if member_id:
            directory_url += f'&shared_by={member_id}'

        long_url_item = create_link_item(directory_url, community_instance, "AppBackend", DIRECTORY_FEATURE, private=True)
        data.append(long_url_item)

    else:
        # adding member directory urls when user is part of the community
        directory_url = base_url + '?source=members_directory'

        if member_id:
            directory_url += f'&shared_by={member_id}'

        long_url_item = create_link_item(directory_url, community_instance, "AppBackend", DIRECTORY_FEATURE)
        data.append(long_url_item)

        # creating private expired link for non logged in user
        private_expired_link = base_url + '?aj=1234'

        if member_id:
            private_expired_link += f'&shared_by={member_id}'

        long_url_item = create_link_item(private_expired_link, community_instance, "AppBackend", "Web download button", private=True)
        data.append(long_url_item)

    # API request
    r = requests.post(url=api_endpoint, json=data)

    # handle errors by branch . it return 'error in case the url is made'
    if r.status_code != 200:
        data = [{}, {}, {}]
        info_logger.info("Branch failed, sending normal links")

    else:
        data = r.json()

    if 'url' not in data[0]:
        data[0]['url'] = base_url + f'?shared_by={member_id}'

        if community_instance.is_paid and community_instance.website_url:
            data[0]['url'] = community_instance.website_url + f'?shared_by={member_id}'

    if 'url' not in data[1]:
        data[1]['url'] = base_url + f'?shared_by={member_id}'

        if aj:
            data[1]['url'] += f'&aj={aj}'

    if 'url' not in data[2]:
        data[2]['url'] = base_url + f'?shared_by={member_id}&source=members_directory'

        if aj:
            data[2]['url'] += f'&aj={aj}'

    return data


def get_community_image(community):
    if community.image_link:
        return community.image_link
    elif community.image_url:
        return community.image_url.url
    else:
        return APP_LOGO


def create_link_item(base_url, community, channel, feature, private=False):
    link_item = {
        "channel": channel,
        "feature": feature,
        "data": {
            # '$deeplink_path':'likeminds://%s'%(base_url),
            '$android_deeplink_path': 'likeminds://%s' % base_url,
            # '$ios_deeplink_path':'likeminds://%s'%(base_url),
            '$deep_link': 'likeminds://%s' % base_url,
            '$og_title': '%s on LikeMinds' % community.name,
            '$og_description': community.purpose,
            '$og_image_url': get_community_image(community),
            '$og_image_width': 554,
            '$og_image_height': 554,
            '$og_url': 'likeminds.community',
            '$uri_redirect_mode': 1,
        }
    }

    fallback_url = desktop_url = 'https://%s' % base_url

    if community.is_paid and feature == BRANCH_FEATURE_PUBLIC_LINK:
        link_item["data"]['$web_only'] = True
        link_item["data"]['$ios_url'] = fallback_url
        link_item["data"]['$android_url'] = fallback_url
        link_item["data"]['$android_deeplink_path'] = fallback_url

    """
    redirect to web in case of member directory 
    download app in all other cases(public + private)
    """

    if community.is_paid:
        if feature != BRANCH_FEATURE_PRIVATE_LINK \
                and feature != BRANCH_FEATURE_COMMUNITY_OTL_URL:
            link_item['data']['$fallback_url'] = fallback_url
        else:
            link_item['data']['$desktop_url'] = desktop_url

    else:
        if feature == DIRECTORY_FEATURE:
            link_item['data']['$fallback_url'] = fallback_url
        else:
            link_item['data']['$desktop_url'] = desktop_url

    if feature == BRANCH_FEATURE_PAYMENT_PAGE_URL:
        link_item["data"]['$web_only'] = True
        link_item['data']['$fallback_url'] = fallback_url
        link_item['data']['$desktop_url'] = desktop_url

    return link_item


def create_community_feed_url(community_instance):

    data = []

    feed_url = f'{host_url}/community_feed?community_id={community_instance.id}'

    long_url_item = create_link_item(feed_url, community_instance, "AppBackend", "CommunityFeed", private=True)
    data.append(long_url_item)

    client = ApiClient()
    client.update_request_url(api_endpoint)
    client.update_body(data)
    client.post()

    if client.fetch_response_code() != 200:
        data = [{}]
        info_logger.info("Branch failed, sending normal links")
    else:
        data = client.fetch_response()

    # in case branch fails
    if 'url' not in data[0]:
        data[0]['url'] = f'https://{feed_url}'

    return data[0]['url']


def create_community_otl_url(community_instance, payment_id, shared_by=None):

    data = []

    base_url = f'{host_url}/community/{community_instance.id}'

    if payment_id and shared_by:
        private_url = base_url + f'?shared_by={shared_by}&payment_id={payment_id}'

    else:
        private_url = base_url + f'?payment_id={payment_id}'

    long_url_item = create_link_item(private_url, community_instance, "AppBackend", BRANCH_FEATURE_COMMUNITY_OTL_URL, private=True)
    data.append(long_url_item)

    client = ApiClient()
    client.update_request_url(api_endpoint)
    client.update_body(data)
    client.post()

    if client.fetch_response_code() != 200:
        data = [{}]
        info_logger.info("Branch failed, sending normal links")
    else:
        data = client.fetch_response()

    # in case branch fails
    if 'url' not in data[0]:
        data[0]['url'] = f'https://{private_url}'

    return data[0]['url']


def create_payment_page_url(community_instance, payment_id):

    data = []

    base_url = f'{web_host_url}/payment_page'

    private_url = base_url + f'?payment_page_id={payment_id}'

    long_url_item = create_link_item(private_url, community_instance, "AppBackend", BRANCH_FEATURE_PAYMENT_PAGE_URL)
    data.append(long_url_item)

    client = ApiClient()
    client.update_request_url(api_endpoint)
    client.update_body(data)
    client.post()

    if client.fetch_response_code() != 200:
        data = [{}]
        info_logger.info("Branch failed, sending normal links")
    else:
        data = client.fetch_response()

    # in case branch fails
    if 'url' not in data[0]:
        data[0]['url'] = f'https://{private_url}'

    return data[0]['url']
