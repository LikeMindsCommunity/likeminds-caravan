import json
import time

from django.conf import settings
from django.db.models import Q
from togther.models import *
from utility.utils import is_IG_community, is_LG_or_LP_community, feedback_community_id, \
    generate_private_link, generate_random, get_time_text, eligibility_count, get_members_count_in_community, \
    is_member_promoter, generate_private_link_for_chatroom, get_date_time_from_timestamp

from utility.states import (card_types, question_states, member_states, poll_types,
                            deleted_members, manager_rights, member_rights)
from .user_moderation_rights import *
url = settings.URL
import ast
from .static_files import *
from datetime import datetime, date


#
# class CommunitySerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Community
#         fields = ('id','name', 'purpose', 'image_url' ,'about', 'location')


def CommunitySerializer(community, promoter_id=0):
    # function to serialize a community object
    new_dict = {
        'id': community.id,
        'name': community.name,
        'purpose': community.purpose,
        'location': community.location if community.location else "",

    }

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

    new_dict['share_url'] = url + '/community/' + str(new_dict['id'])

    new_dict['date'] = community.active_since
    new_dict['members_count'] = get_members_count_in_community(community.id)
    new_dict['state'] = int(community.hide_community)

    # generating private link
    if promoter_id:
        private_link = generate_private_link(community_instance=community,
                                             promoter_instance=promoter_id)
        new_dict['private_link'] = private_link
        if new_dict['members_count'] <= 10:
            new_dict[
                'private_link_text_admin'] = """I have started %s community on LikeMinds and I am inviting you to build this community together with me. Join now with this exclusive link. Auto-verification is enabled for 24 hours: %s""" % (
            community.name, private_link)
        else:
            new_dict[
                'private_link_text_admin'] = """Join %s community on LikeMinds with my exclusive link. Auto-verification is enabled for 24 hours: %s""" % (
            community.name, private_link)

        new_dict['private_link_members_directory'] = private_link + "&source=members_directory"
        new_dict[
            'private_link_text_members_directory'] = """I have created a community directory for %s on LikeMinds. Signup and complete your profile to see detailed profiles of other members in the community using this exclusive link. Auto-verification is enabled for 24 hours: %s""" % (
        community.name, new_dict['private_link_members_directory'])

    if community.type:
        new_dict['type'] = community.type
    if community.sub_type:
        new_dict['sub_type'] = community.sub_type

    new_dict[
        'share_text_admin'] = """I am building %s community on LikeMinds.\n %s \nApply to join our community. %s\n""" % (
        new_dict['name'], new_dict['purpose'], new_dict['share_url'])

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


def CollabcardSerializer(card, user, community=None, current_user_id=None):
    # function to serialize a community object
    collabcard = {
        'id': card.id,
        'title': card.title,
        'community_id': card.community_id,
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count': card.image_count,
        'pdf_count': card.pdf_count,
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        'answers_count': card.answers_count,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count,
        'card_creation_time': time.strftime('%I:%M %p', time.localtime(card.date_epoch)),
        "community_name": card.community.name,
        "date": time.strftime('%d %b %Y', time.localtime(card.date_epoch)),
        "created_at": time.strftime('%H:%M', time.localtime(card.date_epoch))
    }

    if user and int(user) == card.user.id:
        collabcard['has_been_named'] = card.has_been_named

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
        temp = get_members_profile(member_ids=member_ids, community_id=card.community_id, current_user_id=user)
        collabcard['updated_member'] = temp[0]

    if card.updated_time:
        collabcard['updated_time'] = get_time_text(card.updated_time)

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
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count,
        'card_creation_time': time.strftime('%B %d at %H:%M', time.localtime(card.date_epoch))
    }

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

    return chatroom


def get_collabcard_files(card_id, draft=False):
    '''function to return pdf and image files of a collabcard'''

    if not draft:
        files = Card_Attachment.objects.filter(collabcard=card_id)
    else:
        files = draftChatroomFiles.objects.filter(draft=card_id)
    img_list = []
    pdf = []
    for file in files:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url}
            else:
                img = {'image_url': url + file.attachment.url}
            img_list.append(img)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url}
            else:
                pdf_url = {'pdf_file': url + file.attachment.url}
            pdf.append(pdf_url)
    return (img_list, pdf)


def get_share_url_text(card, user_id):
    '''function to share url text'''

    share = {}
    share['link_created_at'] = get_date_time_from_timestamp(time.time())
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


def conversationSerializer(conversation, fetch_reply=True):
    temp = {
        "id": conversation.id,
        "answer": conversation.answer,
        "state": conversation.state,
        'is_deleted': conversation.is_deleted,
        'is_edited': conversation.is_edited,
    }

    answer_files = get_answer_files(temp['id'])

    temp['images'] = answer_files['image']
    temp['pdf'] = answer_files['pdf']

    if 'location' in answer_files:
        temp['location'] = answer_files['location']

    if conversation.og_tags:
        temp['og_tags'] = json.loads(conversation.og_tags)

    if conversation.reply and fetch_reply:
        temp['reply_conversation'] = conversationSerializer(conversation.reply, fetch_reply=False)

    #if member is removed from community
    remove = False
    if conversation.remove:
        remove = True
    temp['member'] =  get_user_profile(conversation.user,conversation.community.id,send_profile=False,remove=remove)
    if conversation.is_deleted:
        temp['deleted_by'] = get_members_profile([conversation.user.id], conversation.community.id)
        temp['deleted_by_member_state'] = conversation.deleted_by_user_state

    return temp




def get_answer_files(answer_id):
    '''function to return pdf and image files of a collabcard'''

    attachments = answerAttachment.objects.filter(answer=answer_id)
    img_list = []
    pdf = []
    files = {}
    for file in attachments:
        if file.type == 'image':
            if file.file_url:
                img = {'image_url': file.file_url}
                img_list.append(img)
        elif file.type == 'pdf':
            if file.file_url:
                pdf_url = {'pdf_file': file.file_url}
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
    return files


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


def get_chatroom_instance(card_instance, member_id, current_user_id=None, state_instance=None):

    if not current_user_id:
        current_user_id = member_id

    collabcard_serializer = CollabcardSerializer(card_instance, member_id, current_user_id=member_id)
    collabcard_member = get_members_profile([card_instance.user.id], card_instance.community.id)

    # get chatroom status
    status = get_status_of_collabcard(member_id, card_instance,state_instance)
    collabcard_serializer['state'] = status['state']
    collabcard_serializer['mute_status'] = status['mute_status']
    collabcard_serializer['follow_status'] = status['follow_status']
    collabcard_serializer['is_guest'] = status['is_guest']
    collabcard_serializer['active'] = False
    collabcard_serializer['is_tagged'] = status['is_tagged']

    expiry_time = status['expiry_time']

    if not expiry_time or expiry_time >= int(time.time()):
        collabcard_serializer['active'] = True


    collabcard_serializer['member'] = collabcard_member[0]

    is_removed = removedMembers.objects.filter(community=card_instance.community,member_id=collabcard_serializer['member']['id'])

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

    # # get time stamp for card
    # time_text = get_time_text(card_instance.date_epoch)
    # collabcard_serializer['created_at'] = time_text

    return collabcard_serializer


def get_removed_member_custom_text(instance):
    '''function to check removed member state and sending the custom text'''
    temp = {}
    # instance = status['remove']
    remove_state = instance.removed_state
    if remove_state == deleted_members.LEFT:
        temp['custom_intro_text'] = """Left the community on %s""" % (
            time.strftime("%d %B %Y", time.localtime(instance.created_at)))
        temp[
            'custom_click_text'] = """The profile you are trying to access does not exist. %s left the community on %s""" % (
            instance.member.userinfo.name, time.strftime("%d %B %Y", time.localtime(instance.created_at)))

    elif remove_state == deleted_members.REMOVED:
        temp['custom_intro_text'] = """Removed from the community on  %s""" % (
            time.strftime("%d %B %Y", time.localtime(instance.created_at)))
        temp[
            'custom_click_text'] = """The profile you are trying to access does not exist. %s was removed from the community on %s""" % (
            instance.member.userinfo.name, time.strftime("%d %B %Y", time.localtime(instance.created_at)))

    temp['remove_state'] = remove_state
    temp['removed_user_image_url'] = REMOVED_USER_URL
    return temp


def get_guest_custom_text(instance):
    '''function to check the guest member of the chatroom and sending the custom text'''

    temp = {}
    temp['custom_intro_text'] = """Joined as a guest via %s’s invite link on %s""" % (
        instance.source.userinfo.name, time.strftime('%d %B %Y', time.localtime(instance.created_at)))
    temp[
        'custom_click_text'] = """The profile you are trying to access does not exist. %s joined this chatroom as a guest via %s’s invite link on %s""" % (
        instance.user.userinfo.name, instance.source.userinfo.name,
        time.strftime('%d %B %Y', time.localtime(instance.created_at)))

    return temp


def get_draft_chatroom_instance(draft_instance, member_id):
    '''function to save draft'''

    draft_serializer = draftChatroomSerializer(draft_instance, member_id)

    draft_member = get_members_profile([draft_instance.user.id], draft_instance.community.id)
    if draft_member:
        draft_serializer['member'] = draft_member[0]

    # status = get_status_of_collabcard(member_id, card_instance)
    # collabcard_serializer['state'] = status['state']
    # collabcard_serializer['mute_status'] = status['mute_status']
    # collabcard_serializer['follow_status'] = status['follow_status']

    draft_files = get_collabcard_files(draft_instance.id, draft=True)

    draft_serializer['images'] = draft_files[0]
    draft_serializer['pdf'] = draft_files[1]
    return draft_serializer


def get_status_of_collabcard(member_id, card,state_instance=None):
    '''function to get the state of collabcard'''

    collabcard_status = {
        'state': 0,
        'mute_status': False,
        'follow_status': False,
        'is_guest': False,
        'remove': False,
        'state_instance': None,
        'expiry_time':None,
        'is_tagged':False

    }

    if not member_id:
        return collabcard_status

    #member_id = User.objects.get(id=member_id)
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
    else:
        collabcard_status['state'] = state_instance.state
        collabcard_status['mute_status'] = state_instance.mute_status
        collabcard_status['follow_status'] = state_instance.follow_status
        collabcard_status['is_guest'] = state_instance.is_guest
        collabcard_status['remove'] = state_instance.remove
        collabcard_status['state_instance'] = state_instance
        collabcard_status['expiry_time'] = state_instance.expiry_time
        collabcard_status['is_tagged'] = state_instance.is_tagged
    return collabcard_status


def CollabcardPollsSerializer(poll, user, card):
    """ Poll serializer """
    # print("user--",user)
    card_instance = card
    polls = {
        'id': poll.id,
        'text': poll.text,
        'is_selected': is_poll_selected(poll, user, card) if user else False
    }

    if card.poll_type == poll_types.POLL_TYPE_INSTANT:
        poll_detail = poll_percentage(card, poll)
        polls['poll_count'] = poll_detail[0]
        polls['no_votes'] = poll_detail[0]
        polls['percentage'] = int(poll_detail[1])

    elif card.poll_type == poll_types.POLL_TYPE_DEFERRED:
        if card.end_date // 1000 <= time.time():
            poll_detail = poll_percentage(card, poll)
            polls['poll_count'] = poll_detail[0]
            polls['no_votes'] = poll_detail[0]
            polls['percentage'] = int(poll_detail[1])

    if poll.sub_text:
        polls['sub_text'] = poll.sub_text

    if poll.image_url:
        polls['image_url'] = poll.image_url

    if poll.user:
        member_profile = get_members_profile([poll.user.id],card_instance.community.id)
        polls['member'] = member_profile[0]

    # if card.end_date // 1000 <= time.time():
    #     poll_detail = poll_percentage(card, poll)
    #
    #     polls['poll_count'] = poll_detail[0]
    #     polls['percentage'] = int(poll_detail[1])

    return polls


def is_poll_selected(poll, user, card):
    """ function to know if user selected a poll or not """
    MemberPoll = MemberPollVotes.objects.filter(card=card, user=user, poll=poll)
    return MemberPoll.exists()


def poll_percentage(card, poll, current_user_id=None):
    """ function to calculate the percentage of particular poll for a card """
    total_polls = MemberPollVotes.objects.filter(card=card)
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
            return f"You and {len(user_names)-1} others voted"
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

    # if card.end_date // 1000 <= time.time():
    #     poll_detail = poll_percentage(card, poll)

    polls['poll_count'] = 0
    polls['percentage'] = 0
    polls['no_votes'] = 0

    return polls


def FormResponseSerilaizer(community_id, user_id, current_user_id=None, bl=False):
    responses = communityAnswers.objects.filter(community=community_id).filter(member=user_id).order_by('id')
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


def get_question_data(question_id, member_state, send_back, user_id=None, community_id = None):
    ''' function to get question id '''

    question_instance = question_id

    if member_state == 1 or member_state == 2:
        if user_id and community_id:
            has_right = check_admin_view_contact_right(user_id, community_id)
            if not has_right:
                questions = get_question_instance(question_instance)
                return questions

        questions = CommunityQuestionsSerializer(question_instance)
    elif send_back:
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

def check_admin_view_contact_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS)

    if user_rights.exists():
        return True
    return False


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

    if context['value'] and (context['state'] == question_states.CHOICE_SINGLE or context['state'] == question_states.CHOICE_MULTIPLE) and context['field']:
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


#member comunity profiles
def MembersSerializer(member_instance, community_id, current_user_id=None, send_profile=True,
                      is_promoter=False, is_owner=False, all_members_api=False, profile_detail_api=False,
                      user_admin_rights=None):

    user_is_owner = member_instance.is_owner
    parents_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list else []
    member_id = member_instance.member_id.id
    community_profile = get_user_profile(member_id, community_id, current_user_id=current_user_id, send_profile=send_profile)
    community_profile['state'] = member_instance.state

    # sending image  url of members
    if member_instance.image_url:
        community_profile['image_url'] = member_instance.image_url

    if member_instance.state == member_states.ADMIN or member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE:
        community_profile['route'] = """route://member_community_profile?community_id=%s&member_id=%s""" % (
            str(community_id), str(member_id))

        community_profile['member_since'] = "Member of " + member_instance.community_id.name + " since " + time.strftime('%b %d %Y',
                                                                                                           time.localtime(
                                                                                                               member_instance.created_at))
    elif member_instance.state == member_states.PENDING_MEMBER:
        community_profile['member_since'] = "Verification pending for " + member_instance.community_id.name


    if member_instance.state == member_states.ADMIN and 'question_answers' not in community_profile:
        community_profile['custom_intro_text'] = """Created this community on %s""" % (
            time.strftime("%d %B %Y", time.localtime(member_instance.created_at)))

    if (member_instance.state == member_states.MEMBER or member_instance.state == member_states.PROFILE_UNAVAILABLE) and 'question_answers' not in community_profile:
        community_profile['custom_intro_text'] = """Joined via a private community link on %s""" % (
            time.strftime("%d %B %Y", time.localtime(member_instance.created_at)))
        community_profile[
            'custom_click_text'] = """%s joined this community via a private community link on %s and hasn’t created their profile for this community yet""" % (
        member_instance.member_id.userinfo.name, time.strftime("%d %B %Y", time.localtime(member_instance.created_at)))

    # add menu for all members api and fetch community profile API

    if (all_members_api or profile_detail_api) and (is_promoter or is_owner):
        community_profile["menu"] = get_menu_for_members(current_user_id=current_user_id,item_member_id=member_id,
                             current_user_is_promoter=is_promoter, current_user_is_owner=is_owner,
                             item_member_state=member_instance.state, item_member_is_owner=user_is_owner,
                             current_user_admin_rights=user_admin_rights,parents_list=parents_list,
                             profile_detail_api=profile_detail_api)

    elif (all_members_api or profile_detail_api) and current_user_id and int(current_user_id) != int(member_id):
        community_profile["menu"] = ["Report member"]

    return community_profile


def get_menu_for_members(current_user_id, item_member_id, current_user_is_promoter, item_member_state, current_user_is_owner=False,
                         item_member_is_owner=False, current_user_admin_rights=None, parents_list=None,
                         profile_detail_api=False):
    """ function to get the menu for all members for all members api and profile detail api """
    #  x is current member , y is member whose profile is currently in iteration sequence
    # current_user_state, item_member_state,

    if parents_list is None:
        parents_list = []

    if current_user_is_owner and int(current_user_id) == int(item_member_id):
        return ["Edit title"]
    if current_user_id and int(current_user_id) == int(item_member_id):
        return []
    elif not current_user_id:
        return []

    menu = []

    if current_user_is_owner and item_member_is_owner:
        menu = ["Edit title"]
    elif current_user_is_owner and item_member_state == member_states.ADMIN:
        menu = ["Remove from community", "Edit management rights"]

    elif current_user_is_owner and item_member_state == member_states.MEMBER:
        menu = ["Remove from community", "Edit permissions", "Give community management rights"]

    elif current_user_is_promoter and item_member_state == member_states.ADMIN:

        is_child = current_user_id in parents_list

        if current_user_admin_rights:
            if current_user_admin_rights["approve"] and is_child:
                menu.append("Remove from community")

            if current_user_admin_rights["add_manager"] and is_child:
                menu.append("Edit permissions")


        if profile_detail_api:
            menu.append("Report member")

    elif current_user_is_promoter and item_member_state == member_states.MEMBER:
        if current_user_admin_rights:
            if current_user_admin_rights["approve"]:
                menu.append("Remove from community")

            if current_user_admin_rights["delete_room"] or current_user_admin_rights["approve"]:
                menu.append("Edit permissions")

            if current_user_admin_rights["add_manager"]:
                menu.append("Give community management rights")

            if not current_user_admin_rights["approve"] and profile_detail_api:
                menu.append("Report member")
        # menu = ["Remove from community", "Edit management rights", "Report member"]
    else:
        if profile_detail_api:
            menu.append("Report member")

    return menu


def get_user_profile(user_id, community_id, current_user_id=None, send_profile=True,remove=False):


    if isinstance(user_id,User):
        user_instance = user_id

        if not user_instance:
            return {}
    else:
        try:
            user_instance = User.objects.get(id=user_id)
        except:
            return {}

    userinfo_serialized_object = UserinfoSerializer(user_instance.userinfo)

    #if member is not a part of community
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

            if user_admin_rights and not user_admin_rights["approve"]:
                if member_filter[0].state == member_states.PENDING_MEMBER:
                    continue

            community_profile = MembersSerializer(member_filter[0], community_id, current_user_id=current_user_id,
                                                  send_profile=send_profile, all_members_api=all_members_api,
                                                  profile_detail_api=profile_detail_api, user_admin_rights=user_admin_rights,
                                                  is_owner=is_owner, is_promoter=is_promoter
                                                  )
            member_profile_list.append(community_profile)

        else:
            temp = get_user_profile(id, community_id, current_user_id=current_user_id,send_profile=send_profile,remove=remove)
            temp['state'] = 0
            member_profile_list.append(temp)

    return member_profile_list


def report_serializer(report_instance):

    community_id = report_instance.community.id
    report = {"community_id": community_id}

    if report_instance.tag:
        report["tag"] = report_tag_serializer(report_instance.tag)

    if report_instance.reason:
        report["reason"] = report_instance.reason

    if report_instance.user_reported:
        user_profile = get_members_profile(member_ids=[report_instance.user_reported.id], community_id=community_id)
        report["user_reported"] = user_profile

    if report_instance.reported_by:
        user_profile = get_members_profile(member_ids=[report_instance.reported_by.id], community_id=community_id)
        report["user_reported"] = user_profile

    if report_instance.type is not None:
        report["type"] =report_instance.type

    if report_instance.action_taken_tag:
        report["tag"] = report_tag_serializer(report_instance.action_taken_tag)

    if report_instance.action_taken_reason:
        report["reason"] = report_instance.action_taken_reason

    if report_instance.action_taken_by:
        user_profile = get_members_profile(member_ids=[report_instance.action_taken_by.id], community_id=community_id)
        report["user_reported"] = user_profile

    if report_instance.action_taken is not None:
        report["action_taken"] = report_instance.action_taken

    if report_instance.rights_added is not None:
        report["rights_added"] = json.loads(report_instance.rights_added)

    if report_instance.rights_removed is not None:
        report["rights_removed"] = json.loads(report_instance.rights_removed)

    if report_instance.is_closed:
        report["is_closed"] = report_instance.is_closed

    if report_instance.closed_by is not None:
        user_profile = get_members_profile(member_ids=[report_instance.closed_by.id], community_id=community_id)
        report["closed_by"] = user_profile

    if report_instance.closed_time:
        report["closed_on"] = report_instance.closed_time

    report["reported_on"] = report_instance.date_epoch

    return report


def report_tag_serializer(tag_instance):
    tag_dict = {'id': tag_instance.tag_id,
                "name": tag_instance.tag_name}

    return tag_dict



