import psycopg2
from connection import get_connection
import time
def get_all_community():

    '''function to get all communities'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select id from togther_community order by id"
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_all_members_of_community(community_id):

    '''function to get all members of the community'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select member_id_id,state from togther_members where community_id_id=%s and (state=1 or state=2 or state=4 or state=7)"
        curr.execute(sql,[community_id])
        res = curr.fetchall()
        curr.close()
        conn.close()
        return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_count_of_pending_members(community_id):

    '''function to get the count of pending members'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select count(*) from togther_members where state=3 and community_id_id=%s"
        curr.execute(sql,[community_id])
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res[0]
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_latest_collabcard(community_id):

    '''function to get the latest collabcard '''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select max(id) from togther_collabcard  where community_id=%s"
        curr.execute(sql, [community_id])
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res[0]
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def is_data_exists(member_id,community_id):

    '''function to test if data exists or not'''
    try:
        conn=get_connection()
        curr=conn.cursor()
        sql="select id from togther_member_engage where member_id_id=%s and community_id_id=%s"
        parameter=[member_id,community_id]
        curr.execute(sql,parameter)
        res=curr.fetchone()
        curr.close()
        conn.close()
        if res:
            return True
        return False
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)



def insert_in_members_engage(member_data):

    '''inserting the data in members engage table'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        if 'pending_member_count' in member_data:
            sql = "insert into togther_member_engage(community_id_id,member_id_id,pending_members,last_unseen_conversation_id,updated_at,last_unseen_count) values(%s,%s,%s,%s,%s,%s)"
            parameter_list=[]
            parameter_list.append(member_data['community_id'])
            parameter_list.append(member_data['member_id'])
            parameter_list.append(member_data['pending_member_count'])
            parameter_list.append(member_data['collabcard_id'])
            parameter_list.append(member_data['updated_at'])
            parameter_list.append(0)

        else:
            sql = "insert into togther_member_engage(community_id_id,member_id_id,last_unseen_conversation_id,updated_at,pending_members,last_unseen_count) values(%s,%s,%s,%s,%s,%s)"
            parameter_list = []
            parameter_list.append(member_data['community_id'])
            parameter_list.append(member_data['member_id'])
            parameter_list.append(member_data['collabcard_id'])
            parameter_list.append(member_data['updated_at'])
            parameter_list.append(0)
            parameter_list.append(0)

        curr.execute(sql, parameter_list)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully into member_engage table")
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

if __name__ == "__main__":

    start_time=time.time()
    all_community=get_all_community()

    for id in all_community:

        community_id=id[0]

        members=get_all_members_of_community(community_id)
        collabcard_id=get_latest_collabcard(community_id)
        pending_members_count=get_count_of_pending_members(community_id)

        for member in members:
            parameter = {}
            parameter['community_id']=community_id
            parameter['collabcard_id']=collabcard_id[0]
            current_time=time.time()
            parameter['updated_at']=current_time
            if member[1] == 1 or member[1] == 2 :
               parameter['member_id']=member[0]
               parameter['pending_member_count']=pending_members_count[0]
            else:
                parameter['member_id']=member[0]

            if not is_data_exists(member[0],community_id):
                insert_in_members_engage(parameter)
    end_time=time.time()
    print(end_time-start_time)

