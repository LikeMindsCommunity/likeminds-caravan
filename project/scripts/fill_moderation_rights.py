from togther.models import (adminRights, memberRights, Members,
                            Community, userAdminRights, userMemberRights, communityRightsSettings)
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Count
import time
import psycopg2
from collabmates_api.notification import get_connection
import json

delete_room = {'id': 1, 'sub_title': None, 'title': 'Delete chat rooms/messages', "state": 0}

approve_members = {'id': 2, 'sub_title': None, 'title': 'Approve/remove members', "state": 1}

edit_community = {'id': 3, 'sub_title': None, 'title': "Edit community details", "state": 2}

view_contact = {'id': 4, 'sub_title': None, 'title': 'View member contact info', "state": 3}

add_manager = {'id': 5, 'sub_title': None, 'title': "Add community managers", "state": 4}

manager_rights_list = [delete_room, approve_members, edit_community, view_contact, add_manager]


create_room = {'id': 1, 'sub_title': None, 'title': "Create chat rooms", "state": 0}

create_poll = {'id': 2, 'sub_title': None, 'title': "Create polls", "state": 1}

create_event = {'id': 3, 'sub_title': None, 'title': "Create events", "state": 2}

respond_in_rooms = {'id': 4, 'sub_title': None, 'title': "Respond in chat rooms", "state": 3}

invite_private = {'id': 5, 'title': "Invite members via private link",
                  'sub_title': "Private links remain valid for 24 hours and. the user joining via them a re auto verified"
                  , "state": 4
                  }

auto_approve_rooms = {'id': 6, 'title': "Auto-approve created chat rooms",
                      'sub_title': "If auto-approved, member's chat rooms will be posted instantly and would not need any approval.",
                      "state": 5}

member_rights_list = [create_room, create_poll, create_event, respond_in_rooms, invite_private, auto_approve_rooms]


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
    print("\n>>>>>>>>>    filling rights")
    start_time = time.time()
    print(">>>>>> filling rights started >>>>>>>>   ", start_time)
    admin_rights = adminRights.objects.all().order_by("state")
    member_rights = memberRights.objects.all().order_by("state")

    members = Members.objects.select_related('member_id', 'community_id').filter(
        Q(state=1) | Q(state=2) | Q(state=4) | Q(state=7) | Q(state=9))

    for member in members:
        is_owner = member.is_owner
        if member.state == 1 or member.state == 2:
            fill_admin_rights(member.member_id, member.community_id, admin_rights, is_owner=is_owner)
            fill_member_rights(member.member_id, member.community_id, member_rights, is_admin=True)
        else:
            fill_member_rights(member.member_id, member.community_id, member_rights, is_admin=False)


    end_time = time.time()
    print(">>>>>> filling rights end >>>>>>>>   ", end_time)
    diff = end_time - start_time
    print(">>>>>> filling rights total time >>>>>>>>  ", diff)


def fill_admin_rights(user, community, rights_list, is_owner=False):

    loop_count = 0
    for right in rights_list:
        if not is_owner and loop_count >= 3:
            print(">>>> admin  --  ", user, community, right)
            break
        try:
            userAdminRights(user=user, community=community, right=right).save()
        except:
            print(">>>> member  --  ", user.id, community.id, right.id)
        loop_count += 1


def fill_member_rights(user, community, rights_list, is_admin=False):
    for right in rights_list:
        if not is_admin and right.state == 4:
            continue
        try:
            userMemberRights(user=user, community=community, right=right).save()
        except:
            print(">>>> member  --  ", user.id, community.id, right.id)

def get_communities_with_admins():
    '''function to get all the communities from database'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """SELECT community_id_id,count(community_id_id) FROM public.togther_members WHERE state=1 or state=2
                    group by community_id_id Having
                    COUNT(community_id_id) > 1 ORDER BY community_id_id ASC"""
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        connection.close()
        if res:
            return res
        else:
            return []
    except(Exception, psycopg2.Error) as error:
        print("Error", error)


def update_custom_title_for_Members():
    """ function to update all owners from database """
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """update togther_members set custom_title='Member' WHERE state=4 or state=7 or state=9"""
        curr.execute(sql)
        curr.close()
        connection.close()
    except(Exception, psycopg2.Error) as error:
        print("Error", error)


def update_custom_title_for_all():
    """ function to update all owners from database """
    Members.objects.filter(is_owner=False).filter(Q(state=1) | Q(state=2)).update(custom_title="Community Manager")
    Members.objects.filter(is_owner=True).filter(Q(state=1) | Q(state=2)).update(custom_title="Owner")
    Members.objects.filter(Q(state=4) | Q(state=7) | Q(state=9)).update(custom_title="Manager")



def update_community_owners():
    """ function to update all owners from database """
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """update togther_members set is_owner=true, custom_title='Owner' where id in (
                 SELECT MIN(id) as id FROM togther_members WHERE state=1 or state=2
                 GROUP BY community_id_id Having COUNT(community_id_id) > 0)"""
        curr.execute(sql)
        curr.close()
        connection.close()
    except(Exception, psycopg2.Error) as error:
        print("Error", error)


def fill_parent_for_admins():
    print("\n>>>>>>>>>     filling parent")
    community_ids = get_communities_with_admins()
    for community_id in community_ids:
        owner = Members.objects.filter(community_id=community_id[0], is_owner=True)
        # print("owner >>>>>>>  ", owner, community_id[0])
        if owner.exists():
            owner_id = owner[0].member_id
            parent_list = json.dumps([str(owner[0].member_id.id)])
            status = Members.objects.filter(community_id=community_id,
                                            is_owner=False, state=1).update(parent_cm=owner_id,
                                                                            parent_cm_list=parent_list)


def fill_community_setting_rights():
    print("\n>>>>>>>>>     filling community_setting rights")
    communities = Community.objects.all()
    member_rights = memberRights.objects.all().order_by("state")
    for community in communities:
        save_community_setting_rights(community, member_rights)


def save_community_setting_rights(community, rights_list):

    for right in rights_list:
        try:
            communityRightsSettings(community=community, right=right).save()
        except:
            print(">>>> member  --  ", community.id, right.id)



start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)

# save_rights()
# update_community_owners()
# update_custom_title_for_all()
# fill_rights()
# fill_parent_for_admins()
fill_community_setting_rights()

end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time - start_time
print(">>>>>> total >>>>>>>>  ", diff)

# fill_moderation_rights.py

