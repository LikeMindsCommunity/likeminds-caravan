from togther.models import (Members, collabcardState, Userinfo, Collabcard,
                            memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory, Report, Report_Tags, communityRightsSettings,
                            Community, removedMembers, userMemberRightsHistory,
                            Member_Engage, conversationEngage)
from django.contrib.auth.models import User
from utility.states import member_states
import time


def get_community_owner(community_obj):
    owner = Members.objects.filter(community_id=community_obj, is_owner=True)

    if owner.exists():
        return owner[0].member_id
    else:
        return get_community_owner_by_time_heirarchy(community_obj)


def get_community_owner_by_time_heirarchy(community_obj):
    members = Members.objects.filter(community_id=community_obj).order_by('id')
    if members.exists():
        return members[0].member_id


def get_communities_list():
    community_list = list(Members.objects.all().values_list('community_id__id', flat=True))
    return community_list


def fill_member_history():
    community_list = get_communities_list()

    communities = Community.objects.filter(pk__in=community_list)

    member_rights = memberRights.objects.all()

    for community in communities:
        print(f"filling community members - {community.id}")
        community_owner = get_community_owner(community)
        member_states_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]
        community_members = Members.objects.filter(community_id=community, state__in=member_states_list)

        for member in community_members:
            check_and_create_user_right_history(member.member_id, community, community_owner, member_rights)


def check_and_create_user_right_history(user, community, owner, member_rights):

    for right in member_rights:

        member_has_right = userMemberRights.objects.filter(user=user, community=community, right=right)
        enabled_by_cm = member_has_right.exists()

        create_member_rights_history(right, user, community,
                                     enabled_by_cm=enabled_by_cm, updated_cm=owner)


def create_member_rights_history(right, user, community, enabled_by_cm=False, updated_cm=None):
    try:
        userMemberRightsHistory(user=user, community=community, right=right,
                                enabled_by_CM=enabled_by_cm, updated_CM=updated_cm).save()
    except:
        print(f"history already exists --> {user.id} - {community.id}")



start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)

fill_member_history()

end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time - start_time
print(">>>>>> total >>>>>>>>  ", diff)


# from scripts import moderation_rights_history