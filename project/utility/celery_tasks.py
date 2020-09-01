from __future__ import absolute_import, unicode_literals
from celery import shared_task
from togther.models import *
import time
from django.db.models import Q

from utility.utils import (decode_meta_from_url, update_tag_image,
                           referal, get_referred_members_of_a_member,
                           eligibility_count, notify_referred_member,
                           user_onbaord, update_member_count,
                           update_community_tags_to_user,tutorial_count,
                           #custom_cache,cache_timeout,
                           get_city_address,
                           update_user_geography_tags, create_or_categorize_tag,
                           insert_user_home_town_tags,user_onbaord,is_IG_community,
                           is_member_engage)

import logging
error_logger = logging.getLogger("error_logger")
info_logger = logging.getLogger("info_logger")

@shared_task
def update_referral_text_in_engage_table(community_id):

    '''function to update the referal text in member engage table by taking member engage object'''
    # getting the state of member
    community = Community.objects.get(pk = community_id)
    engage_communities=Member_Engage.objects.filter(community_id=community)

    for each_community in engage_communities:
        community={}
        community['pending_members_count']=each_community.pending_members
        community['member_referral']=""
        member_state = Members.objects.filter(community_id=each_community.community_id.id,
                                              member_id=each_community.member_id.id)
        if member_state:
            state = member_state[0].state
            community_state = each_community.community_id.hide_community
            # if the community is pilot community and member has shown interest

            if community_state == '3' and state == 8:
                diff = eligibility_count - community['pending_members_count']
                if community['pending_members_count'] < (eligibility_count-2):
                    community['member_referral']="""[Pilot] Help this community find a promoter"""
                elif community['pending_members_count'] >= (eligibility_count-2) and  community['pending_members_count'] < (eligibility_count):
                    community['member_referral'] = """You have successfully referred %s. Refer %s and become promoter of this community."""%(community['pending_members_count'],diff)

            # if the community is pilot community and the member is eligible promoter
            elif community_state == '3' and state == 9:
                community['member_referral'] = "You are eligible to become a promoter of this community"

            # if the community is pilot-active and new promoter comes
            elif community_state == '4' and state == 9:
                community['member_referral'] = "You are eligible to become a promoter of this community"

            # if the community becomes a pilot-active community and member approval is pending
            elif (community_state == '4' or community_state == '0' or community_state == '1') and state == 3:
                community['member_referral'] = "Your request is waiting for approval by promoter"

            # if the community becomes a pilot-active community and member request is approved
            # elif community_state == '4' and state == 4:
            #     diff = eligibility_count - community['pending_members_count']
            #     if community['pending_members_count'] == 1:
            #         community['member_referral'] = """You have successfully referred %s member. Please refer %s more to become promoter.""" % (
            #             community['pending_members_count'], diff)
            #     elif community['pending_members_count']:
            #         community[
            #             'member_referral'] = """You have successfully referred %s members. Please refer %s more to become promoter.""" % (
            #             community['pending_members_count'], diff)
            elif community_state == '0' and community['pending_members_count']:
                if community['pending_members_count'] == 1:
                    community['member_referral'] = str(community['pending_members_count']) + " new member request"
                elif community['pending_members_count'] > 1:
                    community['member_referral'] = str(community['pending_members_count']) + " new member requests"

            each_community.member_referral=community['member_referral']
            each_community.member_state=state
            each_community.save()


@shared_task
def save_community_purpose_card(community_id,card_id):
    time.sleep(2)
    community = Community.objects.get(id=community_id)
    community.purpose_collabcard = card_id
    community.save()


@shared_task
def update_communities_in_member_engage_table(member_id):

    '''function to update the user communities in engage table'''

    all_members=Members.objects.filter(member_id=member_id)
    c=0
    for member in all_members:
        community_id=member.community_id
        if community_id.hide_community == '3':
            community =Community.objects.get(id=community_id.id)
            user=User.objects.get(id=member_id)
            if not is_member_engage(community,user):
                engage=Member_Engage()
                engage.community_id=community
                engage.member_id=user
                engage.updated_at=time.time()
                pending_count= get_referred_members_of_a_member(community.id,member_id)
                engage.pending_members=len(pending_count)
                engage.save()
                info_logger.info("Communities")
                info_logger.info(community)
                c=c+1
            update_referral_text_in_engage_table(community.id)
    info_logger.info(c)


@shared_task
def update_last_unseen_in_engage_on_card_creation(community_id):
    '''function to update the unseen  collabcard in engage when a new collabcard is posted in community
       for all members in the community'''
    community_members = Members.objects.filter(community_id = community_id).filter(Q(state=1)|Q(state=2)|
                                                                                   Q(state=4)|Q(state=7))

    for member in community_members:
        print("member >>>>>    ",member.member_id.id)
        update_last_unseen_in_engage(user=member.member_id.id, community=community_id,is_seen=True)


def update_last_unseen_in_engage(user='',community='',is_seen=False):

    '''function to update the unseen  collabcard in engage'''

    total_chatrooms = Collabcard.objects.filter(community=community).distinct('id').count()
    print("total_chatrooms--",total_chatrooms)
    seen_chatrooms = collabcardState.objects.filter(community=community,user=user).distinct('card').count()
    print("seen_chatrooms--", seen_chatrooms)
    diff = total_chatrooms - seen_chatrooms

    unseen_count = 0
    if diff <= 0:
        unseen_count = 0
    else:
        unseen_count = diff
    print(unseen_count)
    if not is_seen:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(last_unseen_count=unseen_count
                                                                                    )
    else:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(
            last_unseen_count=unseen_count,
            updated_at=time.time()
        )

    # total_collabcards = Collabcard.objects.filter(community=community).filter(~Q(type=4)).values('id').order_by('-id').distinct('id')
    # seen_collabcard = collabcardState.objects.filter(community=community,
    #                                                  user=user).values('card').distinct('card')
    # # print("total_collabcards                >>>>>>>    ", total_collabcards)
    # # print("seen_collabcard                >>>>>>>    ", seen_collabcard)
    #
    # unseen_count=total_collabcards.count() - seen_collabcard.count()
    # if unseen_count<= 0:
    #     # if zero or less than zero , unseen card count = 0
    #     collabcard_unseen = 0
    # else:
    #     collabcard_unseen = (total_collabcards.count() - seen_collabcard.count())
    #
    # unseen_list = total_collabcards.difference(seen_collabcard).values('id').order_by('id')
    # # print("unseen_list                >>>>>>>    ", unseen_list)
    #
    # if total_collabcards.count() > 0:
    #     # if community has atleast one card
    #     if unseen_list.count() != 0:
    #         # if the unseen cards are present
    #         # show the latest unseen cards text
    #         card = Collabcard.objects.get(id=unseen_list.values('id')[0]['id'])
    #
    #     else:
    #         # if no unseen cards , show latest card text
    #         card = Collabcard.objects.get(id=total_collabcards.values('id')[0]['id'])
    #     # print("card                >>>>>>>    ",card)
    #     current_time=time.time()
    #     # print("current_time        >>>>>>>    ",current_time)
    #     # print("collabcard_unseen   >>>>>>>    ",collabcard_unseen)
    #
    #     # member = Member_Engage.objects.get(community_id=community,member_id=user)
    #     # member.last_unseen_count=collabcard_unseen
    #     # member.last_unseen_conversation=card
    #     # member.updated_at=current_time
    #     # member.save()
    #
    #     #when a new card is created updating time for all members
    #     if not is_seen:
    #         Member_Engage.objects.filter(community_id=community, member_id=user).update(last_unseen_count=collabcard_unseen,
    #                                                                                 last_unseen_conversation=card,
    #                                                                                 )
    #     else:
    #         Member_Engage.objects.filter(community_id=community, member_id=user).update(
    #             last_unseen_count=collabcard_unseen,
    #             last_unseen_conversation=card,updated_at=current_time
    #             )

    # # if is_seen == False:
    # #     Member_Engage.objects.filter(community_id=community).filter(~Q(member_id=user)).update(last_unseen_count=collabcard_unseen,updated_at=current_time)



@shared_task
def update_my_chatrooms_for_users(chatroom_id,user_id=None):


    conversation_engage_filter = conversationEngage.objects.filter(card_id=chatroom_id)
    if not user_id:
        user_list = list(conversation_engage_filter.values_list('user_id',flat=True))
    else:
        user_list = [user_id]
    conversations = card_answers.objects.filter(card_id=chatroom_id).filter(state = 0).order_by('id')
    last_conversation = conversations.last()
    length = len(conversations)
    next_unseen_conversation = {}
    unseen_count = {}
    first_conversation = None
    for i in range(length):

        if i+1 < length:
            next_unseen_conversation[conversations[i].id] = conversations[i+1]
        else:
            next_unseen_conversation[conversations[i].id] = conversations[i]

        unseen_count[conversations[i].id] = length - i - 1

        if not first_conversation:
            first_conversation = conversations[i].id

    # print(next_unseen_conversation)
    # print("\n\n")
    # print(unseen_count)
    # print(user_list)
    for user in user_list:

        has_seen = conversationMemberState.objects.filter(card_id=chatroom_id,user_id=user)

        if has_seen.exists():
            seen_id = has_seen[0].conversation.id
            conversation_engage_filter.filter(user=user).update(
                last_conversation=last_conversation,
                updated_at = time.time(),unseen_count = unseen_count[seen_id])
        else:
            conversation_engage_filter.filter(user=user).update(
                last_conversation = last_conversation,
                updated_at=time.time(),unseen_count=length)



