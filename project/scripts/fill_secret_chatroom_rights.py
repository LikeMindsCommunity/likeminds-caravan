from togther.models import (memberRights, Members, Member_Engage, conversationEngage,
                           userMemberRights)
import time
import json

create_secret_rooms = {'id': 7, 'sub_title': None, 'title': "Create secret chat rooms", "state": 6}


def fill_member_rights(user, community, rights_list, is_admin=False):

    for right in rights_list:

        if not is_admin and right.state in [4, 6]:
            continue
        try:
            userMemberRights(user=user, community=community, right=right).save()
        except:
            print(">>>> member  --  ", user.id, community.id, right.id)

    state_list = [0, 1, 2, 3, 4, 5, 6]

    if not is_admin:
        state_list.remove(4)
        state_list.remove(6)

    rights_list = json.dumps(state_list)
    Member_Engage.objects.filter(member_id=user, community_id=community).update(rights_list=rights_list)
    conversationEngage.objects.filter(user=user, community=community).update(rights_list=rights_list)


def fill_secret_chatroom_right_for_admins():

    userMemberRights.objects.filter(right__state=create_secret_rooms["state"]).delete()

    member_rights = memberRights.objects.filter(state=create_secret_rooms["state"])

    members = Members.objects.select_related('member_id', 'community_id').filter(state=1)

    for member in members:
        fill_member_rights(member.member_id, member.community_id, member_rights, is_admin=True)


def create_secret_chatroom_right_records():
    print("\n>>>>>>>>>    creating new member rights")

    memberRights.objects.filter(state=create_secret_rooms["state"]).delete()

    memberRights(pk=create_secret_rooms["id"],
                 title=create_secret_rooms["title"],
                 sub_title=create_secret_rooms["sub_title"],
                 state=create_secret_rooms["state"]).save()


start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)

create_secret_chatroom_right_records()
fill_secret_chatroom_right_for_admins()

end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time - start_time
print(">>>>>> total >>>>>>>>  ", diff)


