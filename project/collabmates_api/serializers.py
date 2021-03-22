import json
from urllib.parse import parse_qsl, urlsplit

from django.conf import settings
from django.db.models import Q

from external_services.caching.cache_impl import CacheImpl
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import *
from utility.utils import is_IG_community, is_LG_or_LP_community, feedback_community_id, \
    generate_private_link, generate_random, get_time_text, eligibility_count, get_members_count_in_community, \
    is_member_promoter, generate_private_link_for_chatroom, get_date_time_from_timestamp, \
    get_community_members_count_for_preview

from utility.states import (card_types, question_states, member_states, poll_types,
                            deleted_members, manager_rights, member_rights, chatroom_states)
from .user_moderation_rights import *
import time

import ast
from .static_files import *
from .static_text import months_semi
from .user_moderation_rights import check_member_invite_private_right, check_admin_view_contact_right
from .branch import create_community_branch_links
from utility.constants import *
from utility.number_utilities import NumberUtilities
error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
url = settings.URL


def CommunitySerializer(community, promoter_id=0, is_owner=False,
                        current_user_id=None, current_user_instance=None):
    # function to serialize a community object
    new_dict = {
        'id': community.id,
        'name': community.name,
        'purpose': community.purpose,
        'location': community.location if community.location else "",

    }

    if not current_user_instance and current_user_id:
        current_user_instance = User.objects.get(pk=current_user_id)

    user_has_share_permission = False

    if current_user_instance:
        user_has_share_permission = check_member_invite_private_right(current_user_instance, community)

    # user is logged in and is a promoter or an owner or has rights.
    if promoter_id or is_owner or user_has_share_permission:
        # public and private links
        aj = private_link = generate_private_link(community_instance=community, promoter_instance=current_user_instance,
                                                  just_send_aj=True)
        branch_links = create_community_branch_links(community.id, current_user_id, aj)
    else:
        # only public link
        branch_links = create_community_branch_links(community.id, current_user_id)
    if community.about:
        new_dict['about'] = community.about

    if community.image_link:
        new_dict['image_url'] = community.image_link
    elif community.image_url:
        new_dict['image_url'] = community.image_url.url
    else:
        new_dict['image_url'] = '/media/media/community/default.jpeg'

    if community.image_link_round:
        new_dict['image_url_round'] = community.image_link_round

    if new_dict['image_url'] == "/media/https%3A/upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg":
        new_dict[
            'image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
    elif not community.image_link:
        new_dict['image_url'] = url + new_dict['image_url']
    new_dict['is_member'] = ''

    new_dict['share_url'] = branch_links[0]['url']

    new_dict['date'] = community.active_since
    new_dict['members_count'] = get_members_count_in_community(community.id)
    new_dict['state'] = int(community.hide_community)

    # generating private link
    if promoter_id or is_owner:
        new_dict['private_link'] = branch_links[1]['url']
        if new_dict['members_count'] <= 10:
            new_dict[
                'private_link_text_admin'] = PRIVATE_LINK_TEXT_ADMIN_1 % (community.name, branch_links[1]['url'])
        else:
            new_dict[
                'private_link_text_admin'] = PRIVATE_LINK_TEXT_ADMIN_2 % (community.name, branch_links[1]['url'])

        new_dict['private_link_members_directory'] = branch_links[2]['url']

        if is_owner:
            private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_1 % (
            community.name, branch_links[2]['url'])

        else:
            private_link_text_members_directory = PRIVATE_LINK_TEXT_MEMBERS_DIRECTORY_2 % (
            community.name, branch_links[2]['url'])

        new_dict[
            'private_link_text_members_directory'] = private_link_text_members_directory

    elif current_user_instance:

        if user_has_share_permission:
            # private_link = generate_private_link(community_instance=community,
            #                                      promoter_instance=current_user_instance)

            new_dict[
                'private_link_text_member'] = PRIVATE_LINK_FOR_PERMITTED_USER % (community.name, branch_links[1]['url'])

            # private_link_members_directory = branch_links[1]['url']
            new_dict[
                'members_directory_link_for_members'] = MEMBER_DIRECTORY_LINK_FOR_PERMITTED_USER % (
            community.name, branch_links[2]['url'])

    if community.type:
        new_dict['type'] = community.type
    if community.sub_type:
        new_dict['sub_type'] = community.sub_type

    new_dict[
        'share_text_admin'] = SHARE_TEXT_ADMIN % (new_dict['name'], new_dict['purpose'], new_dict['share_url'])

    new_dict[
        'share_text_member'] = """I am part of %s community on LikeMinds.\n %s \nApply to join our community. %s\n""" % (
        new_dict['name'], new_dict['purpose'], new_dict['share_url'])

    new_dict[
        'share_text_anonymous'] = """I recently discovered %s community on LikeMinds. You can join this community using this link.\n""" % (
        new_dict['name'])

    new_dict['min_referrer_member'] = eligibility_count

    return new_dict


def UserinfoSerializer(user):
    # function to serialize a userinfo object
    # if the community is not feedback community
    userinfo = {
        'id': user.user_id.id,
        "name": user.name,
        # "email": user.email,
        # "city": user.city,
        # "headline": user.headline,
        # "contact_number": user.contact_number,
        # "about": user.about,
        # "fb_link": user.fb_link,
        # "linkedin_link": user.linkedin_link,
    }

    if user.image_link:
        userinfo['image_url'] = user.image_link

    return userinfo


def get_logged_in_user(user_instance):
    context = UserinfoSerializer(user_instance.userinfo)

    email_filter = userEmails.objects.filter(user=user_instance)

    email_list = []
    for email in email_filter:
        email_list.append(userEmailsSerializer(email))

    # if not email_list:
    #     email = user_instance.userinfo.email
    #     if email:
    #         email_list.append(email)

    mobile_filter = userMobiles.objects.filter(user=user_instance)

    mobile_list = []

    for mobile_no in mobile_filter:
        mobile_list.append(userMobilesSerializer(mobile_no))

    if email_list:
        context['emails'] = email_list
    if mobile_list:
        context['mobiles'] = mobile_list

    return context


def CollabcardSerializer(card, user, community=None, current_user_id=None, preview=False):
    # function to serialize a community object
    collabcard = {
        'id': card.id,
        'title': card.title,
        'community_id': card.community_id,
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count': card.image_count,
        'pdf_count': card.pdf_count,
        'video_count': card.video_count,
        'audio_count': card.audio_count,
        'attachment_count': card.attachment_count,
        'attachments_uploaded': card.attachments_uploaded,
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        "is_pending": card.is_pending,
        'answers_count': card.answers_count,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count,
        'card_creation_time': TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(card.date_epoch),
        "community_name": card.community.name,
        "date": TimeUtilities.convert_epoch_time_in_date(card.date_epoch),
        "created_at": TimeUtilities.convert_epoch_time_in_hh_mm(card.date_epoch),
        "date_epoch": card.date_epoch,
        'is_secret': card.is_secret,
    }

    if card.secret_chatroom_participants:
        collabcard['secret_chatroom_participants'] = json.loads(card.secret_chatroom_participants)

    if card.attachments_uploaded is None:
        collabcard['attachments_uploaded'] = False

    if user and int(user) == card.user.id:
        collabcard['has_been_named'] = card.has_been_named
        collabcard['member_id'] = card.user.id

    if card.community.image_link_round:
        collabcard['image_url_round'] = card.community.image_link_round

    # for poll card
    if card.type == card_types.CARD_POLL:
        polls = []
        card_polls = CollabcardPolls.objects.filter(card=card).order_by('id')
        for poll in card_polls:
            polls.append(CollabcardPollsSerializer(poll, user, card))

        collabcard["answer_text"] = get_answer_text_for_poll(card, current_user_id)
        collabcard['polls'] = polls
        collabcard['expiry_time'] = card.end_date

        if card.multiple_select:
            collabcard['multiple_select'] = card.multiple_select
        if card.multiple_select_no is not None:
            collabcard['multiple_select_no'] = card.multiple_select_no
        if card.multiple_select_state is not None:
            collabcard['multiple_select_state'] = card.multiple_select_state

        collabcard['is_anonymous'] = card.is_poll_anonymous
        collabcard['allow_add_option'] = card.allow_add_option
        collabcard['poll_type'] = card.poll_type
        collabcard[
            'poll_type_text'] = "Instant poll" if card.poll_type == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
        collabcard['submit_type_text'] = "Secret voting" if card.is_poll_anonymous else "Public voting"

    # for event card
    if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT or card.type == card_types.CARD_POLL:
        if card.location:
            collabcard['location'] = card.location

        if card.location_lat:
            collabcard['location_lat'] = card.location_lat

        if card.location_long:
            collabcard['location_long'] = card.location_long

        if card.start_date:
            collabcard['start_date'] = card.start_date

        if card.end_date:
            collabcard['end_date'] = card.end_date

        if card.about:
            collabcard['about'] = card.about

        if card.co_hosts:
            co_host_list = json.loads(card.co_hosts)
            # co_host_list = [36]
            # print(user)
            if not user:
                user = None

            collabcard['co_hosts'] = get_members_profile(member_ids=co_host_list, community_id=card.community.id,
                                                         current_user_id=user)

        if card.online_link:
            collabcard['online_link'] = card.online_link

    # for sending header
    if card.header:
        collabcard['header'] = card.header
    else:

        if len(collabcard['title']) <= 30:
            collabcard['header'] = card.title[:30]
        else:
            collabcard['header'] = card.title[:27] + "..."

    if card.og_tags:
        og_tags = json.loads(card.og_tags)
        collabcard['og_tags'] = og_tags

    # FOR PURPOSE CARD
    if card.updated_member:
        member_ids = [card.updated_member]
        temp = get_members_profile(member_ids=member_ids, community_id=card.community_id,
                                   current_user_id=user, send_profile=False)
        collabcard['updated_member'] = temp[0]

    if card.is_deleted:
        member_ids = [card.deleted_by_user]
        temp = get_members_profile(member_ids=member_ids, community_id=card.community_id,
                                   current_user_id=user, send_profile=False)
        member_obj = temp[0]
        member_obj['community_id'] = card.community.id
        member_obj['chatroom_id'] = card.id
        collabcard['deleted_by_member'] = member_obj
        collabcard['deleted_by'] = card.deleted_by_user.id

    if card.updated_time:
        collabcard['updated_time'] = get_time_text(card.updated_time)

    if not preview:
        share = get_share_url_text(card, user)
        collabcard['share_url'] = share['share_url']
        collabcard['creator_share_url'] = share['creator_share_url']
        collabcard['link_created_at'] = share['link_created_at']
        collabcard['chatroom_category'] = get_category_of_chatroom(card.type)

    return collabcard


def draftChatroomSerializer(card, user, community=None):
    # function to serialize a community object
    chatroom = {
        'id': card.id,
        'title': card.title,
        'community_id': card.community_id,
        # 'share_url': url + '/collabcard/' + str(card.id), #+ "?ref_id=" + str(card.user.id),
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count': card.image_count,
        'pdf_count': card.pdf_count,
        'video_count': card.video_count,
        'audio_count': card.audio_count,
        'attachment_count': card.attachment_count,
        'attachments_uploaded': card.attachments_uploaded,
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count,
        'card_creation_time': TimeUtilities.convert_epoch_time_in_date(card.date_epoch),
        'created_at': TimeUtilities.convert_epoch_time_in_hh_mm(card.date_epoch),
        'community_name': card.community.name,
        'is_secret': card.is_secret,
    }

    if card.secret_chatroom_participants:
        chatroom['secret_chatroom_participants'] = json.loads(card.secret_chatroom_participants)

    if card.attachments_uploaded is None:
        chatroom['attachments_uploaded'] = False

    # for poll card
    if card.type == card_types.CARD_POLL:
        polls = []
        cardPolls = draftPolls.objects.filter(draft=card).order_by('id')
        for poll in cardPolls:
            polls.append(draftPollsSerializers(poll))

        chatroom['polls'] = polls

        if card.multiple_select:
            chatroom['multiple_select'] = card.multiple_select

        chatroom['expiry_time'] = card.end_date
        chatroom['multiple_select_no'] = card.multiple_select_no
        chatroom['multiple_select_state'] = card.multiple_select_state

        chatroom['is_anonymous'] = card.is_poll_anonymous
        chatroom['allow_add_option'] = card.allow_add_option
        chatroom['poll_type'] = card.poll_type
        chatroom[
            'poll_type_text'] = "Instant poll" if card.poll_type == poll_types.POLL_TYPE_INSTANT else "Deferred poll"
        chatroom['submit_type_text'] = "Secret voting" if card.is_poll_anonymous else "Public voting"

    # for event card
    if card.type == card_types.CARD_EVENT or card.type == card_types.CARD_PUBLIC_EVENT or card.type == card_types.CARD_POLL:
        if card.location:
            chatroom['location'] = card.location

        if card.location_lat:
            chatroom['location_lat'] = card.location_lat

        if card.location_long:
            chatroom['location_long'] = card.location_long

        if card.start_date:
            chatroom['start_date'] = card.start_date

        if card.end_date:
            chatroom['end_date'] = card.end_date

        if card.about:
            chatroom['about'] = card.about

        if card.co_hosts:
            co_host_list = json.loads(card.co_hosts)
            if not user:
                user = None

            chatroom['co_hosts'] = get_members_profile(member_ids=co_host_list, community_id=card.community.id,
                                                       current_user_id=user)

        if card.online_link:
            chatroom['online_link'] = card.online_link

        if card.internal_link:
            chatroom['internal_link'] = card.internal_link

    # for sending header
    if card.header:
        chatroom['header'] = card.header
    else:
        chatroom['header'] = card.title[:30]

    if card.og_tags:
        og_tags = json.loads(card.og_tags)
        chatroom['og_tags'] = og_tags

    polls = []
    cardPolls = draftPolls.objects.filter(draft=card).order_by('id')
    for poll in cardPolls:
        polls.append(draftPollsSerializers(poll))

    chatroom['polls'] = polls

    draft_files = get_collabcard_files(card_id=card, draft=True)
    chatroom['images'] = draft_files[0]
    chatroom['pdf'] = draft_files[1]
    chatroom['audios'] = draft_files[2]
    chatroom['videos'] = draft_files[3]
    chatroom['attachments'] = draft_files[4]

    return chatroom


def get_collabcard_files(card_id, draft=False):
    '''function to return pdf and image files of a collabcard'''

    if not draft:
        files = Card_Attachment.objects.filter(collabcard=card_id)
    else:
        files = draftChatroomFiles.objects.filter(draft=card_id)
    img_list = []
    pdf = []
    video_list = []
    audio_list = []

    attachments = []

    for file in files:
        if file.type == 'image':
            img = {'image_url': file.file_url, 'index': file.index, 'type': file.type}
            img_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

            if file.dimensions:
                img['dimensions'] = json.loads(file.dimensions)
                img_attachment['dimensions'] = json.loads(file.dimensions)

            if file.height:
                img['height'] = file.height
                img_attachment['height'] = file.height

            if file.width:
                img['width'] = file.width
                img_attachment['width'] = file.width

            if file.thumbnail_url:
                img['thumbnail_url'] = file.thumbnail_url
                img_attachment['thumbnail_url'] = file.thumbnail_url

            img_list.append(img)
            attachments.append(img_attachment)

        elif file.type == 'video':
            video_url = {'video_url': file.file_url, 'index': file.index, 'type': file.type}
            video_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

            if file.height:
                video_url['height'] = file.height
                video_attachment['height'] = file.height

            if file.width:
                video_url['width'] = file.width
                video_attachment['width'] = file.width

            if file.thumbnail_url:
                video_url['thumbnail_url'] = file.thumbnail_url
                video_attachment['thumbnail_url'] = file.thumbnail_url

            video_list.append(video_url)
            attachments.append(video_attachment)

        elif file.type == 'audio':
            if file.file_url:
                audio_url = {'audio_url': file.file_url, 'index': file.index, 'type': file.type}
            else:
                audio_url = {'audio_url': url + file.attachment.url, 'index': file.index}
            audio_list.append(audio_url)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url, 'index': file.index, 'type': file.type}
            else:
                pdf_url = {'pdf_file': url + file.attachment.url, 'index': file.index}
            pdf.append(pdf_url)

    return img_list, pdf, audio_list, video_list, attachments


def get_share_url_text(card, user_id):
    '''function to share url text'''

    share = {}
    share['link_created_at'] = get_date_time_from_timestamp(TimeUtilities.current_time_in_sec())
    if not user_id:
        card_url = url + '/collabcard/' + str(card.id)

    else:
        user_instance = User.objects.get(id=user_id)
        card_temp = generate_private_link_for_chatroom(card, user_instance)
        card_url = card_temp['private_link']
        share['link_created_at'] = card_temp['private_link_created_at']

    share['share_url'] = card_url
    share['creator_share_url'] = card_url

    if card.type == card_types.CARD_PUBLIC_EVENT:

        share['share_url'] = """Check out this interesting event on LikeMinds: %s""" % (card_url)
        share[
            'creator_share_url'] = """Hosting this open event for %s on LikeMinds. RSVP on this link to join us: %s""" % (
            card.community.name, card_url)

    elif card.type == card_types.CARD_EVENT:

        share['share_url'] = """Join us for this event: %s""" % (card_url)
        share['creator_share_url'] = """Hosting this event for %s. RSVP on this link to join us: %s""" % (
            card.community.name, card_url)

    elif card.type == card_types.CARD_POLL:

        share['share_url'] = """Express your views on this poll. %s""" % (card_url)
        share['creator_share_url'] = """Conducting this poll for %s. Please express your views: %s""" % (
            card.community.name, card_url)

    elif card.type == card_types.CARD_NORMAL:

        share[
            'share_url'] = """We are having this conversation on LikeMinds. I have enabled guest access for you for the next 24 hours. Join now with my link %s""" % (
            card_url)
        share[
            'creator_share_url'] = """Join my chat room on LikeMinds using this exclusive link. I have enabled guest access for you for the next 24 hours. %s""" % (
            card_url)

    elif card.type == card_types.CARD_INTRO:

        share[
            'share_url'] = """%s joined %s on LikeMinds. Know more about him or join him for a chat on this link: %s""" % (
            card.user.userinfo.name, card.community.name, card_url)
        share[
            'creator_share_url'] = """I have joined %s on LikeMinds. Know more about me or join me for a chat on this link: %s""" % (
            card.community.name, card_url)

    return share


def get_category_of_chatroom(typ):
    chatroom_type = "Normal Chatroom"

    if typ == card_types.CARD_INTRO:
        chatroom_type = "Introduction Chatroom"
    elif typ == card_types.CARD_EVENT or typ == card_types.CARD_PUBLIC_EVENT:
        chatroom_type = "Event Chatroom"
    elif typ == card_types.CARD_POLL:
        chatroom_type = "POLL Chatroom"
    elif chatroom_type == card_types.CARD_PURPOSE:
        chatroom_type = "Onboarding Chatroom"

    return chatroom_type


def get_chatroom_name(user_name, card):
    '''function to create chatroom name'''

    # if len(user_name) > 1:
    #     user_name = user_name.split(" ")
    #     user_name = user_name[0]
    type = card.type
    if type == card_types.CARD_PUBLIC_EVENT or type == card_types.CARD_EVENT:
        chatroom_name = """%s's Event""" % (user_name)
    elif type == card_types.CARD_POLL:
        chatroom_name = """%s's Poll""" % (user_name)
    elif type == card_types.CARD_PURPOSE:
        chatroom_name = """Announcement Room"""
    elif type == card_types.CARD_INTRO:
        chatroom_name = """%s's Intro""" % (user_name)
    else:
        chatroom_name = """%s's Chat Room""" % (user_name)

    return chatroom_name


def get_chatroom_instance(card_instance, member_id, current_user_id=None, state_instance=None, send_profile=True,
                          preview=False):
    if not current_user_id:
        current_user_id = member_id

    collabcard_serializer = CollabcardSerializer(card_instance, member_id, current_user_id=member_id, preview=preview)

    # get chatroom status
    if not preview:
        status = get_status_of_collabcard(member_id, card_instance, state_instance)
        collabcard_serializer['state'] = status['state']
        collabcard_serializer['mute_status'] = status['mute_status']
        collabcard_serializer['follow_status'] = status['follow_status']
        collabcard_serializer['attending_status'] = status['attending_status']
        collabcard_serializer['is_guest'] = status['is_guest']
        collabcard_serializer['active'] = False
        collabcard_serializer['is_tagged'] = status['is_tagged']
        collabcard_serializer['secret_chatroom_left'] = status['secret_chatroom_left']

        expiry_time = status['expiry_time']

        if not expiry_time or expiry_time >= TimeUtilities.current_time_in_sec():
            collabcard_serializer['active'] = True

    collabcard_member = get_members_profile([card_instance.user.id], card_instance.community.id,
                                                send_profile=send_profile)
    collabcard_serializer['member'] = collabcard_member[0]

    is_removed = removedMembers.objects.filter(community=card_instance.community,
                                                   member_id=collabcard_serializer['member']['id'])

    if collabcard_serializer['member']['state'] == 0 and is_removed.exists():
        temp = get_removed_member_custom_text(is_removed[0])
        collabcard_serializer['member']['custom_intro_text'] = temp['custom_intro_text']
        collabcard_serializer['member']['custom_click_text'] = temp['custom_click_text']
        collabcard_serializer['member']['remove_state'] = temp['remove_state']
        collabcard_serializer['member']['image_url'] = temp['removed_user_image_url']

    # get chatroom files
    collabcard_files = get_collabcard_files(collabcard_serializer['id'])
    collabcard_serializer['images'] = collabcard_files[0]
    collabcard_serializer['pdf'] = collabcard_files[1]
    collabcard_serializer['audios'] = collabcard_files[2]
    collabcard_serializer['videos'] = collabcard_files[3]
    collabcard_serializer['attachments'] = collabcard_files[4]

    return collabcard_serializer


def get_removed_member_custom_text(instance):
    '''function to check removed member state and sending the custom text'''
    temp = {}
    # instance = status['remove']
    remove_state = instance.removed_state

    current_date = TimeUtilities.convert_epoch_time_in_date(instance.created_at)

    if remove_state == deleted_members.LEFT:
        temp['custom_intro_text'] = """Left the community on %s""" % current_date
        temp['custom_click_text'] = """The profile you are trying to access does not exist. %s left the community on %s""" % (
            instance.member.userinfo.name, current_date)

    elif remove_state == deleted_members.REMOVED:
        temp['custom_intro_text'] = """Removed from the community on  %s""" % current_date
        temp[
            'custom_click_text'] = """The profile you are trying to access does not exist. %s was removed from the community on %s""" % (
            instance.member.userinfo.name,  current_date)

    temp['remove_state'] = remove_state
    temp['removed_user_image_url'] = REMOVED_USER_URL
    return temp


def get_guest_custom_text(instance):
    '''function to check the guest member of the chatroom and sending the custom text'''

    temp = {}

    created_at = TimeUtilities.convert_epoch_time_in_date(instance.created_at)

    temp['custom_intro_text'] = """Joined as a guest via %s’s invite link on %s""" % (
        instance.source.userinfo.name,  created_at)
    temp['custom_click_text'] = """The profile you are trying to access does not exist. %s joined this chatroom as a guest via %s’s invite link on %s""" % (
        instance.user.userinfo.name, instance.source.userinfo.name,
        created_at)

    return temp


def get_draft_chatroom_instance(draft_instance, member_id):
    '''function to save draft'''

    draft_serializer = draftChatroomSerializer(draft_instance, member_id)

    draft_member = get_members_profile([draft_instance.user.id], draft_instance.community.id)
    if draft_member:
        draft_serializer['member'] = draft_member[0]

    if draft_instance.internal_link:
        try:
            draft_serializer['preview'] = get_preview_for_url(member_id=member_id,
                                                              preview_url=draft_instance.internal_link,
                                                              community_instance=draft_instance.preview_community,
                                                              chatroom_instance=draft_instance.preview_chatroom,
                                                              send_preview_text=True)
        except Exception as e:
            error_logger.error(e.args)

    draft_files = get_collabcard_files(draft_instance.id, draft=True)

    draft_serializer['images'] = draft_files[0]
    draft_serializer['pdf'] = draft_files[1]
    draft_serializer['audios'] = draft_files[2]
    draft_serializer['videos'] = draft_files[3]
    draft_serializer['attachments'] = draft_files[4]
    return draft_serializer


def get_status_of_collabcard(member_id, card, state_instance=None):
    '''function to get the state of collabcard'''

    collabcard_status = {
        'state': 0,
        'mute_status': False,
        'follow_status': False,
        'is_guest': False,
        'remove': False,
        'state_instance': None,
        'expiry_time': None,
        'is_tagged': False,
        'attending_status': False,
        'secret_chatroom_left': False
    }

    if not member_id:
        return collabcard_status

    # member_id = User.objects.get(id=member_id)
    if not state_instance:
        collabcard_state = collabcardState.objects.filter(card=card, user=member_id)
        if collabcard_state.exists():
            collabcard_status['state'] = collabcard_state[0].state
            collabcard_status['mute_status'] = collabcard_state[0].mute_status
            collabcard_status['follow_status'] = collabcard_state[0].follow_status
            collabcard_status['is_guest'] = collabcard_state[0].is_guest
            collabcard_status['remove'] = collabcard_state[0].remove
            collabcard_status['state_instance'] = collabcard_state[0]
            collabcard_status['expiry_time'] = collabcard_state[0].expiry_time
            collabcard_status['is_tagged'] = collabcard_state[0].is_tagged
            collabcard_status['attending_status'] = collabcard_state[0].attending_status
            collabcard_status['secret_chatroom_left'] = collabcard_state[0].secret_chatroom_left
    else:
        collabcard_status['state'] = state_instance.state
        collabcard_status['mute_status'] = state_instance.mute_status
        collabcard_status['follow_status'] = state_instance.follow_status
        collabcard_status['is_guest'] = state_instance.is_guest
        collabcard_status['remove'] = state_instance.remove
        collabcard_status['state_instance'] = state_instance
        collabcard_status['expiry_time'] = state_instance.expiry_time
        collabcard_status['is_tagged'] = state_instance.is_tagged
        collabcard_status['attending_status'] = state_instance.attending_status
        collabcard_status['secret_chatroom_left'] = state_instance.secret_chatroom_left

    return collabcard_status


def get_member_images_of_chatroom(conversation_filter):
    """ function to give member images of chatrooms """
    unique_members = set()
    member_images = []

    last_conversations_member = []
    count = 0


    for conversation in conversation_filter:
        community_instance = conversation.card.community
        if conversation.user.id not in unique_members:

            member_filter = Members.objects.filter(member_id=conversation.user, community_id=community_instance)
            image_link = conversation.user.userinfo.image_link
            image_url = image_link if image_link else ""

            if member_filter.exists():
                member_instance = member_filter[0]
                if member_instance.image_url:
                    image_url = member_instance.image_url

            remove = False
            if conversation.remove:
                remove = True
            member_images.append(image_url)

            member_data = get_user_profile(conversation.user, community_instance, send_profile=False, remove=remove)
            last_conversations_member.append(member_data)
            unique_members.add(conversation.user.id)
            count = count + 1

        if count > 5:
            break

    temp = {
        'members_images': member_images,
        'last_response_members': last_conversations_member
    }

    return temp

def get_member_instances_for_footer_images_in_chatroom(card_instance):


    conversation_filter = card_answers.objects\
                              .filter(card=card_instance,state=chatroom_states.ANSWER)\
                              .filter(Q(attachment_count=0) |
                                      Q(attachments_uploaded=True))\
                              .distinct('user')\
                              .order_by('user', '-id')[:5]
    member_images = []
    conversation_members = []
    count = 0
    for conversation in conversation_filter:

        community_instance = conversation.community
        member_filter = Members.objects.filter(member_id=conversation.user, community_id=community_instance)
        image_link = conversation.user.userinfo.image_link
        image_url = image_link if image_link else ""

        if member_filter.exists():
            member_instance = member_filter[0]
            if member_instance.image_url:
                image_url = member_instance.image_url

        remove = False
        if conversation.remove:
            remove = True
        member_images.append(image_url)

        member_data = get_user_profile(conversation.user, community_instance, send_profile=False, remove=remove)
        member_data['community_id'] = community_instance.id
        member_data['chatroom_id'] = card_instance.id
        member_data['image_url'] = image_url
        conversation_members.append(member_data)

        count += 1

        if count > 5:
            break

    temp = {
        'members_images': member_images,
        'last_response_members': conversation_members
    }

    return temp


def CollabcardPollsSerializer(poll, user, card):
    """ Poll serializer """
    # print("user--",user)
    card_instance = card
    polls = {
        'id': poll.id,
        'text': poll.text,
        'is_selected': is_poll_selected(poll, user, card) if user else False
    }

    is_multi_select = False
    if card.multiple_select_no is not None or card.multiple_select_state is not None:
        is_multi_select = True

    if card.poll_type == poll_types.POLL_TYPE_INSTANT:
        poll_detail = poll_percentage(card, poll, is_multi_select=is_multi_select)
        polls['poll_count'] = poll_detail[0]
        polls['no_votes'] = poll_detail[0]
        polls['percentage'] = int(poll_detail[1])

    elif card.poll_type == poll_types.POLL_TYPE_DEFERRED and card.end_date // 1000 <= TimeUtilities.current_time_in_sec():

        poll_detail = poll_percentage(card, poll, is_multi_select=is_multi_select)
        polls['poll_count'] = poll_detail[0]
        polls['no_votes'] = poll_detail[0]
        polls['percentage'] = int(poll_detail[1])

    if poll.sub_text:
        polls['sub_text'] = poll.sub_text

    if poll.image_url:
        polls['image_url'] = poll.image_url

    if poll.user:
        # member_profile = get_members_profile([poll.user.id], card_instance.community.id, send_profile=False)
        # polls['member'] = member_profile[0]
        polls['member'] = get_user_profile(user_id=poll.user.id, community_id=card_instance.community.id,
                                           send_profile=False)

    return polls


def is_poll_selected(poll, user, card):
    """ function to know if user selected a poll or not """
    MemberPoll = MemberPollVotes.objects.filter(card=card, user=user, poll=poll)
    return MemberPoll.exists()


def poll_percentage(card, poll, is_multi_select=False):
    """ function to calculate the percentage of particular poll for a card """
    total_polls = MemberPollVotes.objects.filter(card=card)
    if is_multi_select:
        total_polls = total_polls.distinct("user")
    selected_polls = total_polls.filter(poll=poll).count()
    total_polls = total_polls.count()

    if total_polls == 0:
        return 0, 0
    return selected_polls, selected_polls / total_polls * 100


def get_answer_text_for_poll(card, current_user_id=None):
    total_users = MemberPollVotes.objects.filter(card=card).distinct("user")
    first_user = None
    current_user = None
    should_add_you = False
    user_names = []

    for user in total_users:
        if not first_user:
            first_user = user

        if current_user_id and int(user.user.id) == int(current_user_id):
            if not current_user:
                current_user = user
            should_add_you = True
        user_names.append(user.user.userinfo.name)

    if should_add_you:
        if len(user_names) > 1:
            if len(user_names) == 2:
                return f"You and 1 other voted"
            return f"You and {len(user_names) - 1} others voted"
        # elif len(user_names) == 2:
        #     if current_user.user.userinfo.name == first_user.user.userinfo.name:
        #         name = user_names[1]
        #     else:
        #         name = user_names[0]
        #     return f"You and {name} voted"
        elif len(user_names) == 1:
            return f"You voted on this poll"
    elif len(user_names) > 0:
        if len(user_names) == 1:
            return "1 member voted"
        return f"{len(user_names)} members voted"
    return "Be the first one to vote"


def draftPollsSerializers(poll):
    polls = {
        'draft_poll_id': poll.id,
        'text': poll.text,
        'is_selected': False
    }

    if poll.sub_text:
        polls['sub_text'] = poll.sub_text

    if poll.image_url:
        polls['image_url'] = poll.image_url

    polls['poll_count'] = 0
    polls['percentage'] = 0
    polls['no_votes'] = 0

    return polls


def FormResponseSerilaizer(community_id, user_id, current_user_id=None, bl=False):
    responses = communityAnswers.objects.filter(community=community_id, member=user_id).order_by('id')
    if not responses.exists():
        return None

    member = Members.objects.filter(community_id=community_id, member_id=current_user_id)
    member_state = member[0].state if member.exists() else 0
    user_response = []
    new_response = []
    for response in responses:
        # getting the answers of the users who requested to join
        # for the questions that have been asked while requestiong to join in a community
        response_object = {}
        response_object['key'] = response.question_title
        response_object['value'] = response.question_answer

        send_back = False
        if str(response.member.id) == str(current_user_id):
            send_back = True

        temp = {}
        questions = get_question_data(response.question, member_state, send_back=send_back,
                                      user_id=current_user_id, community_id=community_id)
        if questions:
            temp['community_id'] = community_id.id if isinstance(community_id, Community) else community_id
            temp['member_id'] = user_id
            temp['question_title'] = response.question_title
            temp['value'] = response.question_answer
            # if '$#' in temp['value']:
            #     temp['value'] = temp['value'].replace('$#', ', ')
            temp['question_id'] = response.question_id
            temp['state'] = questions['state']
            temp['is_hidden'] = questions['is_hidden']

            temp['directory_fields'] = questions['field']

            if response.question_title in ICONS:
                temp['image_url'] = ICONS[response.question_title]
            elif questions['field']:
                temp['image_url'] = ICONS['Generic']

            new_response.append(temp)

        user_response.append(response_object)

    if not bl:
        return user_response
    return (user_response, new_response)


def get_question_data(question_id, member_state, send_back, user_id=None, community_id=None):
    ''' function to get question id '''

    question_instance = question_id
    if send_back:
        questions = CommunityQuestionsSerializer(question_instance)

    elif member_state == 1 or member_state == 2:
        if user_id and community_id:
            has_right = check_admin_view_contact_right(user_id, community_id)
            if not has_right:
                questions = get_question_instance(question_instance)
                return questions

        questions = CommunityQuestionsSerializer(question_instance)
    else:
        questions = get_question_instance(question_instance)

    return questions


def get_question_instance(question_instance):
    if question_instance.value and question_instance.value != '':
        value_list = ast.literal_eval(question_instance.value)
        privacy = "Public"
        for value in value_list:
            if 'answer_privacy' in value:
                privacy = value['answer_privacy']

        if privacy == "Public":
            questions = CommunityQuestionsSerializer(question_instance)
        else:
            return False
    else:
        questions = CommunityQuestionsSerializer(question_instance)

    return questions


def CommunityQuestionsSerializer(community_question_instance):
    context = {
        'id': community_question_instance.id,
        'question_title': community_question_instance.question_title,
        'value': community_question_instance.value,
        'optional': community_question_instance.optional,
        'community_id': community_question_instance.community_id,
        'state': community_question_instance.question_state,
        'help_text': community_question_instance.help_text if community_question_instance.help_text else '',
        'is_hidden': community_question_instance.is_hidden,
        'field': community_question_instance.field
    }

    if context['value'] and \
            (context['state'] == question_states.CHOICE_SINGLE or
             context['state'] == question_states.CHOICE_MULTIPLE) and \
            context['field']:
        dropdown_list = json.loads(context['value'])

        dropdown_list = sorted(dropdown_list, key=lambda i: i['value'])

        context['value'] = json.dumps(dropdown_list)

    return context


def communityTypeSerializer(communityTypeInstance):
    context = {

        'id': communityTypeInstance.id,
        'type': communityTypeInstance.typ,
        'next_input_title': communityTypeInstance.next_input_title
    }

    if communityTypeInstance.sub_type_placeholder:
        context['sub_type_placeholder'] = communityTypeInstance.sub_type_placeholder

    return context


def communitySubtypeSerializer(communitySubtypeInstance):
    context = {
        'id': communitySubtypeInstance.id,
        'sub_type': communitySubtypeInstance.sub_typ
    }

    return context


def masterQuestionSerializer(masterQuestionInstance):
    json_dict = {
        'type_id': masterQuestionInstance.typ_id,
        'sub_type_id': masterQuestionInstance.sub_type_id,
        'state': masterQuestionInstance.state,
        'question_title': masterQuestionInstance.question_title
    }

    if masterQuestionInstance.value:
        json_dict['value'] = masterQuestionInstance.value
    if masterQuestionInstance.help_text:
        json_dict['help_text'] = masterQuestionInstance.help_text

    return json_dict


def removedMembersSerializer(community_id, member_id):
    removed_filter = removedMembers.objects.filter(community_id=community_id, member_id=member_id)

    if removed_filter.exists():
        removed_state = removed_filter[0].removed_state
        return removed_state

    return False


def createCommunityActionSerializer(instance):
    temp = {
        'step_no': instance.step_no,
        'step_title': instance.step_title,
        'max_point': instance.max_point,
        'current_point': instance.current_point
    }

    if instance.step_subtitle:
        temp['step_sub_title'] = instance.step_subtitle

    return temp


def chatroomActionsSerializer(instance):
    temp = {
        'id': instance.id,
        'title': instance.title
    }

    if instance.route:
        temp['route'] = instance.route

    return temp


def communityLevelsSerializer(instance):
    temp = {}
    temp['level_no'] = instance.level
    temp['title'] = instance.title
    temp['sub_title'] = instance.sub_title
    temp['state'] = instance.state
    temp['image'] = instance.image

    temp['level_click_state'] = instance.level_click_state

    if instance.joined_members != None:
        temp['joined_members'] = instance.joined_members

    if instance.max_members != None:
        temp['max_members'] = instance.max_members

    if instance.action:
        temp['action'] = instance.action

    return temp


def communityFieldTypeSerializer(instance):
    return {
        'id': instance.id,
        'type': instance.type,
        'sub_type_header': instance.sub_type_header,
        'sub_type_placeholder': instance.sub_type_placeholder
    }


def communityFieldSubTypesSerializer(instance):
    return {
        'id': instance.id,
        'sub_type': instance.sub_type
    }


def communityFieldSerializer(instance):
    return {
        'id': instance.id,
        'question_title': instance.question_title,
        'value': instance.value,
        'optional': instance.optional,
        'state': instance.state,
        'help_text': instance.help_text if instance.help_text else '',
        'type': instance.type.id,
        'sub_type': instance.sub_type.id,
        'field': instance.field,
        'is_compulsory': instance.is_compulsory
    }


def userEmailsSerializer(email_instance):
    return {
        'id': email_instance.id,
        'user_id': email_instance.user.id,
        'email': email_instance.email,
        'state': email_instance.email_state,
        'verified': email_instance.verified

    }


def userMobilesSerializer(mobile_instance):
    return {

        'id': mobile_instance.id,
        'user_id': mobile_instance.user.id,
        'mobile_no': mobile_instance.mobile_no,
        'country_code': mobile_instance.country_code,
        'state': mobile_instance.state
    }


# member comunity profiles
def MembersSerializer(member_instance, community_id, current_user_id=None, send_profile=True,
                      is_promoter=False, is_owner=False, all_members_api=False, profile_detail_api=False,
                      user_admin_rights=None):
    user_is_owner = member_instance.is_owner
    parents_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list else []

    member_id = member_instance.member_id.id
    community_profile = get_user_profile(member_instance.member_id, community_id, current_user_id=current_user_id,
                                         send_profile=send_profile)
    community_profile['state'] = member_instance.state
    community_profile['is_owner'] = member_instance.is_owner
    if member_instance.custom_title and not member_instance.custom_title == 'Member':
        community_profile['custom_title'] = member_instance.custom_title
    # sending image  url of members
    if member_instance.image_url:
        community_profile['image_url'] = member_instance.image_url

    if member_instance.state == member_states.ADMIN or member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE:
        community_profile['route'] = """route://member_community_profile?community_id=%s&member_id=%s""" % (
            str(community_id), str(member_id))

        community_profile['member_since'] = "Member of %s since %s" % (
            member_instance.community_id.name,
            TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(member_instance.created_at))

    elif member_instance.state == member_states.PENDING_MEMBER:
        community_profile['member_since'] = "Verification pending for " + member_instance.community_id.name

    if member_instance.state == member_states.ADMIN:

        answer_filter = communityAnswers.objects.filter(community=community_id).filter(
            member=member_instance.member_id).order_by('id')
        if not answer_filter.exists():
            community_profile['custom_intro_text'] = """Created this community on %s""" % \
                                                     TimeUtilities.convert_epoch_time_in_date(member_instance.created_at)


    if member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE:

        answer_filter = communityAnswers.objects.filter(community=community_id).filter(
            member=member_instance.member_id).order_by('id')

        if not answer_filter.exists():
            community_profile['custom_intro_text'] = """Joined via a private community link on %s""" % (
                TimeUtilities.convert_epoch_time_in_date(member_instance.created_at))
            community_profile[
                'custom_click_text'] = """%s joined this community via a private community link on %s and hasn’t created their profile for this community yet""" % (
                member_instance.member_id.userinfo.name,
                TimeUtilities.convert_epoch_time_in_date(member_instance.created_at))

    # add menu for all members api and fetch community profile API

    if (all_members_api or profile_detail_api) and (is_promoter or is_owner):
        community_profile["menu"] = get_menu_for_members(current_user_id=current_user_id, item_member_id=member_id,
                                                         community_id=community_id,
                                                         current_user_is_promoter=is_promoter,
                                                         current_user_is_owner=is_owner,
                                                         item_member_state=member_instance.state,
                                                         item_member_is_owner=user_is_owner,
                                                         current_user_admin_rights=user_admin_rights,
                                                         parents_list=parents_list,
                                                         profile_detail_api=profile_detail_api)

    elif profile_detail_api and current_user_id and int(current_user_id) != int(member_id):
        report_member = {"title": "Report member",
                         "route": f"route://report_member?community_id={community_id}&member_id={member_id}"}
        block_member = {"title": "Block member",
                        "route": f"route://block_member?community_id={community_id}&member_id={member_id}"}
        community_profile["menu"] = [report_member, block_member]
        if user_is_owner:
            community_profile["menu"] = [report_member]

    return community_profile


def get_menu_for_members(current_user_id, item_member_id, community_id, current_user_is_promoter, item_member_state,
                         current_user_is_owner=False, item_member_is_owner=False, current_user_admin_rights=None,
                         parents_list=None, profile_detail_api=False):
    """ function to get the menu for all members for all members api and profile detail api """
    #  x is current member , y is member whose profile is currently in iteration sequence
    # current_user_state, item_member_state,

    edit_title = {"title": "Edit title",
                  "route": f"route://edit_custom_title?community_id={community_id}&member_id={item_member_id}"}
    edit_permissions = {"title": "Edit permissions",
                        "route": f"route://edit_member_rights?community_id={community_id}&member_id={item_member_id}"}
    give_CM_rights = {"title": "Give community management rights",
                      "route": f"route://give_manager_rights?community_id={community_id}&member_id={item_member_id}"}
    edit_CM_rights = {"title": "Edit management rights",
                      "route": f"route://edit_manager_rights?community_id={community_id}&member_id={item_member_id}"}
    report_member = {"title": "Report member",
                     "route": f"route://report_member?community_id={community_id}&member_id={item_member_id}"}
    remove_from_community = {"title": "Remove from community",
                             "route": f"route://remove_from_community?community_id={community_id}&member_id={item_member_id}"}
    block_member = {"title": "Block member",
                    "route": f"route://block_member?community_id={community_id}&member_id={item_member_id}"}

    if parents_list is None:
        parents_list = []

    if current_user_is_owner and int(current_user_id) == int(item_member_id):
        return [edit_title]
    if current_user_id and int(current_user_id) == int(item_member_id):
        return []
    elif not current_user_id:
        return []

    menu = []

    if current_user_is_owner and item_member_is_owner:
        menu = [edit_title]
    elif current_user_is_owner and item_member_state == member_states.ADMIN:
        menu = [remove_from_community, edit_CM_rights]

    elif current_user_is_owner and (item_member_state == member_states.MEMBER or
                                    item_member_state == member_states.PROFILE_UNAVAILABLE):
        menu = [remove_from_community, edit_permissions, give_CM_rights]

    elif current_user_is_promoter and item_member_state == member_states.ADMIN:

        is_child = current_user_id in parents_list

        if current_user_admin_rights:
            if current_user_admin_rights["approve"] and is_child:
                menu.append(remove_from_community)

            if current_user_admin_rights["add_manager"] and is_child:
                menu.append(edit_CM_rights)

        if profile_detail_api:
            menu.append(report_member)
            # if not item_member_is_owner:
            menu.append(block_member)

    elif current_user_is_promoter and (item_member_state == member_states.MEMBER or
                                       item_member_state == member_states.PROFILE_UNAVAILABLE):
        if current_user_admin_rights:
            if current_user_admin_rights["approve"]:
                menu.append(remove_from_community)

            if current_user_admin_rights["delete_room"] or current_user_admin_rights["approve"]:
                menu.append(edit_permissions)

            if current_user_admin_rights["add_manager"]:
                menu.append(give_CM_rights)

            if not current_user_admin_rights["approve"] and profile_detail_api:
                menu.append(report_member)

            if profile_detail_api:
                menu.append(block_member)

    else:
        if profile_detail_api:
            menu.append(report_member)
            # if not item_member_is_owner:
            menu.append(block_member)

    return menu


def get_user_profile(user_id, community_id=None, current_user_id=None, send_profile=True, remove=False):
    if isinstance(user_id, User):
        user_instance = user_id

        if not user_instance:
            return {}
    else:
        try:
            user_instance = User.objects.get(id=user_id)
        except:
            return {}

    userinfo_serialized_object = UserinfoSerializer(user_instance.userinfo)

    # if member is not a part of community
    if remove:
        userinfo_serialized_object['image_url'] = REMOVED_USER_URL
    # userinfo_serialized_object['state'] = 0

    if not send_profile:
        return userinfo_serialized_object
    form_response = FormResponseSerilaizer(community_id, user_instance.id, bl=True,
                                           current_user_id=current_user_id)

    if form_response:
        # userinfo_serialized_object['response'] = form_response[0]
        userinfo_serialized_object['question_answers'] = form_response[1]

    return userinfo_serialized_object


def get_members_profile(member_ids, community_id, current_user_id=None, send_profile=True, remove=False,
                        is_promoter=False, is_owner=False, all_members_api=False, profile_detail_api=False,
                        user_admin_rights=None):
    '''function to get member profile from list of members ids'''
    member_profile_list = []

    for id in member_ids:

        member_filter = Members.objects.filter(member_id=id, community_id=community_id)

        if member_filter.exists():

            if user_admin_rights and not user_admin_rights["approve"] and not profile_detail_api:
                if member_filter[0].state == member_states.PENDING_MEMBER:
                    continue

            community_profile = MembersSerializer(member_filter[0], community_id, current_user_id=current_user_id,
                                                  send_profile=send_profile, all_members_api=all_members_api,
                                                  profile_detail_api=profile_detail_api,
                                                  user_admin_rights=user_admin_rights,
                                                  is_owner=is_owner, is_promoter=is_promoter
                                                  )

            if isinstance(community_id, Community):
                community_profile['community_id'] = community_id.id
            else:
                community_profile['community_id'] = community_id

            member_profile_list.append(community_profile)

        else:
            temp = get_user_profile(id, community_id, current_user_id=current_user_id,
                                    send_profile=send_profile, remove=remove)
            temp['state'] = 0
            temp['community_id'] = community_id
            member_profile_list.append(temp)

    return member_profile_list


def report_serializer(report_instance, current_user_id):
    report = {"id": report_instance.id}

    community_instance = report_instance.community
    community_id = community_instance.id
    # serialized_community = CommunitySerializer(community_instance)
    report["community_id"] = community_instance.id
    report["community_name"] = community_instance.name

    if report_instance.conversation is not None:
        report["conversation"] = conversationSerializer(report_instance.conversation, current_user_id=current_user_id)
        report["chatroom"] = get_chatroom_instance(report_instance.conversation.card, current_user_id)
        report["conversation_users"] = get_last_two_conversation_user_images(report_instance.conversation.card)

    elif report_instance.collabcard is not None:
        report["chatroom"] = get_chatroom_instance(report_instance.collabcard, current_user_id)
        report["conversation_users"] = get_last_two_conversation_user_images(report_instance.collabcard)

    if report_instance.tag:
        report["tag"] = report_tag_serializer(report_instance.tag)

    if report_instance.reason:
        report["reason"] = report_instance.reason

    if report_instance.user_reported:
        user_profile = get_members_profile(member_ids=[report_instance.user_reported.id], community_id=community_id)
        report["user_reported"] = user_profile[0]

    if report_instance.reported_by:
        user_profile = get_members_profile(member_ids=[report_instance.reported_by.id], community_id=community_id)
        report["reported_by"] = user_profile[0]

    if report_instance.type is not None:
        report["type"] = report_instance.type

    if report_instance.action_taken_tag:
        report["action_taken_tag"] = report_tag_serializer(report_instance.action_taken_tag)

    if report_instance.action_taken_reason:
        report["action_taken_reason"] = report_instance.action_taken_reason

    if report_instance.action_taken_by:
        user_profile = get_members_profile(member_ids=[report_instance.action_taken_by.id], community_id=community_id)
        report["action_taken_by"] = user_profile[0]

    if report_instance.action_taken is not None:
        report["action_taken"] = report_instance.action_taken

    if report_instance.rights_added is not None:
        report["rights_added"] = json.loads(report_instance.rights_added)

    if report_instance.rights_removed is not None:
        report["rights_removed"] = json.loads(report_instance.rights_removed)

    # if report_instance.is_closed:
    report["is_closed"] = report_instance.is_closed if report_instance.is_closed is not None else False

    if report_instance.closed_by is not None:
        user_profile = get_members_profile(member_ids=[report_instance.closed_by.id], community_id=community_id)
        report["closed_by"] = user_profile[0]

    if report_instance.closed_time:
        report["closed_on"] = report_instance.closed_time

    report["reported_on"] = report_instance.date_epoch

    return report


def get_last_two_conversation_user_images(chatroom):
    last_conversations = card_answers.objects.filter(card=chatroom).select_related("user").order_by("-id")

    conversation_users = []
    user_list = []
    loop_count = 0
    for conversation in last_conversations:
        user_instance = conversation.user
        if loop_count >= 2:
            break
        elif user_instance.id in user_list:
            continue
        else:
            user_list.append(user_instance.id)

        user_dict = {"id": user_instance.id, "name": user_instance.userinfo.name,
                     "image_url": user_instance.userinfo.image_link}

        conversation_users.append(user_dict)
        loop_count += 1
    return conversation_users


def report_tag_serializer(tag_instance):
    tag_dict = {'id': tag_instance.tag_id,
                "name": tag_instance.tag_name}

    return tag_dict


# ------------------------------- chatroom conversation data ------------------------------------

def is_draft_conversation(conversation, current_user_id):

    if (conversation.attachment_count > 0 and
        conversation.attachments_uploaded is False) and\
            ((current_user_id and
              NumberUtilities.get_integer_from_string(current_user_id) != conversation.user.id) or
             conversation.api_version <= 0):
        return True

    return False



def conversationSerializer(conversation, current_user_id=None, fetch_reply=True):
    temp = {
        "id": conversation.id,
        "answer": conversation.answer,
        "state": conversation.state,
        'is_edited': conversation.is_edited,
        'created_at': conversation.created_at,
        'has_files': conversation.has_files,
        'attachment_count': conversation.attachment_count,
        'attachments_uploaded': conversation.attachments_uploaded,
        'chatroom_id': conversation.card.id,
        'community_id': conversation.community.id,
        'created_epoch': int(conversation.created_at)
    }

    if conversation.attachments_uploaded is None:
        temp['attachments_uploaded'] = False

    if conversation.has_files or\
            conversation.attachment_count > 0:
        answer_files = get_answer_files(temp['id'])
        temp['images'] = answer_files['image']
        temp['videos'] = answer_files['videos']
        temp['audios'] = answer_files['audios']
        temp['pdf'] = answer_files['pdf']
        temp['attachments'] = answer_files['attachments']
        if 'location' in answer_files:
            temp['location'] = answer_files['location']

    if conversation.og_tags:
        temp['og_tags'] = json.loads(conversation.og_tags)

    if conversation.is_deleted:
        temp['deleted_by'] = conversation.deleted_by_user.id

    # if member is removed from community
    remove = False
    if conversation.remove:
        remove = True

    member_profile = get_members_profile([conversation.user.id], conversation.community.id,
                                         current_user_id=current_user_id, send_profile=False, remove=remove)
    temp['member'] = member_profile[0]

    temp['date'] = TimeUtilities.convert_epoch_time_in_date(conversation.created_at)

    if conversation.is_guest:
        temp['member']['is_guest'] = conversation.is_guest
        state_filter = collabcardState.objects.filter(card=conversation.card,
                                                      user=conversation.user, is_guest=True)
        if state_filter.exists() and state_filter[0].source:
            instance = state_filter[0]
            guest_text = get_guest_custom_text(instance)
            temp['member']['custom_intro_text'] = guest_text['custom_intro_text']
            temp['member']['custom_click_text'] = guest_text['custom_click_text']

        # if the member is removed from the community
    elif conversation.remove:
        instance = conversation.remove
        removed_member_text = get_removed_member_custom_text(instance)
        temp['member']['custom_intro_text'] = removed_member_text['custom_intro_text']
        temp['member']['custom_click_text'] = removed_member_text['custom_click_text']
        temp['member']['remove_state'] = removed_member_text['remove_state']
        temp['member']['image_url'] = removed_member_text['removed_user_image_url']

    if conversation.reply:
        reply_conversation = conversation.reply
        temp['reply_conversation'] = reply_conversation.id

        if fetch_reply and not is_draft_conversation(reply_conversation, current_user_id):
            temp['reply_conversation_object'] = conversationSerializer(reply_conversation,
                                                                       fetch_reply=False,
                                                                       current_user_id=current_user_id)

    if conversation.temporary_id:
        temp['temporary_id'] = conversation.temporary_id

    return temp


def get_answer_files(answer_id):
    '''function to return pdf and image files of a collabcard'''

    attachments = answerAttachment.objects.filter(answer=answer_id).order_by("index")
    img_list = []
    pdf = []
    videos = []
    audios = []

    attachments_list = []

    files = {}
    for file in attachments:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url, 'index': file.index, 'type': file.type}
                img_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                if file.dimensions:
                    img['dimensions'] = json.loads(file.dimensions)
                    img_attachment['dimensions'] = json.loads(file.dimensions)
                if file.height:
                    img['height'] = file.height
                    img_attachment['height'] = file.height

                if file.width:
                    img['width'] = file.width
                    img_attachment['width'] = file.width

                if file.thumbnail_url:
                    img['thumbnail_url'] = file.thumbnail_url
                    img_attachment['thumbnail_url'] = file.thumbnail_url

                img_list.append(img)
                attachments_list.append(img_attachment)

        elif file.type == 'video':
            if file.file_url:
                video_url = {'video_url': file.file_url, 'index': file.index, 'type': file.type}
                video_attachment = {'url': file.file_url, 'index': file.index, 'type': file.type}

                if file.height:
                    video_url['height'] = file.height
                    video_attachment['height'] = file.height

                if file.width:
                    video_url['width'] = file.width
                    video_attachment['width'] = file.width

                if file.thumbnail_url:
                    video_url['thumbnail_url'] = file.thumbnail_url
                    video_attachment['thumbnail_url'] = file.thumbnail_url

                videos.append(video_url)
                attachments_list.append(video_attachment)

        elif file.type == 'audio':
            if file.file_url:
                audio_url = {'audio_url': file.file_url, 'index': file.index, 'type': file.type}
                audios.append(audio_url)

        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url, 'index': file.index, 'type': file.type}
                pdf.append(pdf_url)

        elif file.type == "location":
            location = {
                'location_name': file.location_name,
                'location_lat': file.location_lat,
                'location_long': file.location_long
            }
            files['location'] = location

    files['image'] = img_list
    files['pdf'] = pdf
    files['videos'] = videos
    files['audios'] = audios
    files['attachments'] = attachments_list
    return files


# =================================== client db synching serializers ======================================


def get_conversation_instance_for_db_synching(conversation, fetch_reply=True, current_user_id=None):
    conversation_dict = {
        "id": conversation.id,
        "answer": conversation.answer,
        "state": conversation.state,
        'is_edited': conversation.is_edited,
        'created_at': TimeUtilities.convert_epoch_time_in_hh_mm(conversation.created_at),
        'has_files': conversation.has_files,
        'attachment_count': conversation.attachment_count,
        'attachments_uploaded': conversation.attachments_uploaded,
        'chatroom_id': conversation.card.id,
        'community_id': conversation.community.id,
        'member_id': conversation.user.id,
        'created_epoch': int(conversation.created_at)
    }

    if conversation.attachments_uploaded is None:
        conversation_dict['attachments_uploaded'] = False

    if conversation.has_files or\
            conversation.attachment_count > 0:

        answer_files = get_answer_files(conversation_dict['id'])
        conversation_dict['images'] = answer_files['image']
        conversation_dict['pdf'] = answer_files['pdf']
        conversation_dict['videos'] = answer_files['videos']
        conversation_dict['audios'] = answer_files['audios']
        conversation_dict['attachments'] = answer_files['attachments']

        if 'location' in answer_files:
            conversation_dict['location'] = answer_files['location']

    if conversation.og_tags:
        conversation_dict['og_tags'] = json.loads(conversation.og_tags)

    if conversation.is_deleted:
        conversation_dict['deleted_by'] = conversation.deleted_by_user.id

    conversation_dict['date'] = TimeUtilities.convert_epoch_time_in_date(conversation.created_at)

    if conversation.internal_link:
        try:
            conversation_dict['preview'] = get_preview_for_url(current_user_id, conversation.internal_link,
                                                               community_instance=conversation.preview_community,
                                                               chatroom_instance=conversation.preview_chatroom)
        except Exception as e:
            error_logger.error(e.args)

    if conversation.reply:
        conversation_dict['reply_conversation'] = conversation.reply.id

    return conversation_dict


def get_member_instance_for_db_synching(member_instance, community_id, current_user_id=None, send_profile=True):
    # member_id = member_instance.member_id.id

    community_name = member_instance.community_id.name

    community_profile = get_user_profile(member_instance.member_id, community_id, current_user_id=current_user_id,
                                         send_profile=send_profile)

    community_profile['state'] = member_instance.state
    community_profile['is_owner'] = member_instance.is_owner
    if member_instance.custom_title and not member_instance.custom_title == 'Member':
        community_profile['custom_title'] = member_instance.custom_title

    # sending image  url of members
    if member_instance.image_url:
        community_profile['image_url'] = member_instance.image_url

    if member_instance.state == member_states.ADMIN or member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE:
        # community_profile['route'] = """route://member_community_profile?community_id=%s&member_id=%s""" % (
        #     str(community_id), str(member_id))

        community_profile['member_since'] = "Member of " + community_name + " since " + TimeUtilities.convert_epoch_time_to_date_with_mon_day_year(member_instance.created_at)
    elif member_instance.state == member_states.PENDING_MEMBER:
        community_profile['member_since'] = "Verification pending for " + community_name

    if member_instance.state == member_states.ADMIN:

        answer_filter = communityAnswers.objects.filter(community=community_id).filter(
            member=member_instance.member_id)

        if not answer_filter.exists():
            # if 'question_answers' not in community_profile:
            community_profile['custom_intro_text'] = """Created this community on %s""" % \
                                                     TimeUtilities.convert_epoch_time_in_date(member_instance.created_at)

    if (member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE):

        answer_filter = communityAnswers.objects.filter(community=community_id).filter(
            member=member_instance.member_id)

        if not answer_filter.exists():
            # if 'question_answers' not in community_profile:

            community_profile['custom_intro_text'] = """Joined via a private community link on %s""" % (
                TimeUtilities.convert_epoch_time_in_date(member_instance.created_at))
            community_profile['custom_click_text'] = CUSTOM_CLICK_TEXT % (
                member_instance.member_id.userinfo.name,
                TimeUtilities.convert_epoch_time_to_date_month_year(member_instance.created_at))

    community_profile['community_id'] = community_id

    return community_profile


def get_removed_member_instance(instance):
    community_id = instance.community_id
    user_profile = get_user_profile(instance.member, community_id, send_profile=False, remove=True)
    removed = get_removed_member_custom_text(instance)
    user_profile['custom_intro_text'] = removed['custom_intro_text']
    user_profile['custom_click_text'] = removed['custom_click_text']
    user_profile['remove_state'] = removed['remove_state']
    user_profile['community_id'] = community_id

    return user_profile


def get_guest_member_instance(instance):
    community_id = instance.community.id
    user_profile = get_user_profile(instance.user, community_id, send_profile=False)
    user_profile['community_id'] = community_id
    user_profile['chatroom_id'] = instance.card.id

    if instance.source:
        guest = get_guest_custom_text(instance)
        user_profile['custom_intro_text'] = guest['custom_intro_text']
        user_profile['custom_click_text'] = guest['custom_click_text']

    return user_profile


# ==============================================================================================================


############################ fetch preview functions #####################


def get_preview_for_url(member_id=None, preview_url=None,
                        community_instance=None, chatroom_instance=None, send_preview_text=True):
    """ function to get preview of community or chatroom """

    user_instance = User.get_user_or_none(member_id)

    is_member_directory = False
    preview_type = None
    preview_text = None
    title = None
    route = None
    aj = None
    source_id = None
    shared_by = None
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
        if 'shared_by' in query_items:
            shared_by = query_items['shared_by']

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

    if community_id:
        # checking if community_instance already exists
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

    if preview_type == "chatroom":
        title = get_title_for_chatroom_preview(chatroom_instance, member_id)

    else:
        is_private = True if aj else False
        title = get_title_for_community_preview(community_instance, member_id, preview_type, is_private=is_private)

    if send_preview_text:
        context["title"] = title

    # writing at last to get the action and others based on progress done above
    if chatroom_id:
        if chatroom_instance.type == card_types.CARD_EVENT or chatroom_instance.type == card_types.CARD_PUBLIC_EVENT:
            context["action"] = "VIEW EVENT"
            if send_preview_text:
                context["preview_text"] = "Preview of the event will be added later"
        elif chatroom_instance.type == card_types.CARD_POLL:
            context["action"] = "VIEW POLL"
            if send_preview_text:
                context["preview_text"] = "Preview of the poll will be added later"

        elif chatroom_instance.type == card_types.CARD_INTRO:
            context["action"] = "SAY HI"
        else:
            context["action"] = "VIEW CHAT ROOM"

    if aj:
        route = route + f"&aj={aj}"

    if source_id:
        route = route + f"&source_id={source_id}"

    if shared_by:
        route = route + f"&shared_by={shared_by}"

    context["action_route"] = route

    return context


def get_title_for_chatroom_preview(chatroom, current_user_id):
    if chatroom.type == card_types.CARD_EVENT or chatroom.type == card_types.CARD_PUBLIC_EVENT:

        is_open_event = chatroom.type == card_types.CARD_PUBLIC_EVENT
        additional_text = "open " if is_open_event else ""

        if current_user_id and int(current_user_id) == int(chatroom.user.id):
            return f"I am hosting this {additional_text}event for {chatroom.community.name}. RSVP to join us."
        else:

            event_date = chatroom.end_date

            result = time.localtime(int(event_date) / 1000)

            if int(result.tm_mday) == 1:
                day_text = "1st"
            elif int(result.tm_mday) == 2:
                day_text = "2nd"
            elif int(result.tm_mday) == 3:
                day_text = "3rd"
            else:
                day_text = f"{result.tm_mday}th"

            month_text = months_semi[result.tm_mon]

            event_date_text = f"{day_text} {month_text}"

            current_year = time.strftime("%Y")

            if int(result.tm_year) != int(current_year):
                event_date_text = event_date_text + " " + str(result.tm_year)

            return f"Join us for this {additional_text}event on {event_date_text}"

    elif chatroom.type == card_types.CARD_POLL:
        return 'Please express your views on this poll'

    elif chatroom.type == card_types.CARD_INTRO:

        community_name = chatroom.community.name
        if current_user_id and int(current_user_id) == int(chatroom.user.id):
            return f"I have joined {community_name}. Join me for a chat or view my community profile here."

        return f"{chatroom.user.userinfo.name} joined {community_name}. Know more about them or join them for a chat here."

    else:
        return "Join us in this conversation. Guest access is enabled for the next 24 hours."


def get_title_for_community_preview(community, current_user_id, preview_type, is_private=False):
    if preview_type == "directory":
        return "The directory for our community has been set up. Complete your profile to see detailed profiles of other members in the community."
    else:
        community_name = community.name
        if is_private:
            return f"Join {community_name} with my exclusive invite. For security, this is valid only for the next 24 hours."
        else:
            is_admin = Members.objects.filter(community_id=community,
                                              member_id=current_user_id, state=member_states.ADMIN).exists()
            if is_admin:
                return f"I am building {community_name} community. Apply to join our community."
            else:
                return f"I am a part of {community_name} community. Apply to join our community."


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

    chatroom_instance = get_chatroom_instance(card_instance, member_id, send_profile=False, preview=True)
    conversation_filter = card_answers.objects.filter(card=card_instance.id,
                                                      state=chatroom_states.ANSWER
                                                      ).filter(Q(attachment_count=0) |
                                                               Q(attachments_uploaded=True))
    chatroom_instance['total_response_count'] = conversation_filter.count()

    last_response_members = get_member_instances_for_footer_images_in_chatroom(card_instance)
    chatroom_instance['last_response_members'] = last_response_members['last_response_members']

    return chatroom_instance


def get_member_images_of_chatroom_v1(conversation_filter):
    """ function to give member images of chatrooms """
    conversation_filter = conversation_filter.distinct("user").order_by('user', '-id')[:5]
    last_conversations_member = []
    for conversation in conversation_filter:
        remove = False
        if conversation.remove:
            remove = True
        member_data = get_user_profile(conversation.user, None, send_profile=False, remove=remove)
        last_conversations_member.append(member_data)

    temp = {
        'last_response_members': last_conversations_member
    }

    return temp

# =========================================================================#
