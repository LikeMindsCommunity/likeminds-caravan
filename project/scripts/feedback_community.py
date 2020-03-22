from django.contrib.auth.models import User
from togther.models import (Community, Members,
                            Collabcard, Member_Engage,Userinfo)
from utility.states import member_states
import time


feedback_community_id = 48640
feedback_collabcard_id = 664

def is_member_engage(community,member):

    '''function to check if data is presnt in member engage table or not'''

    is_present=False
    member_data=Member_Engage.objects.filter(community_id=community,member_id=member)
    if member_data.exists():
        is_present=True
    return is_present

def create_member_for_feedback_community(user_instance):

    '''function to make user directly a member of feedback community'''

    is_member=Members.objects.filter(community_id=feedback_community_id,member_id=user_instance)

    community_instance = Community.objects.get(id=feedback_community_id)

    if not is_member.exists():                                                #not is_member.exists()
        member_instance=Members()
        member_instance.member_id=user_instance
        member_instance.community_id=community_instance
        member_instance.state=member_states.MEMBER
        member_instance.created_at=time.time()
        member_instance.save()
    else:
        #print("member already exists")
        pass


    if not is_member_engage(community_instance,user_instance):          #not is_member_engage(community_instance,user_instance)

        card_instance=Collabcard.objects.get(id=feedback_collabcard_id)
        engage = Member_Engage()
        engage.member_id = user_instance
        engage.community_id = community_instance
        engage.last_unseen_conversation = card_instance
        engage.updated_at = time.time()
        engage.member_state = member_states.MEMBER
        engage.save()
    else:
        #print("member engage already exists")
        pass


def add_user_to_feedback_community():

    users = Userinfo.objects.all()

    for user in users:
        print("user  == ", user.user_id.id)
        create_member_for_feedback_community(user.user_id)


print("script started")
add_user_to_feedback_community()
print("script ended")

