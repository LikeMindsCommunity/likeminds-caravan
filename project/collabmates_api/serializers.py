import json
import time

from django.conf import settings
from django.db.models import Q
from togther.models import *
from togther.models import *
from utility.utils import is_IG_community,is_LG_or_LP_community,feedback_community_id,\
    generate_private_link,generate_random,get_time_text,eligibility_count
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
    new_dict['members_count'] = get_member_count(community)
    new_dict['state']=int(community.hide_community)

    #generating private link
    if promoter_id:
        new_dict['private_link'] = generate_private_link(community_instance=community,
                                                                  promoter_instance=promoter_id)


    is_ig = is_IG_community(community)
    if is_LG_or_LP_community(community):
        community_type=1
        new_dict['community_type'] = community_type
    elif is_IG_community(community):
        community_type=0
        new_dict['community_type'] = community_type

    if community.type:
        new_dict['type']=community.type
    if community.sub_type:
        new_dict['sub_type'] = community.sub_type

    if not is_ig:
        new_dict[
            'share_text_admin'] = """Hi, I am trying to gather %s community on LikeMinds. It will be good if you can join it.\n""" % (
        new_dict['name'])
        new_dict[
            'share_text_member'] = """I recently joined %s community on LikeMinds. It will be good if you also join this community.\n""" % (
        new_dict['name'])
        new_dict[
            'share_text_anonymous'] = """I recently discovered %s community on LikeMinds. You can join this community using this link.\n""" % (
        new_dict['name'])
    else:
        new_dict[
            'share_text_admin'] = """Hi, I am trying to gather %s community on CollabMates. It will be fun if you can join it.\n""" % (
        new_dict['name'])
        new_dict[
            'share_text_member'] = """I recently joined %s community on CollabMates. It will be fun if you also join this community.\n""" % (
        new_dict['name'])
        new_dict[
            'share_text_anonymous'] = """I recently discovered %s community on CollabMates. You can join this community using this link.\n""" % (
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
        'share_url': url + '/collabcard/' + str(card.id) + "?ref_id=" + str(card.user.id),
        'answer_text': card.answer_text,
        'share_link': card.share_link,
        'image_count': card.image_count,
        'pdf_count': card.pdf_count,
        'type': card.type,
        'date_time': card.date_time,
        'duration': card.duration,
        'answers_count':card.answers_count,
        'attending_count': card.attending_count,
        'polls_count': card.polls_count
    }

    if card.community.image_link_round:
        collabcard['image_url_round'] = card.community.image_link_round

    if card.type == card_types.CARD_POLL:
        polls = []
        cardPolls = CollabcardPolls.objects.filter(card=card)
        for poll in cardPolls:
            polls.append(CollabcardPollsSerializer(poll, user, card))

        collabcard['polls'] = polls


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
        #co_host_list = list(map(int, co_host_list))

        collabcard['co_hosts'] = get_members_profile(member_ids=co_host_list,community_id=card.community.id,
                                                     current_user_id=user)

    if card.online_link:
        collabcard['online_link'] = card.online_link

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


def CollabcardPollsSerializer(poll, user, card):
    """ Poll serializer """

    polls = {
        'id': poll.id,
        'text': poll.text,
        'is_selected': is_poll_selected(poll, user, card),
    }

    if card.date_time // 1000 <= time.time():
        polls['percentage'] = int(poll_percentage(card, poll))

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
        return 0
    return selected_polls/total_polls * 100


def get_member_count(community):
    return Members.objects.filter(community_id=community).filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state = 8)).count()

def get_members_profile(member_ids,community_id,current_user_id):

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
                userinfo_serialized_object['response'] = form_response[0]
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
            temp['question_instance'] = questions               #sending the question instance
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