import requests
from django.conf import settings
from togther.models import Community
from django.shortcuts import get_object_or_404
from .static_files import *
from .utilities.constants import BRANCH_QUICKLINK_URI

host_url = settings.URL


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

    d = {
        "channel": "AppBackend",
        "feature": "CommunityPublic",
        "data": {
            # '$deeplink_path':'likeminds://%s'%(base_url),
            '$android_deeplink_path': 'Likeminds://%s' % base_url,
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
    data.append(d)
    if aj:
        # if the user is owner or promoter
        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&aj=%s' % (
                host_url, str(community.id), str(shared_by_id), str(aj))
        else:
            base_url = '%s/community?community_id=%s&aj=%s' % (
                host_url, str(community.id), str(aj))
        d = {
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
        data.append(d)

        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&aj=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id), str(aj))
        else:
            base_url = '%s/community?community_id=%s&aj=%s&source=members_directory' % (
                host_url, str(community.id), str(aj))
        d = {
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
        data.append(d)
    else:
        # adding memberdirectory usrl when user is part of the community
        if shared_by_id:
            base_url = '%s/community?community_id=%s&shared_by=%s&source=members_directory' % (
                host_url, str(community.id), str(shared_by_id))
        else:
            base_url = '%s/community?community_id=%s&source=members_directory' % (
                host_url, str(community.id))
        d = {
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
        data.append(d)
    r = requests.post(url=api_endpoint, json=data)
    data = r.json()
    return data


def get_community_image(community):
    if community.image_link:
        return community.image_link
    elif community.image_url:
        return community.image_url.url
    else:
        return APP_LOGO
