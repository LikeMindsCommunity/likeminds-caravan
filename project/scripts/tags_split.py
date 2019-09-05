import psycopg2
from connection import get_connection
import json
import time
def get_all_tags(sql):

    '''function to get tags based on sql'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        return res

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def insert_tags(sql,parameter):

    '''function to split the tags and insert it in table'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql,parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully" )
        curr.close()
        conn.close()

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def is_exist(sql,parameter):

    '''function to check the existance of tags'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql,parameter)
        res=curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return True
        return False

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def split_community():

    '''function to split the communities for existing tags'''

    sql = "select legacy,profession,interests,geography,community_id_id from togther_community_lpig"

    community_tags = get_all_tags(sql)

    for community in community_tags:

        legacy = json.loads(community[0])
        profession = json.loads(community[1])
        interest = json.loads(community[2])
        geography = json.loads(community[3])

        for each in legacy:

            sql = "select id from togther_community_legacy where community_id_id=%s and tags_id_id=%s"
            parameter = [community[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_community_legacy(tags_id_id,community_id_id) values(%s,%s)"
                parameter = [each, community[4]]
                insert_tags(sql, parameter)

        for each in profession:

            sql = "select id from togther_community_profession where community_id_id=%s and tags_id_id=%s"
            parameter = [community[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_community_profession(tags_id_id,community_id_id) values(%s,%s)"
                parameter = [each, community[4]]
                insert_tags(sql, parameter)

        for each in interest:

            sql = "select id from togther_community_interest where community_id_id=%s and tags_id_id=%s"
            parameter = [community[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_community_interest(tags_id_id,community_id_id) values(%s,%s)"
                parameter = [each, community[4]]
                insert_tags(sql, parameter)

        for each in geography:

            sql = "select id from togther_community_geography where community_id_id=%s and tags_id_id=%s"
            parameter = [community[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_community_geography(tags_id_id,community_id_id) values(%s,%s)"
                parameter = [each, community[4]]
                insert_tags(sql, parameter)


def split_user():

    '''function to split the user for existing tags'''

    sql = "select legacy,profession,interests,geography,member_id_id from togther_user_lpig"

    user_tags = get_all_tags(sql)

    for user in user_tags:

        legacy = json.loads(user[0])
        profession = json.loads(user[1])
        interest = json.loads(user[2])
        geography = json.loads(user[3])

        for each in legacy:

            sql = "select id from togther_user_legacy where user_id_id=%s and tags_id_id=%s"
            parameter = [user[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_user_legacy(tags_id_id,user_id_id) values(%s,%s)"
                parameter = [each, user[4]]
                insert_tags(sql, parameter)

        for each in profession:

            sql = "select id from togther_user_profession where user_id_id=%s and tags_id_id=%s"
            parameter = [user[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_user_profession(tags_id_id,user_id_id) values(%s,%s)"
                parameter = [each, user[4]]
                insert_tags(sql, parameter)

        for each in interest:

            sql = "select id from togther_user_interest where user_id_id=%s and tags_id_id=%s"
            parameter = [user[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_user_interest(tags_id_id,user_id_id) values(%s,%s)"
                parameter = [each, user[4]]
                insert_tags(sql, parameter)

        for each in geography:

            sql = "select id from togther_user_geography where user_id_id=%s and tags_id_id=%s"
            parameter = [user[4], each]

            if not is_exist(sql, parameter):
                sql = "insert into togther_user_geography(tags_id_id,user_id_id) values(%s,%s)"
                parameter = [each, user[4]]
                insert_tags(sql, parameter)

if __name__ == "__main__":

    current_time=time.time()
    split_community()
    split_user()
    end_time=time.time()
    print(end_time-current_time)