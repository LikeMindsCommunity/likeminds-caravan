from togther.models import Members,collabcardState,Userinfo
from utility.states import collabcard_states, member_states, question_states, community_states, deleted_members, \
    card_types, chatroom_states, email_states

from django.db.models import Q,Subquery
from django.db import connection
from .serializers import *
from .utility import *


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

    tagging_list = sorted(tagging_list,key=lambda i:i['name'])

    guest_list = []
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
            guest_list.append(temp)
        guest_list = sorted(guest_list,key=lambda i:i['name'])

    tagging_list = tagging_list + guest_list
    return tagging_list

def get_pending_members_of_community(community_id,requested_member_id):

    '''functions to get pending members of the community'''

    pending_requests = []

    promoter_filter = Members.objects.filter(community_id=community_id,member_id=requested_member_id,state=member_states.ADMIN)

    if not promoter_filter.exists():
        return []

    member_filter = Members.objects.filter(community_id=community_id,state=member_states.PENDING_MEMBER)

    for pending_member in member_filter:

        user_profile = MembersSerializer(pending_member,community_id,current_user_id=requested_member_id)

        pending_requests.append(user_profile)


    return pending_requests

def get_all_members(request, req_dict=None):
    '''function to get all members of the community'''

    page = request.GET.get('page', 1)

    if not req_dict:
        community_id = request.GET.get('community_id')
        collabcard_id = request.GET.get('collabcard_id', None)
    else:
        community_id = req_dict['community_id']
        collabcard_id = req_dict['collabcard_id'] if 'collabcard_id' in req_dict else None

    current_user_id = get_member_id_from_headers(request)
    is_filter = request.GET.get('is_filter', False)

    filter_list = request.GET.get('filter', None)
    community_instance = Community.objects.get(id=community_id)

    # functionality for user filteration based on options
    context = {}

    #flow for sending members of chatrooms
    if collabcard_id and is_request_web(request):
        members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id,page_no=page)
        # print(members)
        context = {'members': members}
        return context

    if collabcard_id:
        context = send_participants_of_chatroom(collabcard_id, filter_list, community_id, current_user_id, page=page)
        return context


    member_list = get_member_query_set(current_user_id, community_id,page=page)
    if filter_list:
        filter_list = json.loads(filter_list)
        member_set = get_filtered_users(filter_list, member_list)
        members = get_filtered_member_instances(member_list, current_user_id, community_id, is_filter=is_filter,
                                               member_set=member_set,page=page)
    else:
        members = get_filtered_member_instances(member_list, current_user_id, community_id,page=page)



    promoter_instance = is_member_promoter(community_instance,current_user_id)

    community = CommunitySerializer(community_instance,promoter_id=promoter_instance)

    context = {'members': members,'community':community}

    ##sending total members and pending members count
    context['total_members'] = community['members_count']
    if promoter_instance:
        context['total_pending_members'] = Members.objects.filter(community_id=community_id,state=member_states.PENDING_MEMBER).count()

    return context

def get_filtered_member_instances(member_list,current_user_id,community_id,is_filter=False,member_set=None,page=1):

    '''function to get members instances from members table'''

    members = []
    current_user = {}

    #fetching the user profile to show his name at top

    if int(page) == 1:

        current_filter = Members.objects.filter(member_id=current_user_id,community_id=community_id)

        if current_filter.exists():

            if member_set and current_user_id and int(current_user_id) in member_set:
                current_user = MembersSerializer(current_filter[0],community_id,current_user_id=current_user_id)
            elif not member_set:
                current_user = MembersSerializer(current_filter[0],community_id,current_user_id=current_user_id)




    #member_list = pagination(member_list, page, paginate_by=10)

    for member in member_list:
        member_id = member.member_id.id
        userinfo_serialized_object = MembersSerializer(member,community_id,current_user_id=current_user_id)

        if not is_filter:
            if member_id == int(current_user_id):
                pass
            else:
                members.append(userinfo_serialized_object)

        else:
            if member_id in member_set:
                if member_id == int(current_user_id):
                    pass
                else:
                    members.append(userinfo_serialized_object)

    # for making the logged in user name first
    #members = sorted(members,key= lambda i:i['name'])
    if current_user:
        members.insert(0,current_user)
    return members

def get_filtered_users(filter_list,member_list):

    '''function to get filtered users'''

    member_set = set()

    for data in member_list:
        member_set.add(data.member_id.id)

    filter_map={}
    for data in filter_list:
        key_list = []
        question_id = data['question_id']
        if question_id in filter_map:

            key_list = filter_map[question_id]
            key_list.append(data['value'])
            filter_map[question_id] = key_list
        else:
            key_list.append(data['value'])
            filter_map[question_id] = key_list


    distinct_members = {}

    for key,value in filter_map.items():

        question_id = key
        question_set = set()
        for option in value:

            question_filters = questionFilters.objects.filter(filter=option,
                                                              question=question_id)
            for instance in question_filters:
                question_set.add(instance.member.id)
        distinct_members[question_id] = question_set


    for key,value  in distinct_members.items():

       member_set = intersect_sets(member_set,value)

    return member_set

def get_members_data_for_collabcard(card_id,community_id,current_user_id,page_no=1,member_set=None):


    #card_instance = Collabcard.objects.get(id=card_id)

    state_list = [collabcard_states.COLLABCARD_STATE_FOLLOW, collabcard_states.COLLABCARD_STATE_ATTEND_FOLLOWING,
                  collabcard_states.COLLABCARD_STATE_ATTEND_UNFOLLOWING]

    collabcard_state_list = collabcardState.objects.filter(card=card_id).filter(remove=None,follow_status=True).order_by('-user_id')

    show_removed = False
    paginated_data = get_paginated_queryset_with_maxpages(collabcard_state_list,page_no,paginate_by=10)
    collabcard_state_list = paginated_data['page_list']

    if int(page_no) == paginated_data['last_page']:
        show_removed = True
    members = []

    for instance in collabcard_state_list:

        user_instance = instance.user

        if member_set and user_instance.id not in member_set:
            continue
        user_context = get_members_profile([user_instance.id],community_id,current_user_id)
        user_context = user_context[0]
        user_context['collabcard_state'] = instance.state
        user_context['is_guest'] = instance.is_guest

        #if the user is the guest in that chatroom
        if instance.is_guest:
            guest_text = get_guest_custom_text(instance)
            user_context['custom_intro_text'] = guest_text['custom_intro_text']
            user_context['custom_click_text'] = guest_text['custom_click_text']

        # if instance.remove:
        #     instance = instance.remove
        #     temp = get_removed_member_custom_text(instance)
        #     user_context['custom_intro_text'] = temp['custom_intro_text']
        #     user_context['custom_click_text'] = temp['custom_intro_text']
        #     user_context['remove_state'] = temp['remove_state']

        members.append(user_context)

    #for handling the removed members of community
    if show_removed and not member_set:
        removed_list = collabcardState.objects.filter(card=card_id).filter(follow_status=True).filter(~Q(remove=None)).order_by('-user_id')

        for instance in removed_list:
            user_instance = instance.user
            user_context = get_user_profile(user_instance.id,current_user_id)
            user_context['collabcard_state'] = instance.state
            user_context['is_guest'] = instance.is_guest

            temp = get_removed_member_custom_text(instance.remove)
            user_context['custom_intro_text'] = temp['custom_intro_text']
            user_context['custom_click_text'] = temp['custom_click_text']
            user_context['remove_state'] = temp['remove_state']
            user_context['image_url'] = temp['removed_user_image_url']

            members.append(user_context)





    return members

def intersect_sets(set1,set2):

    return set1.intersection(set2)


def get_member_query_set(current_user_id,community_id,collabcard_id = None,page=1):

    if collabcard_id:
        member_list = Members.objects.filter(community_id=community_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) | Q(
            state=member_states.PROFILE_UNAVAILABLE) | Q(state=member_states.PENDING_MEMBER)).order_by('id')
        return member_list


    state = 0
    state_filter = Members.objects.filter(member_id=current_user_id,community_id=community_id)
    if state_filter.exists():
        state= state_filter[0].state

    if state == member_states.ADMIN:
        member_list = get_paginated_member_queryset(page=page,community_id=community_id,promoter=True)

    else:
        member_list = get_paginated_member_queryset(page=page,community_id=community_id,promoter=False)

    return member_list



def send_participants_of_chatroom(chatroom_id,filter_list,community_id,current_user_id,page=1):


    community_instance = Community.objects.get(id=community_id)
    collabcard_id=chatroom_id
    member_list = get_member_query_set(current_user_id, community_id,collabcard_id)

    if filter_list:
        filter_list = json.loads(filter_list)
        member_set = get_filtered_users(filter_list, member_list)
        members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id, page_no=page,
                                                  member_set=member_set)
    else:
        members = get_members_data_for_collabcard(collabcard_id, community_id, current_user_id, page_no=page,
                                                  member_set=None)

    promoter_instance = is_member_promoter(community_instance, current_user_id)

    community = CommunitySerializer(community_instance, promoter_id=promoter_instance)

    context = {'members': members, 'community': community}

    return context


def get_paginated_member_queryset(page,community_id,promoter=False):

    '''function to get paginated  member ids'''

    cursor = connection.cursor()
    page_number = int(page)
    limit = 10
    offset = (page_number-1) * 10
    if promoter:
        sql = """SELECT togther_members.id,togther_members.member_id_id, togther_userinfo.name FROM togther_members INNER JOIN togther_userinfo ON togther_members.member_id_id = togther_userinfo.user_id_id  and togther_members.community_id_id = %s  and (togther_members.state = 1 or togther_members.state = 4 or togther_members.state = 9 or togther_members.state = 3) order by name limit %s offset %s"""%(str(community_id),str(limit),str(offset))
    else:
        sql = """SELECT togther_members.id,togther_members.member_id_id, togther_userinfo.name FROM togther_members INNER JOIN togther_userinfo ON togther_members.member_id_id = togther_userinfo.user_id_id  and togther_members.community_id_id = %s  and (togther_members.state = 1 or togther_members.state = 4 or togther_members.state = 9 or togther_members.state = 3) order by name limit %s offset %s"""%(str(community_id),str(limit),str(offset))

    cursor.execute(sql)

    res = cursor.fetchall()

    member_ids=[]

    for id in res:
        instance =Members.objects.get(id=id[0])
        member_ids.append(instance)

    return member_ids
