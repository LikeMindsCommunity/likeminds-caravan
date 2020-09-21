from togther.models import Collabcard, card_answers, conversationEngage, collabcardState,\
    Member_Engage,Members,Userinfo,User
import time
from django.db.models import Q
import json


HOURS_24 = 86400


def get_expiry_time_of_chatroom(card_state_instance=None):
    '''function to get expiry time of chatroom'''
    expiry_time = time.time() + 86400

    if card_state_instance:
        if card_state_instance.expiry_time and card_state_instance.expiry_time > expiry_time:
            expiry_time = card_state_instance.expiry_time

    return expiry_time


def update_activity_in_chatroom(card_instance, user_instance):
    '''function to update activities in chatrooms

    in collabcardState table and conversationEngage table'''
    engage_filter = conversationEngage.objects.filter(card=card_instance, user=user_instance)
    # expiry_time = get_expiry_time_of_chatroom()
    if engage_filter.exists():
        engage_instance = engage_filter[0]
        unread_count = engage_instance.unseen_count

        state_filter = collabcardState.objects.filter(card=card_instance, user=user_instance)
        expiry_time = get_expiry_time_of_chatroom(card_state_instance=state_filter[0])

        if unread_count > 0:
            if state_filter.exists():
                state_filter[0].expiry_time = None
                state_filter[0].save()
        else:

            expire_at = get_expire_at(card_instance)

            state_filter.update(expiry_time=expire_at)


def get_new_chatroom_members(member_id, community_id):
    """ to get the member objects for new chatrooms created """
    last_instance = collabcardState.objects.filter(user=member_id, community=community_id,external_seen=True).last()


    if last_instance:
        last_card = last_instance.card
        unseen_chatrooms = Collabcard.objects.filter(community=community_id,id__gt=last_card.id).distinct('user_id')
    else:
        unseen_chatrooms = Collabcard.objects.filter(community=community_id).distinct('user_id')



    member_list = []
    for card in unseen_chatrooms:

        member_filter = Members.objects.filter(member_id=card.user, community_id=community_id)
        image_url = card.user.userinfo.image_link if card.user.userinfo.image_link  else ''
        if member_filter.exists():
            member_instance = member_filter[0]
            if member_instance.image_url:
                image_url = member_instance.image_url


        member = get_user_profile(card.user.id,community_id,send_profile=False)
        member['image_url'] = image_url
        member_list.append(member)

        if len(member_list) > 3:
            break

    return member_list


def UserinfoSerializer(user):
    # function to serialize a userinfo object
    # if the community is not feedback community
    userinfo = {
        'id': user.user_id.id,
        "name": user.name,

    }

    if user.image_link:
        userinfo['image_url'] = user.image_link

    return userinfo

def get_user_profile(user_id, community_id, current_user_id=None, send_profile=True):


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
    # userinfo_serialized_object['state'] = 0

    if not send_profile:
        return userinfo_serialized_object


    return userinfo_serialized_object


def get_expire_at(card_instance):

    last_conversation = card_answers.objects.filter(card=card_instance, state=0).last()
    if last_conversation:
        expire_at = last_conversation.created_at + HOURS_24
    else:
        expire_at = card_instance.date_epoch + HOURS_24

    return expire_at



def get_all_chatroom_states():
    chatroooms = collabcardState.objects.filter(remove=None).order_by('id')
    for data in chatroooms:

        card_instance = data.card
        user_instance = data.user
        follow_status = data.follow_status


        if follow_status:
            update_activity_in_chatroom(card_instance, user_instance)
        else:
            if not data.expiry_time:
                data.expiry_time = get_expire_at(card_instance)
                data.save()

        print(card_instance)
        print(user_instance.userinfo.name)
        print("\n")


def set_chatroom_state_for_all_members_on_card_creation(community_id,card_id):

    card_instance = Collabcard.objects.get(id=card_id)
    all_members = Members.objects.filter(community_id=community_id).filter(Q(state=4)|Q(state=1)|Q(state=9))
    for data in all_members:

        state_filter = collabcardState.objects.filter(user=data.member_id,card=card_instance)
        if not state_filter.exists():
            user_instance = data.member_id
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = card_instance
            collabcard_state_instance.community = card_instance.community
            collabcard_state_instance.user = user_instance
            collabcard_state_instance.state = 0
            collabcard_state_instance.created_at = time.time()
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.external_seen = False
            collabcard_state_instance.expiry_time = None

            # print(data.member_id)
            # print(card_instance.id)
            collabcard_state_instance.save()

        update_last_unseen_in_engage(user=data.member_id.id, community=community_id, is_seen=False)


def update_last_unseen_in_engage(user='',community='',is_seen=False):

    '''function to update the unseen  collabcard in engage'''

    total_chatrooms = Collabcard.objects.filter(community=community).distinct('id').count()
    #print("total_chatrooms--",total_chatrooms)
    seen_chatrooms = collabcardState.objects.filter(community=community,user=user,external_seen=True).distinct('card').count()
    #print("seen_chatrooms--", seen_chatrooms)
    diff = total_chatrooms - seen_chatrooms

    unseen_count = 0
    if diff <= 0:
        unseen_count = 0
    else:
        unseen_count = diff



    if not is_seen:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(last_unseen_count=unseen_count)
    else:
        Member_Engage.objects.filter(community_id=community, member_id=user).update(
            last_unseen_count=unseen_count,
            updated_at=time.time()
        )

    if unseen_count > 0:
        member_instances = get_new_chatroom_members(user, community)
        if len(member_instances) > 0:
            Member_Engage.objects.filter(community_id=community, member_id=user).update(
                new_chatroom_users=json.dumps(member_instances))


def migrate_members_in_chatrooms():

    '''function to migrate the data in chatrooms'''
   # community_id = 49231

    all_chatrooms = Collabcard.objects.all()

    for data in all_chatrooms:
        set_chatroom_state_for_all_members_on_card_creation(data.community.id, data.id)

        print("card_id",data.id)
        print("community_id",data.community.id)






start_time = time.time()
###get_all_chatroom_states()
migrate_members_in_chatrooms()
end_time = time.time()

diff = end_time - start_time

print(diff)
