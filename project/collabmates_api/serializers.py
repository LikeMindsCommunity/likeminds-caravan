import json
import time

from django.conf import settings
from django.db.models import Q
from togther.models import *
from togther.models import *
from utility.utils import is_IG_community,is_LG_or_LP_community,feedback_community_id

url = settings.URL

#
# class CommunitySerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Community
#         fields = ('id','name', 'purpose', 'image_url' ,'about', 'location')

def CommunitySerializer(community):
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


    if is_IG_community(community):
        community_type=0
        new_dict['community_type'] = community_type
    elif is_LG_or_LP_community(community):
        community_type=1
        new_dict['community_type'] = community_type

    if community.type:
        new_dict['type']=community.type
    if community.sub_type:
        new_dict['sub_type'] = community.sub_type


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

    if card.type == 3:
        polls = []
        cardPolls = CollabcardPolls.objects.filter(card=card)
        for poll in cardPolls:
            polls.append(CollabcardPollsSerializer(poll, user, card))

        collabcard['polls'] = polls

    if card.og_tags:
        og_tags = json.loads(card.og_tags)
        collabcard['og_tags'] = og_tags

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


def FormResponseSerilaizer(community_id, user_id,bl=False):

    responses = communityAnswers.objects.filter(community=community_id).filter(member=user_id).order_by('id')
    if not responses.exists():
        return None
    user_response = []
    new_response=[]
    for response in responses:
        # getting the answers of the users who requested to join
        # for the questions that have been asked while requestiong to join in a community
        response_object = {}
        response_object['key'] = response.question_title
        response_object['value'] = response.question_answer


        temp={}
        questions = get_question_data(response.question_id)
        temp['community_id'] = community_id
        temp['member_id'] = user_id
        temp['question_title'] = response.question_title
        temp['value'] = response.question_answer
        temp['question_id'] = response.question_id
        temp['state'] = questions['state']
        temp['question_instance'] = questions
        new_response.append(temp)

        user_response.append(response_object)

    if not bl:
        return user_response
    return (user_response,new_response)


def get_question_data(question_id):

    '''function to get question id'''

    question_instance=communityQuestions.objects.get(id=question_id)

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
