import logging
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404

from togther.models import Community
from .static_files import *
from .utilities.constants import BRANCH_QUICKLINK_URI

host_url = settings.URL
info_logger = logging.getLogger("info_logger")


def create_community_branch_links(community_id, shared_by_id, aj=None):

    """
    This will return 2 links in case of member and 3 in case of a owner or promoter
    For public
        0 => public community share link
        1 => public member directory share link
    For owner/promoter
        0 => public community share link
        1 => private community share link
        2 => private member directory share link
    """

    community = get_object_or_404(Community, pk=community_id)

    api_endpoint = BRANCH_QUICKLINK_URI % settings.BRANCH_KEY
    data = []

    if shared_by_id:
        base_url = '%s/community?community_id=%s&shared_by=%s' % (host_url, str(community.id), str(shared_by_id))
    else:
        base_url = '%s/community?community_id=%s' % (host_url, str(community.id))

    long_url_item = {
        "channel": "AppBackend",
        "feature": "CommunityPublic",
        "data": {
            # '$deeplink_path':'likeminds://%s'%(base_url),
            '$android_deeplink_path': 'likeminds://%s' % base_url,
            # '$ios_deeplink_path':'Likeminds://%s'%(base_url),
            '$deep_link': 'collabmates://%s' % base_url,
            '$og_title': '%s on LikeMinds' % community.name,
            '$og_description': community.purpose,
            '$og_image_url': get_community_image(community),
            '$og_image_width': 554,
            '$og_image_height': 554,
            '$og_url': 'likeminds.community',
            '$uri_redirect_mode': 1,
            '$fallback_url': 'https://%s' % base_url,
        }
    }
    data.append(long_url_item)
    if aj:
        # if the user is owner or promoter
        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&aj=%s' % (
                host_url, str(community.id), str(shared_by_id), str(aj))
        else:
            base_url = '%s/community?community_id=%s&aj=%s' % (
                host_url, str(community.id), str(aj))
        long_url_item = {
            "channel": "AppBackend",
            "feature": "CommunityPrivate",
            "data": {
                # '$deeplink_path':'likeminds://%s'%(base_url),
                '$android_deeplink_path': 'likeminds://%s' % base_url,
                # '$ios_deeplink_path':'likeminds://%s'%(base_url),
                '$deep_link': 'collabmates://%s' % base_url,
                '$og_title': '%s on LikeMinds' % community.name,
                '$og_description': community.purpose,
                '$og_image_url': get_community_image(community),
                '$og_image_width': 554,
                '$og_image_height': 554,
                '$og_url': 'likeminds.community',
                '$uri_redirect_mode': 1,
                '$fallback_url': 'https://%s' % base_url,
            }
        }
        data.append(long_url_item)

        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&aj=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id), str(aj))
        else:
            base_url = '%s/community?community_id=%s&aj=%s&source=members_directory' % (
                host_url, str(community.id), str(aj))
        long_url_item = {
            "channel": "AppBackend",
            "feature": "Community Members Directory",
            "data": {
                # '$deeplink_path':'likeminds://%s'%(base_url),
                '$android_deeplink_path': 'likeminds://%s' % base_url,
                # '$ios_deeplink_path':'likeminds://%s'%(base_url),
                '$deep_link': 'collabmates://%s' % base_url,
                '$og_title': '%s on LikeMinds' % community.name,
                '$og_description': community.purpose,
                '$og_image_url': get_community_image(community),
                '$og_image_width': 554,
                '$og_image_height': 554,
                '$og_url': 'likeminds.community',
                '$uri_redirect_mode': 1,
                '$fallback_url': 'https://%s' % base_url,
            }
        }
        data.append(long_url_item)
    else:
        # adding memberdirectory usrl when user is part of the community
        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id))
        else:
            base_url = '%s/community?community_id=%s&source=members_directory' % (
                host_url, str(community.id))
        long_url_item = {
            "channel": "AppBackend",
            "feature": "Community Members Directory",
            "data": {
                # '$deeplink_path':'likeminds://%s'%(base_url),
                '$android_deeplink_path': 'likeminds://%s' % base_url,
                # '$ios_deeplink_path':'likeminds://%s'%(base_url),
                '$deep_link': 'collabmates://%s' % base_url,
                '$og_title': '%s on LikeMinds' % community.name,
                '$og_description': community.purpose,
                '$og_image_url': get_community_image(community),
                '$og_image_width': 554,
                '$og_image_height': 554,
                '$og_url': 'likeminds.community',
                '$uri_redirect_mode': 1,
                '$fallback_url': 'https://%s' % base_url,
            }
        }
        data.append(long_url_item)
    r = requests.post(url=api_endpoint, json=data)
    data = r.json()

    # handeling errors by brach . it return 'error in case the url is made'
    if r.status_code != 200:
        data = [{}, {}, {}]
        info_logger.info("Branch failed, sending normal links")
    if aj:
        if 'url' not in data[0]:
            data[0]['url'] = '%s/community?community_id=%s&shared_by=%s' % (
                host_url, str(community.id), str(shared_by_id))

        if 'url' not in data[1]:
            data[0]['url'] = '%s/community?community_id=%s&shared_by=%s&aj=%s' % (
                host_url, str(community.id), str(shared_by_id), str(aj))

        if 'url' not in data[2]:
            data[0]['url'] = '%s/community?community_id=%s&shared_by=%s&aj=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id), str(aj))
    else:
        if 'url' not in data[0]:
            data[0]['url'] = '%s/community?community_id=%s&shared_by=%s' % (
                host_url, str(community.id), str(shared_by_id))

        if 'url' not in data[1]:
            data[0]['url'] = '%s/community?community_id=%s&shared_by=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id))

    return data


def get_community_image(community):
    if community.image_link:
        return community.image_link
    elif community.image_url:
        return community.image_url.url
    else:
        return APP_LOGO
