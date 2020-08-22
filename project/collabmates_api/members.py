from togther.models import Members,collabcardState
from utility.states import collabcard_states, member_states, question_states, community_states, deleted_members, \
    card_types, chatroom_states, email_states

from django.db.models import Q

from .serializers import get_user_profile


def get_tagging_list_internal(community_id,chatroom_id=None):

    '''function to give tagging list of members in community'''

    member_filter = Members.objects.filter(community_id=community_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
            state=member_states.PROFILE_UNAVAILABLE)).order_by('id')

    tagging_list = []
    for member in member_filter:
        temp = {}
        user_instance = member.member_id
        temp['id'] = user_instance.id
        temp['name'] = user_instance.userinfo.name
        temp['image_url'] = user_instance.userinfo.image_link
        temp['state'] = member.state

        # member_dict = {'member': temp}

        tagging_list.append(temp)

    if chatroom_id:
        state_filter = collabcardState.objects.filter(card_id=chatroom_id, is_guest=True)

        for data in state_filter:
            temp = {}
            user_instance = data.user
            temp['id'] = user_instance.id
            temp['name'] = user_instance.userinfo.name
            temp['image_url'] = user_instance.userinfo.image_link
            temp['state'] = 0
            temp['is_guest'] = True

            # member_dict = {'member': temp}
            tagging_list.append(temp)

    return tagging_list

def get_pending_members_of_community(community_id,requested_member_id):

    '''functions to get pending members of the community'''

    pending_requests = []

    member_filter = Members.objects.filter(community_id=community_id,state=member_states.PENDING_MEMBER)

    for pending_member in member_filter:

        user_profile = get_user_profile(pending_member.member_id.id,community_id,current_user_id=requested_member_id)
        user_profile['state'] = pending_member.state

        pending_requests.append(user_profile)


    return pending_requests


