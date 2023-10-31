from django.db import connection

from utility.request_utilities import RequestUtilities
from .serializers import *
from .utility import *
from .user_moderation_rights import check_admin_approve_right
from .rest_api import CommunitySerializerV1
from .raw_queries import (get_users_sdk_meta_dict)
from collabmates_api.sdk.models import (SdkClient)
from utility.response_utilities import ResponseUtilities
from utility.states import (question_answers_versions)


def get_tagging_list_internal(community_id, chatroom_id=None, current_member_id=None):
    '''function to give tagging list of members in community'''

    if chatroom_id and not community_id:

        card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if not card_instance:
            return []

        community_id = card_instance.community_id

    elif chatroom_id and community_id:

        card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if not card_instance:
            return []

    member_filter = Members.objects.filter(community_id=community_id).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) |
        Q(state=member_states.PROFILE_UNAVAILABLE)).order_by('id')

    tagging_list = []

    blocked_users_list = list(blockedMembers.objects.filter(community=community_id,
                                                            blocked_by=current_member_id).values_list(
        "blocked_member__id", flat=True))
    for member in member_filter:

        user_instance = member.member_id
        if int(user_instance.id) in blocked_users_list:
            continue

        temp = {'id': user_instance.id}

        if str(temp['id']) == current_member_id:
            continue

        temp['name'] = user_instance.userinfo.name
        temp['image_url'] = member.image_url if member.image_url else user_instance.userinfo.image_link
        temp['state'] = member.state

        # member_dict = {'member': temp}

        tagging_list.append(temp)

    tagging_list = sorted(tagging_list, key=lambda i: i['name'])

    guest_list = []

    if chatroom_id:
        state_filter = collabcardState.objects.filter(card_id=chatroom_id, is_guest=True, remove=None)

        for data in state_filter:
            temp = {}
            user_instance = data.user
            temp['id'] = user_instance.id

            if str(temp['id']) == current_member_id:
                continue

            temp['name'] = user_instance.userinfo.name
            temp['image_url'] = user_instance.userinfo.image_link
            temp['state'] = 0
            temp['is_guest'] = True

            # member_dict = {'member': temp}
            guest_list.append(temp)
        guest_list = sorted(guest_list, key=lambda i: i['name'])

    tagging_list = tagging_list + guest_list
    return tagging_list


def get_tagging_list_internal_v1(community_id, chatroom_id=None, current_member_id=None):
    '''function to give tagging list of members in community'''
    card_instance = None
    # check and fetch for community id
    if chatroom_id:
        card_instance = Collabcard.get_chatroom_or_raise_exception(chatroom_id)
        community = card_instance.community
    else:
        community = Community.get_community_or_raise_exception(community_id)

    blocked_users_list = get_blocked_members_list(community, current_member_id)

    if chatroom_id:
        if card_instance.is_secret:
            response = get_secret_chatroom_tagging_list(chatroom_instance=card_instance, community_instance=community,
                                                        blocked_users_list=blocked_users_list,
                                                        current_user_id=current_member_id)
        else:
            response = get_chatroom_participants_for_tagging(chatroom_id, blocked_users_list, current_member_id)

    else:
        response = get_community_members_for_tagging(community, blocked_users_list, current_member_id)

    return response


def get_blocked_members_list(community, user_id):
    blocked_users_list = list(blockedMembers.objects.filter(community=community,
                                                            blocked_by=user_id).values_list(
        "blocked_member__id", flat=True))
    return blocked_users_list


def get_secret_chatroom_tagging_list(chatroom_instance, community_instance, blocked_users_list, current_user_id):
    participants_list = []
    secret_room_participants = json.loads(chatroom_instance.secret_chatroom_participants)

    secret_room_participants_list = Members.objects \
        .filter(community_id=community_instance,
                member_id__id__in=secret_room_participants,
                member_id__userinfo__is_guest=False) \
        .select_related('member_id__userinfo')

    for participant in secret_room_participants_list:

        user_instance = participant.member_id
        user_id = user_instance.id

        if int(user_id) in blocked_users_list:
            continue

        if str(user_id) == current_user_id:
            continue

        member_dict = {'id': user_id,
                       'name': user_instance.userinfo.name,
                       'image_url': user_instance.userinfo.image_link,
                       'is_guest': user_instance.userinfo.is_guest,
                       }

        if participant.image_url:
            member_dict['image_url'] = participant.image_url

        if member_dict['image_url'] is None:
            member_dict['image_url'] = ''

        participants_list.append(member_dict)

    participants_list = sorted(participants_list, key=lambda i: i['name'])

    response = {
        'participants': participants_list
    }

    return response


def get_chatroom_participants_for_tagging(chatroom_id, blocked_users_list, current_member_id):
    participants_list = []
    state_filter = collabcardState.objects.filter(card_id=chatroom_id, remove=None,
                                                  user__userinfo__is_guest=False).select_related('user')

    for data in state_filter:

        user_instance = data.user
        user_id = user_instance.id
        if int(user_id) in blocked_users_list:
            continue

        if str(user_id) == current_member_id:
            continue

        member_dict = {'id': user_id,
                       'name': user_instance.userinfo.name,
                       'image_url': user_instance.userinfo.image_link,
                       }

        if data.follow_status:
            participants_dict = member_dict.copy()
            additional_dict = {'follow_status': data.follow_status,
                               'attending_status': data.attending_status,
                               'is_guest': data.is_guest
                               }

            participants_dict.update(**additional_dict)
            participants_list.append(participants_dict)

    participants_list = sorted(participants_list, key=lambda i: i['name'])

    response = {
        'participants': participants_list
    }

    return response


def get_community_members_for_tagging(community, blocked_users_list, current_member_id):
    member_filter = Members.objects.filter(community_id=community, member_id__userinfo__is_guest=False).filter(
        Q(state=member_states.ADMIN) | Q(state=member_states.MEMBER) |
        Q(state=member_states.PROFILE_UNAVAILABLE)).select_related('member_id')

    tagging_list = []

    for member in member_filter:

        user_instance = member.member_id
        user_id = user_instance.id
        if int(user_id) in blocked_users_list:
            continue

        if int(user_id) == int(current_member_id):
            continue

        temp = {
            'id': user_id,
            'name': user_instance.userinfo.name,
            'image_url': member.image_url if member.image_url else user_instance.userinfo.image_link,
            'is_guest': user_instance.userinfo.is_guest,
            'state': member.state
        }

        tagging_list.append(temp)

    tagging_list = sorted(tagging_list, key=lambda i: i['name'])

    response = {
        'members': tagging_list
    }
    return response


def get_tagging_list_internal_web(chatroom_id, current_user_id=None):
    '''function to return tagging list of members in chatroom'''
    if not chatroom_id:
        return []

    tagging_list = []
    try:
        card_instance = Collabcard.objects.get(id=chatroom_id)
    except Exception as e:
        return []

    state_filter = collabcardState.objects.filter(card=card_instance, follow_status=True, remove=None)
    user_set = set()
    for data in state_filter:
        user_instance = data.user
        user_id = user_instance.id
        if current_user_id and int(current_user_id) == user_id:
            continue
        temp = get_user_profile(user_instance, send_profile=False)
        temp['is_participant'] = True
        tagging_list.append(temp)
        user_set.add(user_id)

    community = card_instance.community
    member_filter = Members.objects.filter(community_id=community)
    for member in member_filter:
        user_instance = member.member_id
        user_id = user_instance.id

        if current_user_id and int(current_user_id) == user_id:
            continue

        if user_id not in user_set:
            temp = get_user_profile(user_instance, send_profile=False)
            temp['is_participant'] = False
            tagging_list.append(temp)
            user_set.add(user_id)

    return tagging_list


def get_pending_members_of_community(community_id, requested_member_id):
    """ functions to get pending members of the community """

    pending_requests = []

    promoter_filter = Members.objects.filter(community_id=community_id,
                                             member_id=requested_member_id, state=member_states.ADMIN)

    if not promoter_filter.exists():
        return []

    member_filter = Members.objects.filter(community_id=community_id, state=member_states.PENDING_MEMBER)

    user_ids = []

    for pending_member in member_filter:
        user_profile = MembersSerializer(pending_member, community_id, current_user_id=requested_member_id,
                                         send_profile=pending_member.state == member_states.PENDING_MEMBER)
        
        user_ids.append(user_profile['id'])

        pending_requests.append(user_profile)

    # Add sdk_client_info to all pending member objects
    sdk_meta_dict = get_users_sdk_meta_dict(user_ids, only_sdk_client_info=True)

    for pending_request in pending_requests:
        pending_request['sdk_client_info'] = sdk_meta_dict.get(pending_request['id'])

    return pending_requests


def get_secret_chatroom_participants(chatroom_instance, current_user_id, page=1, filter_list=None):
    member_profile_list = []
    current_user_id = NumberUtilities.get_integer_from_string(current_user_id)

    participants_list = json.loads(chatroom_instance.secret_chatroom_participants)

    if filter_list:
        try:
            filter_list = json.loads(filter_list)
        except:
            response = {
                'success': False,
                'error_message': 'Json decode error - error at filter list'
            }
            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        participants_list = list(get_filtered_users(filter_list, participants_list))

    # removing and adding current user id, so as to show his profile on top
    # following this procedure in order to ensure current user id is present at the first page and not duplicated
    # and also to reduce a query to fetch current user profile separately
    if current_user_id in participants_list:
        participants_list.remove(current_user_id)
        participants_list.insert(0, current_user_id)

    paginated_participants_list = paginate_list(participants_list, page, paginate_by=10)

    community_instance = chatroom_instance.community
    community_id = community_instance.id

    chatroom_participants = Members.objects \
        .filter(community_id=community_instance,
                member_id__id__in=paginated_participants_list) \
        .prefetch_related('member_id')

    current_user_profile = None

    for participant in chatroom_participants:

        community_profile = MembersSerializer(participant, community_id, current_user_id=current_user_id,
                                              send_profile=False)

        community_profile['community_id'] = community_id

        if participant.member_id_id == current_user_id:
            current_user_profile = community_profile
            continue

        member_profile_list.append(community_profile)

    can_edit_participant = current_user_id == chatroom_instance.user_id

    if current_user_profile is not None:
        member_profile_list.insert(0, current_user_profile)

    context = {'members': member_profile_list,
               'can_edit_participant': can_edit_participant,
               'total_members': len(participants_list)}

    return context


def get_all_members(request, req_dict=None):
    """function to get all members of the community"""

    page = request.GET.get('page', 1)

    if not req_dict:
        community_id = request.GET.get('community_id')
        collabcard_id = request.GET.get('collabcard_id', None)
    else:
        community_id = req_dict['community_id']
        collabcard_id = req_dict['collabcard_id'] if 'collabcard_id' in req_dict else None

    current_user_id = get_member_id_from_headers(request)
    platform_code = RequestUtilities.get_platform_code(request)
    version_code = RequestUtilities.get_version_code_from_headers(request)

    try:
        current_user_instance = User.objects.get(pk=current_user_id)
    except Exception as e:
        current_user_instance = None
        print(e.args)

    is_filter = request.GET.get('is_filter', False)

    filter_list = request.GET.get('filter', None)
    community_instance = Community.get_community_or_raise_exception(community_id)

    # functionality for user filteration based on options
    context = {}

    # flow for sending members of chat rooms
    if collabcard_id:
        chatroom_instance = Collabcard.objects.get(pk=collabcard_id)

        if is_request_web(request):
            members = get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page_no=page)
            context = {'members': members}
            return context

        context = send_participants_of_chatroom(chatroom_instance, filter_list, community_id, current_user_id,
                                                page=page)
        return context

    promoter_instance = None
    is_owner = False
    is_promoter = False
    member_instance = Members.objects.filter(community_id=community_instance, member_id=current_user_id)
    if member_instance.exists():
        member_instance = member_instance[0]
        is_promoter = member_instance.state == member_states.ADMIN
        if is_promoter:
            promoter_instance = current_user_instance
        is_owner = member_instance.is_owner
    else:
        member_instance = None

    community = CommunitySerializer(community_instance, promoter_id=promoter_instance, is_owner=is_owner,
                                    current_user_id=current_user_id, current_user_instance=current_user_instance,
                                    platform_code=platform_code, version_code=version_code)

    if filter_list:
        member_list = get_member_query_set(current_user_id, community_id, send_all=True)
        filter_list = json.loads(filter_list)
        member_set = get_filtered_users(filter_list, member_list)
        total_filtered_members = len(member_set)
        members = get_member_instances_with_filter(member_set, current_user_id, community_id, page=page,
                                                   member_instance=member_instance)

    else:
        member_list = get_member_query_set(current_user_id, community_id, page=page)
        members = get_member_instances_without_filter(member_list, current_user_id, community_id, page=page)
        total_filtered_members = community['members_count']

    context = {'members': members, 'community': community}

    # sending total members and pending members count
    context['total_members'] = community['members_count']
    context['total_filtered_members'] = total_filtered_members

    if promoter_instance:
        user_engage = Member_Engage.objects.filter(community_id=community_instance,
                                                   member_id=promoter_instance)
        if user_engage.exists():
            context['total_pending_members'] = user_engage[0].pending_members

    return context


def add_expired_members_metadata(members, community_instance):
    from .member_community.member_community_impl import MemberCommunityImpl

    if not members:
        return []

    user_list = [data['id'] for data in members]
    membership_expired_dict = MemberCommunityImpl.fetch_members_for_membership_expired(user_list, community_instance)
    processed_member_list = []

    for data in members:
        member_dict = {}
        member_id = data['id']

        if membership_expired_dict.get(member_id):
            member_dict.update(data)
            membership_expired_instance = membership_expired_dict[member_id]
            user_name = member_dict['name']
            member_dict['custom_intro_text'] = CUSTOM_INTRO_TEXT_MEMBERSHIP_EXPIRED
            member_dict['custom_click_text'] = CUSTOM_CLICK_TEXT_MEMBERSHIP_EXPIRED % \
                                               (user_name,
                                                TimeUtilities.convert_epoch_time_in_date(
                                                    membership_expired_instance.created_at))

        else:
            member_dict.update(data)

        processed_member_list.append(member_dict)

    return processed_member_list


def get_all_members_version_1(request, req_dict=None):
    """function to get all members of the community"""

    page = RequestUtilities.get_page_number(request)

    community_id = request.GET.get('community_id')
    chatroom_id = request.GET.get('chatroom_id', None)
    current_user_id = get_member_id_from_headers(request)
    current_user_instance = ModelUtilities.get_model_instance_or_none(User, current_user_id)
    filter_list = request.GET.get('filter', None)
    conversation_id = request.GET.get('conversation_id')
    user_type = request.GET.get('type', None)
    member_state = request.GET.get('member_state', None)
    member_state = NumberUtilities.get_integer_from_string(member_state, -1)
    question_answers_version = request.GET.get('question_answers_version', '')
    included_member_states = StringUtilities.get_list_from_string(request.GET.get('included_member_states', ''))

    question_answers_v2 = question_answers_version.lower() == question_answers_versions.V2

    api_key = RequestUtilities.get_api_key_from_headers(request)

    if not current_user_instance:
        return ResponseUtilities.get_impl_error_context("Invalid x-member-id",
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

    if not community_instance:
        return ResponseUtilities.get_impl_error_context("Invalid API key/community ID",
                                                        status_code=status_codes.HTTP_400_BAD_REQUEST)

    community_id = community_instance.id

    if conversation_id:
        return send_participants_of_conversation(conversation_id, filter_list, current_user_id,
                                                 page=NumberUtilities.get_integer_from_string(page))

    if chatroom_id:
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_impl_error_context(f'chatroom with id {chatroom_id} does not exists',
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        if str(user_type) == ATTENDEES_FILTER_NAME:
            # Filter only attendees of this chatroom
            total_participants_list = ModelUtilities.get_model_filter(collabcardState,
                                                                      {"card": chatroom_instance,
                                                                       "attending_status": True})

            context = collabcard_members_for_given_list(chatroom_instance, community_id, current_user_id, page,
                                                        total_participants_list, question_answers_v2=question_answers_v2)

            context['total_members'] = total_participants_list.count()
            context['success'] = True

            return context

        elif str(user_type) == CO_HOSTS_FILTER_NAME:

            # Filter only co-hosts of this chatroom
            if chatroom_instance.co_hosts:
                co_hosts_ids_list = json.loads(chatroom_instance.co_hosts)

                total_participants_list = ModelUtilities.get_model_filter(collabcardState,
                                                                          {"card": chatroom_instance,
                                                                           "user_id__in": co_hosts_ids_list})

                total_count = total_participants_list.count()

                context = collabcard_members_for_given_list(chatroom_instance, community_id, current_user_id, page,
                                                            total_participants_list, question_answers_v2=question_answers_v2)

            else:
                total_count = 0
                context = {
                    "members": [],
                    "community": CommunitySerializerV1(chatroom_instance.community,
                                                       context={"current_user_id": current_user_id},
                                                       many=False).data
                }

            context['total_members'] = total_count
            context['success'] = True

            return context

        total_participants_list = collabcardState.objects.filter(card=chatroom_instance,
                                                                 follow_status=True,
                                                                 is_tagged=False,
                                                                 remove=None)

        if chatroom_instance.type == card_types.CARD_EVENT:
            total_participants_list = total_participants_list.filter(attending_status=True)

        total_participants = total_participants_list.count()

        if chatroom_instance.is_secret:
            context = get_secret_chatroom_participants(chatroom_instance,
                                                       current_user_id, page, filter_list=filter_list)
            context['success'] = True

            return context

        if is_request_web(request):
            context = collabcard_members(chatroom_instance, community_id, current_user_id, page, 
                                         question_answers_v2=question_answers_v2)
            context['total_members'] = total_participants
            context['success'] = True

            return context

        context = chatroom_participants(chatroom_instance, filter_list, community_id, current_user_id, page,
                                        question_answers_v2=question_answers_v2)
        context['total_members'] = total_participants
        context['success'] = True

        return context

    promoter_instance = None
    community_instance = Community.get_community_or_raise_exception(community_id)

    member_instance = Members.get_member_instance_or_none(community_instance, current_user_instance)

    if member_instance and member_instance.state == member_states.ADMIN:
        promoter_instance = current_user_instance

    community = CommunitySerializerV1(community_instance, context={"current_user_id": current_user_id},
                                      many=False).data

    if member_state <= 0:
        member_state = None

    if filter_list:

        filter_context = filtered_member_list(current_user_id, community_id, filter_list, page, member_instance,
                                              member_state=member_state, included_member_states=included_member_states)
        members = filter_context['members']
        total_filtered_members = filter_context['total_filtered_members']

    else:

        unfiltered_context = unfiltered_member_list(current_user_id, community_id, page, member_state=member_state,
                                                    sdk_client_info_flag=True, question_answers_v2=question_answers_v2,
                                                    included_member_states=included_member_states)
        members = unfiltered_context['members']
        total_filtered_members = community['members_count']

    members = add_expired_members_metadata(members, community_instance)

    context = {'success': True, 'members': members, 'community': community,
               'total_members': community['members_count'], 'total_filtered_members': total_filtered_members}

    if NumberUtilities.get_integer_from_string(page) == 1:
        context['total_only_members'] = Members.objects \
            .filter(community_id=community_instance, state=member_states.MEMBER, member_id__userinfo__is_guest=False) \
            .count()

    if promoter_instance:
        pending_members = pending_members_count_in_community(community_instance, current_user_instance)

        if pending_members is not None:
            context['total_pending_members'] = pending_members

    return context


def pending_members_count_in_community(community_instance, user_instance):
    user_engage = Member_Engage.objects.filter(community_id=community_instance,
                                               member_id=user_instance)
    if user_engage.exists():
        return user_engage[0].pending_members


def collabcard_members(chatroom_instance, community_id, current_user_id, page, question_answers_v2: bool=False):
    members = get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page_no=page,
                                              question_answers_v2=question_answers_v2)
    context = {'members': members}

    return context


def collabcard_members_for_given_list(chatroom_instance, community_id, current_user_id, page,
                                      total_participants_list=[], question_answers_v2: bool=False):
    members_serialized_object = get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page,
                                                                collabcard_state_list=total_participants_list, 
                                                                question_answers_v2=question_answers_v2)

    community_instance = CommunitySerializerV1(chatroom_instance.community,
                                               context={"current_user_id": current_user_id},
                                               many=False).data

    return {"members": members_serialized_object, "community": community_instance}


def chatroom_participants(chatroom_instance, filter_list, community_id, current_user_id, page, question_answers_v2: bool=False):
    context = send_participants_of_chatroom(chatroom_instance, filter_list, community_id, current_user_id, page=page,
                                            question_answers_v2=question_answers_v2) 

    return context


def filtered_member_list(current_user_id, community_id, filter_list, page, member_instance, member_state=None,
                         included_member_states=[]):
    member_list = get_member_query_set(current_user_id, community_id, send_all=True, member_state=member_state,
                                       included_member_states=included_member_states)
    member_list = member_list.filter(member_id__userinfo__is_guest=False)
    filter_list = json.loads(filter_list)
    member_set = get_filtered_users(filter_list, member_list)
    total_filtered_members = len(member_set)
    members = get_member_instances_with_filter(member_set, current_user_id, community_id, page=page,
                                               member_instance=member_instance)
    filter_context = {
        'members': members,
        'total_filtered_members': total_filtered_members
    }

    return filter_context


def unfiltered_member_list(current_user_id, community_id, page, member_state=None, sdk_client_info_flag:bool=False, 
                           question_answers_v2: bool=False, included_member_states: list = []):
    member_list = get_member_query_set(current_user_id, community_id, page=page, remove_guest_user=True,
                                       member_state=member_state, included_member_states=included_member_states)
        
    members = get_member_instances_without_filter(member_list, current_user_id, community_id, page=page, 
                                                  member_state=member_state, sdk_client_info_flag=sdk_client_info_flag,
                                                  question_answers_v2=question_answers_v2)

    unfilter_context = {
        'members': members
    }

    return unfilter_context


def get_community_managers(community_instance):
    '''function to get count of community managers'''

    manager_filter = Members.objects.filter(community_id=community_instance,
                                            state=member_states.ADMIN).order_by('created_at')
    temp = {}
    manager_name = ""
    for manager in manager_filter:
        manager_name = manager.member_id.userinfo.name
        break
    temp['manager_name'] = manager_name
    temp['count'] = manager_filter.count()

    return temp


def get_member_instances_without_filter(member_list, current_user_id, community_id, page=1, member_state: int = None, 
                                        sdk_client_info_flag:bool=False, question_answers_v2: bool = False):
    '''function to get members instances from members table'''

    members = []
    member_ids = []
    current_user = {}
    is_owner = False
    user_admin_rights = None
    is_promoter = False

    # fetching the user profile to show his name at top

    current_filter = Members.objects.filter(member_id=current_user_id, community_id=community_id)

    if current_filter:
        current_user_filter = current_filter[0]
        is_owner = current_user_filter.is_owner
        is_promoter = current_user_filter.state == member_states.ADMIN

    if int(page) == 1:

        if current_filter:
            current_user = MembersSerializer(current_user_filter, community_id, current_user_id=current_user_id,
                                             send_profile=(not question_answers_v2),
                                             all_members_api=True, is_promoter=is_promoter,
                                             is_owner=is_owner)

    if is_owner or is_promoter:
        user_admin_rights = check_all_manager_rights(current_user_id, community_id)

    for member in member_list:
        member_id = member.member_id_id
        member_ids.append(member_id)

        if current_user_id and member_id == int(current_user_id):
            continue

        userinfo_serialized_object = MembersSerializer(member, community_id, current_user_id=current_user_id,
                                                       send_profile=(not question_answers_v2),
                                                       all_members_api=True, is_promoter=is_promoter,
                                                       is_owner=is_owner, user_admin_rights=user_admin_rights)
        members.append(userinfo_serialized_object)

    # If first page and current user'state matches member_state filter, then add him to the top of the list 
    if current_user and (not member_state or current_user['state'] == member_state):        
        members.insert(0, current_user)
    
    # If sdk_client_info_flag is True, then add sdk_client_info to members object
    if sdk_client_info_flag:
        sdk_client_info_meta = get_users_sdk_meta_dict(member_ids, only_sdk_client_info=True)

        for member in members:
            member['sdk_client_info'] = sdk_client_info_meta.get(member['id'])

    # If question_answers_v2 is True, then add latest serialised question_answers to members object
    if question_answers_v2:

        from collabmates_api.community.community_impl import CommunityHelper

        question_answers_dict = CommunityHelper.get_members_filled_community_answers_data(community_id, members)

        for member in members:

            if member.get('id') in question_answers_dict:
                member['question_answers'] = question_answers_dict.get(member.get('id'))
                
            else:
                member['question_answers'] = None


    return members


def get_member_instances_with_filter(member_set, current_user_id, community_id, page=1, member_instance=None):
    # sending first user if he is the part of list
    current_user = None
    members = []

    is_owner = False
    user_admin_rights = None
    is_promoter = False

    if member_instance is not None:
        is_owner = member_instance.is_owner
        is_promoter = member_instance.state == member_states.ADMIN

    if int(page) == 1:

        if member_instance is not None:
            current_user_filter = member_instance

            if member_set and current_user_id and int(current_user_id) in member_set:
                current_user = MembersSerializer(current_user_filter, community_id, current_user_id=current_user_id,
                                                 send_profile=True,
                                                 all_members_api=True, is_promoter=is_promoter,
                                                 is_owner=is_owner)

        else:
            current_filter = Members.objects.filter(member_id=current_user_id, community_id=community_id)
            if current_filter.exists():

                current_user_filter = current_filter[0]
                is_owner = current_user_filter.is_owner
                is_promoter = current_user_filter.state == member_states.ADMIN

                if member_set and current_user_id and int(current_user_id) in member_set:
                    current_user = MembersSerializer(current_user_filter, community_id, current_user_id=current_user_id,
                                                     send_profile=True,
                                                     all_members_api=True, is_promoter=is_promoter,
                                                     is_owner=is_owner)

    # logic for pagination of members for filters
    if current_user_id and int(current_user_id) in member_set:
        member_set.remove(int(current_user_id))
    member_ids = list(member_set)
    member_ids = paginate_list(member_ids, page, paginate_by=10)

    if is_owner or is_promoter:
        user_admin_rights = check_all_manager_rights(current_user_id, community_id)

    member_instances_list = get_members_profile(list(member_ids), community_id, current_user_id=current_user_id,
                                                send_profile=True, all_members_api=True, is_promoter=is_promoter,
                                                is_owner=is_owner, user_admin_rights=user_admin_rights)

    if current_user:
        members.insert(0, current_user)

    members = members + member_instances_list

    return members


def get_filtered_users(filter_list, member_list):
    '''function to get filtered users'''

    if not isinstance(member_list, list):
        member_set = set(data.member_id_id for data in member_list)
    else:
        member_set = set(member_list)

    filter_map = dict()
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

    for key, value in filter_map.items():
        question_set = set(questionFilters.objects
                           .filter(filter__in=value, question=key)
                           .values_list('member_id', flat=True))

        distinct_members[key] = question_set

    for key, value in distinct_members.items():
        member_set = intersect_sets(member_set, value)

    return member_set


def get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page_no=1, member_set=None,
                                    collabcard_state_list=[], question_answers_v2: bool=False):
    if not collabcard_state_list:
        collabcard_state_list = collabcardState.objects \
            .filter(card=chatroom_instance,
                    remove=None,
                    follow_status=True,
                    is_tagged=False) \
            .select_related('user') \
            .order_by('-user_id')

        if chatroom_instance.type == card_types.CARD_EVENT:
            collabcard_state_list = collabcard_state_list.filter(attending_status=True)

    show_removed = False
    paginated_data = get_paginated_queryset_with_maxpages(collabcard_state_list, page_no, paginate_by=10)
    collabcard_state_list = paginated_data['page_list']

    if int(page_no) == paginated_data['last_page']:
        show_removed = True

    members = []

    for instance in collabcard_state_list:

        user_instance = instance.user

        if member_set and user_instance.id not in member_set:
            continue

        user_context = get_members_profile([user_instance.id], community_id, current_user_id, 
                                           send_profile=(not question_answers_v2))
        user_context = user_context[0]
        user_context['collabcard_state'] = instance.state
        user_context['attending_status'] = instance.attending_status
        user_context['is_guest'] = instance.is_guest
        user_context['attended'] = instance.attended

        # if the user is the guest in that chatroom
        if instance.is_guest and instance.source:
            guest_text = get_guest_custom_text(instance)
            user_context['custom_intro_text'] = guest_text['custom_intro_text']
            user_context['custom_click_text'] = guest_text['custom_click_text']

        if instance.remove:
            removed_user_text = get_removed_member_custom_text(instance.remove)
            user_context['custom_intro_text'] = removed_user_text['custom_intro_text']
            user_context['custom_click_text'] = removed_user_text['custom_click_text']

        members.append(user_context)

    # if question answers v2 is True, then add latest serialised question_answers to members object
    if question_answers_v2:
            
            from collabmates_api.community.community_impl import CommunityHelper
    
            question_answers_dict = CommunityHelper.get_members_filled_community_answers_data(community_id, members)
    
            for member in members:
    
                if member.get('id') in question_answers_dict:
                    member['question_answers'] = question_answers_dict.get(member.get('id'))
                    
                else:
                    member['question_answers'] = None

    return members


def intersect_sets(set1, set2):
    return set1.intersection(set2)


def get_member_query_set(current_user_id, community_id, send_all=False, page=1, remove_guest_user=False,
                         member_state=None, included_member_states=[]):

    if not included_member_states:
        included_member_states = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE,
                                  member_states.PENDING_MEMBER]

    if send_all:

        if member_state:
            included_member_states = [member_state]

        member_list = Members.objects.filter(community_id=community_id, state__in=included_member_states).order_by('id')
        return member_list

    state = 0
    state_filter = Members.objects.filter(member_id=current_user_id, community_id=community_id)

    if state_filter.exists():
        state = state_filter[0].state

    is_promoter = state == member_states.ADMIN

    if is_promoter:
        is_promoter = check_admin_approve_right(community=community_id, user=current_user_id)

    if not is_promoter:
        included_member_states = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]

    if member_state:
        included_member_states = [member_state]

    member_list = get_paginated_member_queryset(page=page, community_id=community_id,
                                                remove_guest_user=remove_guest_user,
                                                included_member_states=included_member_states)

    return member_list


def send_participants_of_chatroom(chatroom_instance, filter_list, community_id, current_user_id, page=1, 
                                  question_answers_v2: bool=False):
    member_list = get_member_query_set(current_user_id, community_id, send_all=True)

    if filter_list:
        filter_list = json.loads(filter_list)
        member_set = get_filtered_users(filter_list, member_list)
        members = get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page_no=page,
                                                  member_set=member_set, question_answers_v2=question_answers_v2)
    else:
        members = get_members_data_for_collabcard(chatroom_instance, community_id, current_user_id, page_no=page,
                                                  member_set=None, question_answers_v2=question_answers_v2)

    community_instance = chatroom_instance.community

    community = CommunitySerializerV1(community_instance, context={"current_user_id": current_user_id}, many=False).data

    context = {
        'members': members,
        'community': community,
    }

    return context


def get_tuple_from_array(array):
    if len(array) == 1:
        tupp = "(" + str(array[0]) + ")"

    else:
        tupp = tuple(array)

    return tupp


def get_paginated_member_queryset(page, community_id, remove_guest_user=False, included_member_states=None):
    '''function to get paginated  member ids'''

    cursor = connection.cursor()
    page_number = int(page)
    limit = 10
    offset = (page_number - 1) * 10

    guest_user_query = ""

    if remove_guest_user:
        guest_user_query = "AND togther_userinfo.is_guest = false"

    included_member_state_query = ""

    if included_member_states and isinstance(included_member_states, list):
        included_member_state_query = " AND togther_members.state IN {}".format(get_tuple_from_array(
            included_member_states))

    sql = """
            SELECT   togther_members.id,
                     togther_members.member_id_id,
                     togther_userinfo.name
            FROM togther_members
            INNER JOIN togther_userinfo
                ON togther_members.member_id_id = togther_userinfo.user_id_id
                    AND togther_members.community_id_id = %s %s %s
            ORDER BY togther_members.created_at DESC limit %s offset %s
    """ % (str(community_id), guest_user_query, included_member_state_query, str(limit), str(offset))

    cursor.execute(sql)
    res = cursor.fetchall()

    member_id_list = [obj[0] for obj in res]

    member_ids = Members.objects.filter(pk__in=member_id_list).order_by('-created_at')

    return member_ids


def send_participants_of_conversation(conversation_id, filter_list, current_user_id, page=1):
    conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)
    context = {'members': []}

    if not conversation_instance:
        return context

    community_instance = conversation_instance.community
    user_list = list(ModelUtilities.get_model_filter(conversationEventMembers,
                                                     {'conversation': conversation_instance,
                                                      'attending_status': True}).values_list('user', flat=True))
    member_list = ModelUtilities.get_model_filter(Members,
                                                  {'community_id': community_instance,
                                                   'member_id__in': user_list})

    community_data = CommunitySerializerV1(community_instance, context={"current_user_id": current_user_id},
                                           many=False).data
    if filter_list:
        filter_list = json.loads(filter_list)
        member_set = get_filtered_users(filter_list, member_list)
        total_filtered_members = len(member_set)
        member_instance = ModelUtilities.get_model_instance_or_none(User, current_user_id)

        if not member_instance:
            return context

        members = get_member_instances_with_filter(member_set, current_user_id, community_instance.id, page=page,
                                                   member_instance=member_instance)
        context = {
            'members': members,
            'total_filtered_members': total_filtered_members,
            'total_members': len(user_list),
            'community': community_data

        }

    else:
        total_members = len(user_list)
        member_list = ModelUtilities.paginate_queryset(member_list, page, paginate_by=10)
        members = get_member_instances_without_filter(member_list, current_user_id, community_instance.id,
                                                      page=page)
        context = {
            'members': members,
            'total_members': total_members,
            'total_filtered_members': total_members,
            'community': community_data
        }

    return context
