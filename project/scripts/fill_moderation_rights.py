from togther.models import (adminRights, memberRights, Members,
                            Community, userAdminRights, userMemberRights)
from django.contrib.auth.models import User
from django.db.models import Q

delete_room = {'id': 1, 'title': 'Delete chat rooms/messages', 'sub_title': None, "state": 0}

edit_permission = {'id': 2, 'title': 'Edit member permissions', 'sub_title': None, "state": 1}

invite = {'id': 3, 'title': 'Approve/remove members', 'sub_title': None, "state": 2}

edit_community = {'id': 4, 'title': "Edit community details", 'sub_title': None, "state": 3}

view_contact = {'id': 5, 'title': 'View member contact info', 'sub_title': None, "state": 4}

add_manager = {'id': 6, 'title': "Add community managers", 'sub_title': None, "state": 5}

manager_rights_list = [delete_room, edit_permission, invite, edit_community, view_contact, add_manager]

create_room = {'id': 1, 'title': "Create chat rooms", 'sub_title': None, "state": 0}

create_poll = {'id': 2, 'title': "Create polls", 'sub_title': None, "state": 1}

create_event = {'id': 3, 'title': "Create events", 'sub_title': None, "state": 2}

respond_in_rooms = {'id': 4, 'title': "Respond in chat rooms", 'sub_title': None, "state": 3}

invite_private = {'id': 5, 'title': "Invite members via private link",
                  'sub_title': "Private links remain valid for 24 hours and. the user joining via them a re auto verified"
                  , "state": 4
                  }

member_rights_list = [create_room, create_poll, create_event, respond_in_rooms, invite_private]


def save_rights():
    create_manager_rights_records()
    create_member_rights_records()


def create_manager_rights_records():
    print("\n>>>>>>>>>    manager rights")
    for right in manager_rights_list:
        print(right)
        adminRights(title=right["title"], sub_title=right["sub_title"], state=right["state"]).save()


def create_member_rights_records():
    print("\n>>>>>>>>>    member rights")
    for right in member_rights_list:
        print(right)
        memberRights(title=right["title"], sub_title=right["sub_title"], state=right["state"]).save()


def fill_rights():

    admin_rights = adminRights.objects.all().order_by("state")
    member_rights = memberRights.objects.all().order_by("state")

    members = Members.objects.select_related('member_id', 'community_id').filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state=9))

    for member in members:
        if member.state == 1 or member.state == 2:
            fill_admin_rights(member.member_id, member.community_id, admin_rights)
        else:
            fill_member_rights(member.member_id, member.community_id, member_rights)


def fill_admin_rights(user, community, rights_list):
    for right in rights_list:
        userAdminRights(user=user, community=community, right=right).save()


def fill_member_rights(user, community, rights_list):
    for right in rights_list:
        userMemberRights(user=user, community=community, right=right).save()

print(">>>>>> started")
save_rights()
fill_rights()
print(">>>>>> end")