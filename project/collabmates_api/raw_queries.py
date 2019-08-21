# from __future__ import absolute_import, unicode_literals
# from celery import shared_task
import time
import json
import psycopg2

envir=False
try:
    from .notification import notification
except:
    envir=True
    import sys
    sys.path.append("..")
    from scripts.connection import get_connection

def get_all_tags(sql):

    '''function to get tags based on sql'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res[0]

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def filter_tags(user_id=0,community_id=0):
    '''function to return the filtered tags based on LPIG'''
    sql=""
    if user_id:
        sql="select id,member_id_id,geography,interests,legacy,profession from togther_user_lpig where member_id_id="+str(user_id)
    elif community_id:
        sql = "select id,community_id_id,geography,interests,legacy,profession from togther_community_lpig where community_id_id=" + str(community_id)
    res=get_all_tags(sql)

    if res is None:
        return {}
    legacy=None
    profession=None
    interests=None
    geo_list = []
    if res[4]:
        legacy=json.loads(res[4])

    if res[5]:
        profession=json.loads(res[5])

    if res[3]:
        interests=json.loads(res[3])

    if res[2]:

        geo_list=json.loads(res[2])

    tags={}

    if user_id:
        tags['user_id']=user_id

    if community_id:
        tags['community_id']=community_id
    tags['legacy']=legacy
    tags['profession']=profession
    tags['interests']=interests
    tags['geography']=geo_list
    return tags

def get_all_data(sql):
    '''function to get all data based on a sql query'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_global_id():

    '''function that will give the global id to the user'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="select * from togther_tags_lpig where category_id_id=5"
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        global_tags={}
        if res:
            for tag in res:
                global_tags[tag[1]]=tag[0]
            return global_tags

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_relevant_score(user,community):

    '''function to get relevant score of community'''

    legacy_user_list = user['legacy']
    geo_user_list = user['geography']
    interest_user_list = user['interests']
    profession_user_list = user['profession']

    #community attributes
    legacy_community_list=community['legacy']
    geo_community_list=community['geography']
    interest_community_list=community['interests']
    profession_community_list=community['profession']




    count_legacy=0
    count_geography=0
    count_interest=0
    count_profession=0

    # for legacy in legacy_user_list:
    #     if legacy in legacy_community_list:
    #         count_legacy += 1

    if legacy_community_list is None or profession_community_list is None or interest_community_list is None:
        return (user['user_id'],community['community_id'],0)


    for legacy in legacy_community_list:
        if legacy in legacy_user_list:
            count_legacy+=1

    if count_legacy != len(legacy_community_list):
         count_legacy=0

    for geography in geo_user_list:
        if geography in geo_community_list:
            count_geography += 1

    for interest in interest_user_list:
        if interest in interest_community_list:
            count_interest += 1

    for profession in profession_user_list:
        if profession in profession_community_list:
            count_profession += 1


    if count_legacy==0 or count_geography==0 or count_interest == 0 or count_profession == 0:
        relevance_score=0
    elif count_legacy and count_geography and count_profession and count_interest:
        relevance_score=count_legacy+count_profession+count_interest+count_geography
    else:
        relevance_score=0

    return (user['user_id'],community['community_id'],relevance_score)


#community ranking based on user tags

def ranking_tags(tag):

    '''function to map communities and user based on rank.It inserts data for the tags'''

    id=is_tag_present(tag)
    if id:
        delele_tag_by_id(id)

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "insert into togther_community_rank(member_id_id,community_id_id,weight) values(%s,%s,%s)"
        parameter = [tag[0], tag[1], tag[2]]
        curr.execute(sql, parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully into community_rank table")
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def is_tag_present(tag):

    '''function to check whether the tag is already present in rank table or not'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select * from  togther_community_rank where member_id_id=%s and community_id_id=%s"
        parameter = [tag[0],tag[1]]
        curr.execute(sql, parameter)
        res = curr.fetchone()
        curr.close()
        conn.close()
        if res:
            return res[0]
        return False
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def update_tag(tag,id):

    '''function to update data in community rank table'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "update togther_community_rank set member_id_id=%s,community_id_id=%s,weight=%s where id=%s"
        parameter = [tag[0], tag[1], tag[2],id]
        curr.execute(sql, parameter)
        conn.commit()
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def delele_tag_by_id(id):

    '''function to delete tag by id'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "delete from togther_community_rank where id=%s"
        parameter = [id]
        curr.execute(sql, parameter)
        conn.commit()
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def compute_rank():

    '''function to run '''
    sql = "select member_id_id from togther_user_lpig"
    all_user = get_all_data(sql)
    user_tags = []
    for user in all_user:
        filter_tag = filter_tags(user_id=user[0])
        user_tags.append(filter_tag)

    # getting all communities
    sql = "select community_id_id from togther_community_lpig"
    all_communities = get_all_data(sql)
    community_tags = []
    for community in all_communities:
        filter_tag = filter_tags(community_id=community[0])
        community_tags.append(filter_tag)

    for user in user_tags:
        for community in community_tags:
            score = get_relevant_score(user, community)
            if score[2] != 0:
                ranking_tags(score)

if envir:
    if __name__ == "__main__":
        print("python file")
        start_time=time.time()
        compute_rank()
        end_time=time.time()

        print("Execution Time--")
        print(end_time-start_time)



