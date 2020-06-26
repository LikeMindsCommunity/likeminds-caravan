import json
import time

from django.conf import settings
from django.db.models import Q
from togther.models import *
from utility.utils import is_IG_community,is_LG_or_LP_community,feedback_community_id,\
    generate_private_link,generate_random,get_time_text,eligibility_count,get_members_count_in_community
from utility.states import card_types
url = settings.URL
import ast

#
# class CommunitySerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Community
#         fields = ('id','name', 'purpose', 'image_url' ,'about', 'location')







def CommunitySerializer(community,promoter_id=0):
    # function to serialize a community object
    new_dict =  {
        'id': community.id,
        'name': community.name,
        'purpose': community.purpose,
        'location': community.location if community.location else "",

    }

    if community.about:
        new_dict['about'] = community.about

    if community.image_link:
        new_dict['image_url']=community.image_link
    elif community.image_url:
        new_dict['image_url'] = community.image_url.url
    else:
        new_dict['image_url'] = '/media/media/community/default.jpeg'

    if community.image_link_round:
        new_dict['image_url_round'] = community.image_link_round


    if new_dict['image_url'] == "/media/https%3A/upload.wikimedia.org/wikipedia/en/0/09/Community_title.jpg":
        new_dict['image_url'] = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQMUCHvC0wEVO5yDMe9wddUoagIqQ3VPH0nm8_VtjK5gk3M0mMO'
    elif not community.image_link:
        new_dict['image_url'] = url + new_dict['image_url']
    new_dict['is_member'] = ''
    if feedback_community_id != community.id:
        new_dict['share_url'] = url + '/community/' + str(new_dict['id'])
    else:
        new_dict['share_url'] = ""
    new_dict['date'] = community.active_since
    new_dict['members_count'] = get_members_count_in_community(community.id)
    new_dict['state']=int(community.hide_community)

    #generating private link
    if promoter_id:
        private_link = generate_private_link(community_instance=community,
                                                                  promoter_instance=promoter_id)
        new_dict['private_link'] = private_link
        new_dict['private_link_members_directory'] = private_link + "&source=members_directory"



    if community.type:
        new_dict['type']=community.type
    if community.sub_type:
        new_dict['sub_type'] = community.sub_type


    new_dict[
            'share_text_admin'] = """Hi, I am trying to gather %s community on LikeMinds. It will be good if you can join it.\n""" % (
    new_dict['name'])
    new_dict[
            'share_text_member'] = """I recently joined %s community on LikeMinds. It will be good if you also join this community.\n""" % (
    new_dict['name'])
    new_dict[
            'share_text_anonymous'] = """I recently discovered %s community on LikeMinds. You can join this community using this link.\n""" % (
    new_dict['name'])


    new_dict['min_referrer_member'] = eligibility_count




    return new_dict

def UserinfoSerializer(user):
    # function to serialize a userinfo object
            #if the community is not feedback community
    userinfo = {
        'id': user.user_id.id,
        "name": user.name,
        "email": user.email,
        "city": user.city,
        "headline": user.headline,
        "contact_number": user.contact_number,
        "about": user.about,
        "fb_link": user.fb_link,
        "linkedin_link": user.linkedin_link,
    }

    if not user.image_link:
        userinfo['image_url'] = url + user.image_file.url
    else:
        userinfo['image_url'] = user.image_link

    return userinfo

def CollabcardSerializer(card,user,community=None):
    # function to serialize a community object
    collabcard={
        'id': card.id,
        'title': card.title,
        'community_id': card.community_id,
        'share_url': url + '/collabcard/' + str(card.id), #+ "?ref_id=" + str(card.user.id),
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count': card.image_count,
        'pdf_count': card.pdf_count,
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        'answers_count':card.answers_count,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count,
        'card_creation_time' : time.strftime('%B %d at %H:%M',time.localtime(card.date_epoch))
    }

    if card.community.image_link_round:
        collabcard['image_url_round'] = card.community.image_link_round

    #for poll card
    if card.type == card_types.CARD_POLL:
        polls = []
        cardPolls = CollabcardPolls.objects.filter(card=card).order_by('id')
        for poll in cardPolls:
            polls.append(CollabcardPollsSerializer(poll, user, card))

        collabcard['polls'] = polls

        collabcard['multiple_select'] = card.multiple_select
        collabcard['multiple_select_no'] = card.multiple_select_no
        collabcard['multiple_select_state'] = card.multiple_select_state

    #for event card
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
            #co_host_list = [36]
            #print(user)
            if not user:
                user = None

            collabcard['co_hosts'] = get_members_profile(member_ids=co_host_list,community_id=card.community.id,
                                                         current_user_id=user)

        if card.online_link:
            collabcard['online_link'] = card.online_link



    #for sending header
    if card.header:
        collabcard['header'] = card.header
    else:
        collabcard['header'] = get_chatroom_name(card.user.userinfo.name,card.type)

    if card.og_tags:
        og_tags = json.loads(card.og_tags)
        collabcard['og_tags'] = og_tags

    #FOR PURPOSE CARD
    if card.updated_member:
        member_ids = [card.updated_member]
        temp=get_members_profile(member_ids=member_ids,community_id=card.community_id,current_user_id=user)
        collabcard['updated_member'] = temp[0]

    if card.updated_time:
        collabcard['updated_time'] = get_time_text(card.updated_time)

    return collabcard


def get_collabcard_files(card_id):
    '''function to return pdf and image files of a collabcard'''

    files = Card_Attachment.objects.filter(collabcard=card_id)
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

def conversationSerializer(conversation):

    temp = {
        "id":conversation.id,
        "answer":conversation.answer,
        "state" : conversation.state,
        "member" : UserinfoSerializer(conversation.user.userinfo)
    }

    answer_files = get_answer_files(temp['id'])

    temp['images'] = answer_files['image']
    temp['pdf'] = answer_files['pdf']

    if 'location' in answer_files:
        temp['location'] = answer_files['location']



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
                'location_name' : file.location_name,
                'location_lat' : file.location_lat,
                'location_long' : file.location_long

            }
            files['location'] = location


    files['image'] = img_list
    files['pdf'] =pdf
    return files


def get_chatroom_name(user_name,type):

    '''function to create chatroom name'''

    if len(user_name) > 1:
        user_name = user_name.split(" ")
        user_name = user_name[0]

    if type == card_types.CARD_PUBLIC_EVENT  or type == card_types.CARD_EVENT:
        chatroom_name = """%s's Event"""%(user_name)
    elif type == card_types.CARD_POLL:
        chatroom_name = """%s's Poll""" % (user_name)
    elif type == card_types.CARD_PURPOSE:
        chatroom_name = """Onboarding Room"""
    elif type == card_types.CARD_INTRO:
        chatroom_name = """%s's Intro"""%(user_name)
    else:
        chatroom_name = """%s's Chat Room"""%(user_name)


    return chatroom_name

def get_chatroom_instance(card_instance,member_id):

    collabcard_serializer = CollabcardSerializer(card_instance, member_id)

    collabcard_member = get_members_profile([card_instance.user.id], card_instance.community.id)
    if collabcard_member:
        collabcard_serializer['member'] = collabcard_member[0]

    status = get_status_of_collabcard(member_id,card_instance)
    collabcard_serializer['state'] = status['state']
    collabcard_serializer['mute_status'] = status['mute_status']
    collabcard_serializer['follow_status'] = status['follow_status']

    collabcard_files = get_collabcard_files(collabcard_serializer['id'])

    collabcard_serializer['images'] = collabcard_files[0]
    collabcard_serializer['pdf'] = collabcard_files[1]
    return collabcard_serializer


def get_status_of_collabcard(member_id,card):
    '''function to get the state of collabcard'''

    collabcard_status = {
        'state' : 0,
        'mute_status' : False,
        'follow_status' : False
    }

    if not member_id:
        return collabcard_status

    member_id = User.objects.get(id=member_id)
    collabcard_state = collabcardState.objects.filter(card=card, user=member_id)

    if collabcard_state.exists():
        collabcard_status['state'] = collabcard_state[0].state
        collabcard_status['mute_status'] = collabcard_state[0].mute_status
        collabcard_status['follow_status'] = collabcard_state[0].follow_status
    return collabcard_status


def CollabcardPollsSerializer(poll, user, card):
    """ Poll serializer """
    #print("user--",user)
    polls = {
        'id': poll.id,
        'text': poll.text,
        'is_selected': is_poll_selected(poll, user, card) if user else False
    }

    if poll.sub_text:
        polls['sub_text'] = poll.sub_text

    if poll.image_url:
        polls['image_url'] = poll.image_url

    if card.end_date // 1000 <= time.time():
        poll_detail = poll_percentage(card, poll)

        polls['poll_count'] = poll_detail[0]
        polls['percentage'] = int(poll_detail[1])

    return polls


def is_poll_selected(poll, user, card):
    """ function to know if user selected a poll or not """
    MemberPoll = MemberPollVotes.objects.filter(card=card, user=user, poll=poll)
    return MemberPoll.exists()


def poll_percentage(card, poll):
    """ function to calculate the percentage of particular poll for a card """
    total_polls = MemberPollVotes.objects.filter(card=card)
    selected_polls = total_polls.filter(poll=poll).count()
    total_polls = total_polls.count()

    if total_polls == 0:
        return 0,0
    return selected_polls,selected_polls/total_polls * 100


# def get_member_count(community):
#     return Members.objects.filter(community_id=community).filter(
#         Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state = 8)).count()

def get_members_profile(member_ids,community_id,current_user_id=None):

    '''function to get member profile from list of members ids'''
    member_profile_list = []
    for id in member_ids:
        member_filter = Members.objects.filter(member_id=id,community_id=community_id)

        if member_filter.exists():
            member_id = member_filter[0].member_id.id
            member=member_filter[0]
            userinfo_serialized_object = UserinfoSerializer(member.member_id.userinfo)
            userinfo_serialized_object['state'] = member.state

            form_response = FormResponseSerilaizer(community_id, member_id, bl=True,
                                                   current_user_id=current_user_id)

            if form_response:
                #userinfo_serialized_object['response'] = form_response[0]
                userinfo_serialized_object['question_answers'] = form_response[1]

            member_profile_list.append(userinfo_serialized_object)

    return member_profile_list

def FormResponseSerilaizer(community_id, user_id,current_user_id=None,bl=False):

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

        send_back=False
        if str(response.member.id) == str(current_user_id):
            send_back = True

        temp={}
        questions = get_question_data(response.question, member_state, send_back=send_back)
        if questions:
            temp['community_id'] = community_id
            temp['member_id'] = user_id
            temp['question_title'] = response.question_title
            temp['value'] = response.question_answer
            temp['question_id'] = response.question_id
            temp['state'] = questions['state']
            #temp['question_instance'] = questions               #sending the question instance
            new_response.append(temp)

        user_response.append(response_object)

    if not bl:
        return user_response
    return (user_response,new_response)


def get_question_data(question_id, member_state, send_back):

    '''function to get question id'''

    question_instance=question_id

    if member_state == 1 or member_state == 2 or send_back:
        questions = CommunityQuestionsSerializer(question_instance)
    else:
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

    return {
        'id':community_question_instance.id,
        'question_title':community_question_instance.question_title,
        'value':community_question_instance.value,
        'optional':community_question_instance.optional,
        'community_id':community_question_instance.community_id,
        'state':community_question_instance.question_state,
        'help_text':community_question_instance.help_text if community_question_instance.help_text else ''
    }


def communityTypeSerializer(communityTypeInstance):

    return {

        'id':communityTypeInstance.id,
        'type':communityTypeInstance.typ,
        'next_input_title':communityTypeInstance.next_input_title
    }


def communitySubtypeSerializer(communitySubtypeInstance):

    return {
        'id':communitySubtypeInstance.id,
        'sub_type':communitySubtypeInstance.sub_typ
    }


def masterQuestionSerializer(masterQuestionInstance):


    json_dict = {
        'type_id': masterQuestionInstance.typ_id,
        'sub_type_id': masterQuestionInstance.sub_type_id,
        'state' : masterQuestionInstance.state,
        'question_title': masterQuestionInstance.question_title
    }

    if masterQuestionInstance.value:
        json_dict['value'] = masterQuestionInstance.value
    if masterQuestionInstance.help_text:
        json_dict['help_text'] = masterQuestionInstance.help_text

    return json_dict

def removedMembersSerializer(community_id,member_id):

    removed_filter = removedMembers.objects.filter(community_id=community_id,member_id=member_id)

    if removed_filter.exists():
        removed_state = removed_filter[0].removed_state
        return removed_state

    return False


def createCommunityActionSerializer(instance):

    temp = {
    'step_no': instance.step_no,
    'step_title' : instance.step_title,
    'max_point' : instance.max_point,
    'current_point' : instance.current_point
    }

    if instance.step_subtitle:
        temp['step_sub_title'] = instance.step_subtitle

    return temp


def chatroomActionsSerializer(instance):

    temp = {
        'id':instance.id,
        'title':instance.title
    }

    if instance.route:
        temp['route']  = instance.route

    return temp




def communityLevelsSerializer(instance):

    temp = {}
    temp['level_no'] = instance.level
    temp['title'] = instance.title
    temp['sub_title'] = instance.sub_title
    temp['state'] = instance.state
    temp['image'] = instance.image

    if instance.joined_members != None:
        temp['joined_members'] = instance.joined_members

    if instance.max_members != None:
        temp['max_members'] = instance.max_members

    if instance.action:
        temp['action'] = instance.action

    return temp


def communityFieldTypeSerializer(instance):

    return {
        'id' : instance.id,
        'type':instance.type,
        'sub_type_header' : instance.sub_type_header
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
        'type' : instance.type.id,
        'sub_type':instance.sub_type.id,
        'field':instance.field
    }