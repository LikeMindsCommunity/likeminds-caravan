from togther.models import (adminRights, memberRights, Members,
                            Community, userAdminRights, userMemberRights)
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Count
import time
import psycopg2
from collabmates_api.notification import get_connection

delete_room = {'id': 1, 'title': 'Delete chat rooms/messages', 'sub_title': None, "state": 0}

approve_members = {'id': 2, 'title': 'Approve/remove members', 'sub_title': None, "state": 1}

edit_community = {'id': 3, 'title': "Edit community details", 'sub_title': None, "state": 2}

view_contact = {'id': 4, 'title': 'View member contact info', 'sub_title': None, "state": 3}

add_manager = {'id': 5, 'title': "Add community managers", 'sub_title': None, "state": 4}

manager_rights_list = [delete_room, approve_members, edit_community, view_contact, add_manager]

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
            fill_member_rights(member.member_id, member.community_id, member_rights)
        else:
            fill_member_rights(member.member_id, member.community_id, member_rights)


def fill_admin_rights(user, community, rights_list):
    for right in rights_list:
        userAdminRights(user=user, community=community, right=right).save()


def fill_member_rights(user, community, rights_list):
    for right in rights_list:
        userMemberRights(user=user, community=community, right=right).save()


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


def update_community_owners():

    '''function to get all the communities from database'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """Update public.togther_members set is_owner=true where community_id_id in 
                    (SELECT community_id_id FROM public.togther_members WHERE state=1 or state=2
                    group by community_id_id Having
                    COUNT(community_id_id) > 1 ORDER BY community_id_id ASC)
                and state=1 or state=2"""
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


def fill_parent_for_admins():

    community_ids = get_communities_with_admins()

    for community_id in community_ids:
        print(community_id[0])
        members = Members.objects.filter(community_id=community_id[0]).order_by("id")

    # for member in members:
    #     print(member.count_status)

        # if member.admin_count > 1:
        #     print(member.community_id.id)
        # if members.exists() and members.count() > 1:
        #     pass


start_time = time.time()
print(">>>>>> started >>>>>>>>   ", start_time)


# save_rights()
# fill_rights()
fill_parent_for_admins()


end_time = time.time()
print(">>>>>> end >>>>>>>>  ", end_time)
diff = end_time-start_time
print(">>>>>> total >>>>>>>>  ", diff)

"""-- SELECT DISTINCT community_id_id,member_id_id FROM public.togther_members WHERE state=1 or state=2
-- group by community_id_id, member_id_id Having
-- COUNT(community_id_id) > 1 ORDER BY community_id_id ASC 

SELECT
    community_id_id, MIN(member_id_id)
FROM
    togther_members
GROUP BY
    community_id_id"""