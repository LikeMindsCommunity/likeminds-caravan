from togther.models import Members,collabcardState
from utility.states import collabcard_states, member_states, question_states, community_states, deleted_members, \
    card_types, chatroom_states, email_states

from django.db.models import Q



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
