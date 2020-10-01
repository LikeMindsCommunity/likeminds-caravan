from urllib.parse import parse_qsl, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from togther.models import (Collabcard, Community, Members, card_answers)
from utility.states import member_states, card_types, chatroom_states
from utility.utils import get_community_members_count_for_preview
from .serializers import get_chatroom_instance, get_member_images_of_chatroom
from .static_text import *

url = settings.URL


def get_preview_for_url(member_id=None, preview_url=None,
                        community_instance=None, chatroom_instance=None, send_preview_text=True):
    """ function to get preview of community or chatroom """

    user_instance = User.objects.get(pk=member_id)

    is_member_directory = False
    preview_type = None
    preview_text = None
    title = None
    route = None
    aj = None
    source_id = None
    chatroom_id = None
    community_id = None

    if preview_url:
        parsed_url = urlsplit(preview_url)
        query_items = dict(parse_qsl(parsed_url.query))

        if "community" in parsed_url.path:
            if 'source' in query_items and query_items['source'] == 'members_directory':
                is_member_directory = True
                preview_type = "directory"
                title = "Follow the link to join this LikeMinds community and view its member's profiles"
                preview_text = "Preview of directory will be added later"
            else:
                preview_type = "community"
                title = "Follow the link to join this LikeMinds community."
                preview_text = "Preview of community will be added later"
            community_id = parsed_url.path.split("/")[-1]

        elif "collabcard" in parsed_url.path:
            preview_type = "chatroom"
            preview_text = "Preview of chat room will be added later"
            chatroom_id = parsed_url.path.split("/")[-1]

        if 'aj' in query_items:
            aj = query_items['aj']
        if 'source_id' in query_items:
            source_id = query_items['source_id']

    context = {"preview_type": preview_type}
    if send_preview_text:
        context = {"internal_link": preview_url, "preview_type": preview_type,
                   "preview_text": preview_text, "title": title}

    if chatroom_id:
        if not chatroom_instance:
            chatroom_instance = Collabcard.objects.get(pk=chatroom_id)

        community_instance = chatroom_instance.community
        community_id = community_instance.id

        chatroom = get_chatroom_preview(chatroom_instance, member_id)
        context["chatroom"] = chatroom

        title = f'Participate in this LikeMinds chat room in community. "{community_instance.name}"'
        route = f"route://collabcard?collabcard_id={chatroom_id}"

    if send_preview_text:
        context["title"] = title

    if community_id:
        if not community_instance:
            community_instance = Community.objects.get(pk=community_id)

        community = get_community_preview(community_instance, user_instance)
        context["community"] = community
        is_member = community["member_state"] in [1, 2, 3, 4, 7, 9]

        if is_member_directory and is_member:
            context["action"] = "VIEW DIRECTORY"
            route = f"route://members_directory?community_id={community_id}&community_name={community_instance.name}"
        elif is_member and not chatroom_id:
            route = f"route://community?community_id={community_id}"
            context["action"] = "VIEW COMMUNITY"
        elif not chatroom_id:
            route = f"route://community?community_id={community_id}"
            context["action"] = "JOIN COMMUNITY"
        else:
            context["action"] = "JOIN COMMUNITY"

    if chatroom_id:
        if chatroom_instance.type == card_types.CARD_EVENT or chatroom_instance.type == card_types.CARD_PUBLIC_EVENT:
            context["action"] = "VIEW EVENT"
            if send_preview_text:
                context["preview_text"] = "Preview of the event will be added later"
        elif chatroom_instance.type == card_types.CARD_POLL:
            context["action"] = "VIEW POLL"
            if send_preview_text:
                context["preview_text"] = "Preview of the poll will be added later"
        else:
            context["action"] = "VIEW CHAT ROOM"

    if aj:
        route = route + f"&aj={aj}"

    if source_id:
        route = route + f"&source_id={source_id}"

    context["action_route"] = route

    return context


def get_community_preview(community_instance, user_instance):
    community = {"id": community_instance.id,
                 "name": community_instance.name,
                 "purpose": community_instance.purpose,
                 }

    if community_instance.image_link:
        community['image_url'] = community_instance.image_link
    elif community_instance.image_url:
        community['image_url'] = community_instance.image_url.url
    else:
        community['image_url'] = '/media/media/community/default.jpeg'

    if community_instance.image_link_round:
        community['image_url_round'] = community_instance.image_link_round

    if community['image_url'] == "/media/https%3A/upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg":
        community[
            'image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn' \
                           ':ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO '
    elif not community_instance.image_link:
        community['image_url'] = url + community['image_url']

    community_members = get_community_members_count_for_preview(community_instance, user_instance)

    community.update(**community_members)

    return community


def get_chatroom_preview(card_instance, member_id, active=None):
    """ function to get chatrooms """

    chatroom_instance = get_chatroom_instance(card_instance, member_id)
    conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                      state=chatroom_states.ANSWER).order_by('id')
    chatroom_instance['total_response_count'] = conversation_filter.count()

    if card_instance.internal_link:
        chatroom_instance['preview'] = get_preview_for_url(member_id, card_instance.internal_link,
                                                           community_instance=card_instance.preview_community,
                                                           chatroom_instance=card_instance.preview_chatroom,
                                                           send_preview_text=False)

    last_response_members = get_member_images_of_chatroom(conversation_filter)
    chatroom_instance['members_images'] = last_response_members['members_images']
    chatroom_instance['last_response_members'] = last_response_members['last_response_members']

    return chatroom_instance


