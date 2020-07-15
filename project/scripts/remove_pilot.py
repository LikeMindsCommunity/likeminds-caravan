import time
from togther.models import Members,Member_Engage,membersEngagePilot,membersPilot

from django.db import connection

def get_pilot_communities_for_users(table_name):

    '''function to get iitd communities ids'''

    cursor = connection.cursor()


    sql = """select community_id_id,member_id_id from %s where community_id_id
    in(select id from togther_community where hide_community = '3') order by id"""%(table_name)
    cursor.execute(sql)
    res=cursor.fetchall()

    pilot_list = []

    for data in res:
        temp ={}
        #temp['id'] = data[0]
        temp['community_id'] = data[0]
        temp['member_id'] = data[1]

        pilot_list.append(temp)

    return pilot_list


def create_backup_for_members_engage():

    '''function to create backup of members engage'''

    pilot_list = get_pilot_communities_for_users("togther_member_engage")

    for pilot in pilot_list:

        pilot_filter = membersEngagePilot.objects.filter(member=pilot['member_id'],community=pilot['community_id'])
        engage_filter = Member_Engage.objects.filter(member_id=pilot['member_id'],community_id=pilot['community_id'])
        if not pilot_filter.exists() and engage_filter.exists():

            instance = engage_filter[0]

            engage_pilot = membersEngagePilot()
            engage_pilot.member = instance.member_id
            engage_pilot.community = instance.community_id
            engage_pilot.last_unseen_conversation = instance.last_unseen_conversation
            engage_pilot.last_unseen_count = instance.last_unseen_count
            engage_pilot.pending_members = instance.pending_members
            engage_pilot.updated_at = instance.updated_at
            engage_pilot.member_referral = instance.member_referral
            engage_pilot.member_state = instance.member_state
            engage_pilot.save()

        delete = engage_filter.delete()
        print(delete)



def create_backup_for_members():

    '''function to create backup of members engage'''

    pilot_list = get_pilot_communities_for_users("togther_members")

    for pilot in pilot_list:

        pilot_filter = membersPilot.objects.filter(member_id=pilot['member_id'],community_id=pilot['community_id'])
        member_filter = Members.objects.filter(member_id=pilot['member_id'],community_id=pilot['community_id'])
        if not pilot_filter.exists() and member_filter.exists():

            instance = member_filter[0]

            member_pilot = membersPilot()
            member_pilot.member_id = instance.member_id
            member_pilot.community_id = instance.community_id
            member_pilot.state = instance.state
            member_pilot.created_at = instance.created_at
            member_pilot.tool_state = instance.tool_state
            member_pilot.ask_member_id = instance.ask_member_id
            member_pilot.approved_member_id = instance.approved_member_id
            member_pilot.edit_required = instance.edit_required
            member_pilot.actions_required = instance.actions_required
            member_pilot.save()

        delete = member_filter.delete()
        print(delete)



start_time = time.time()
create_backup_for_members_engage()
print("member engage backup created")
print("pilot communities deleted from members engage")

create_backup_for_members()
print("members  backup created")
print("pilot communities deleted from members ")

end_time = time.time()

print(end_time-start_time)