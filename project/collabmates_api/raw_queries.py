from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import json
import psycopg2

envir=False
try:
    from .notification import get_connection
except:
    envir=True
    import sys
    sys.path.append("..")
    from scripts.connection import get_connection



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

def create_hashmap():

    '''function to crate a hashmap in order to store relevant id of tags'''

    correct_tags={}

    sql="select id,tag_id from togther_tags_lpig"

    tags=get_all_data(sql)

    for tag in tags:
        if tag[0]:
            correct_tags[tag[0]]=tag[1]

    return correct_tags

def get_list_of_tag_id(tags,hashmap):

    '''function to insert tag to tags list which is mapped in hashmap'''
    tag_list=[]
    for tag in tags:
        tag_list.append(hashmap[tag])
    return tag_list


def filter_tags(user_id=0,community_id=0):
    '''function to return the filtered tags based on LPIG'''
    hashmap=create_hashmap()
    legacy=[]
    profession=[]
    interest=[]
    geo_list=[]
    sql=""

    if community_id:
        sql="select tags_id_id from togther_community_legacy where community_id_id="+str(community_id)
        tags=get_all_data(sql)

        legacy=[]
        for data in tags:
            legacy.append(data[0])
        legacy=get_list_of_tag_id(legacy,hashmap)

        sql = "select tags_id_id from togther_community_profession where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        profession = []
        for data in tags:
            profession.append(data[0])
        profession=get_list_of_tag_id(profession,hashmap)


        sql = "select tags_id_id from togther_community_interest where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        interest = []
        for data in tags:
            interest.append(data[0])
        interest = get_list_of_tag_id(interest, hashmap)

        sql = "select tags_id_id from togther_community_geography where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        geo_list = get_list_of_tag_id(geo_list, hashmap)

    if user_id:
        sql = "select tags_id_id from togther_user_legacy where user_id_id=" + str(user_id)
        tags = get_all_data(sql)

        legacy = []
        for data in tags:
            legacy.append(data[0])
        legacy = get_list_of_tag_id(legacy, hashmap)

        sql = "select tags_id_id from togther_user_profession where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        profession = []
        for data in tags:
            profession.append(data[0])
        profession = get_list_of_tag_id(profession, hashmap)

        sql = "select tags_id_id from togther_user_interest where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        interest = []
        for data in tags:
            interest.append(data[0])
        interest = get_list_of_tag_id(interest, hashmap)

        sql = "select tags_id_id from togther_user_geography where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        geo_list = get_list_of_tag_id(geo_list, hashmap)



    tags={}

    if user_id:
        tags['user_id']=user_id

    if community_id:
        tags['community_id']=community_id

    tags['legacy']=legacy
    tags['profession']=profession
    tags['interest']=interest
    tags['geography']=geo_list

    return tags



def get_relevant_score(user,community):

    '''function to get relevant score of community'''

    legacy_user_list = user['legacy']
    geo_user_list = user['geography']
    interest_user_list = user['interest']
    profession_user_list = user['profession']

    #community attributes
    legacy_community_list=community['legacy']
    geo_community_list=community['geography']
    interest_community_list=community['interest']
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
         return (user['user_id'], community['community_id'], 0)

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




def action_for_user_crete_or_community_create(user_id,community_id):

    '''function to handle the create user or create community'''

    user_tags = []
    community_tags = []
    # if user_id is None and community_id is None:
    #     sql = "select distinct(user_id_id) from togther_user_legacy"
    #     all_user = get_all_data(sql)
    #     user_tags = []
    #     for user in all_user:
    #         filter_tag = filter_tags(user_id=user[0])
    #         user_tags.append(filter_tag)
    #     # getting all communities
    #     sql = "select distinct(community_id_id) from togther_community_legacy"
    #     all_communities = get_all_data(sql)
    #     community_tags = []
    #     for community in all_communities:
    #         filter_tag = filter_tags(community_id=community[0])
    #         community_tags.append(filter_tag)


    if user_id is not None and community_id is None:
        all_user = [(user_id,)]
        user_tags = []
        for user in all_user:
            filter_tag = filter_tags(user_id=user[0])
            user_tags.append(filter_tag)
        flag=False

        if user_tags and not flag:
            sql = """SELECT community_id_id
                            FROM togther_community_legacy
                            INNER JOIN togther_user_legacy
                            ON togther_community_legacy.tags_id_id = togther_user_legacy.tags_id_id
                            and togther_user_legacy.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_profession
                            INNER JOIN togther_user_profession
                            ON togther_community_profession.tags_id_id = togther_user_profession.tags_id_id
                            and togther_user_profession.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_interest
                            INNER JOIN togther_user_interest
                            ON togther_user_interest.tags_id_id = togther_community_interest.tags_id_id
                            and togther_user_interest.user_id_id=%s and community_id_id
                            in 
                            (SELECT community_id_id
                            FROM togther_community_geography
                            INNER JOIN togther_user_geography
                            ON togther_community_geography.tags_id_id = togther_user_geography.tags_id_id
                            and togther_user_geography.user_id_id=%s)))
                    """ % (user_id, user_id, user_id, user_id)
            all_communities = []
            flag = True
            data = get_all_data(sql)
            for i in data:
                all_communities.append(i[0])

        else:
            sql = "select distinct(community_id_id) from togther_community_legacy"
            all_communities = get_all_data(sql)

        community_tags = []

        for community in all_communities:
            if not flag:
                filter_tag = filter_tags(community_id=community[0])
            else:
                filter_tag = filter_tags(community_id=community)
            community_tags.append(filter_tag)
        #print(community_tags)

    elif user_id is None and community_id is not None:
        sql = "select distinct(user_id_id) from togther_user_legacy"
        all_user = get_all_data(sql)
        user_tags = []
        for user in all_user:
            filter_tag = filter_tags(user_id=user[0])
            user_tags.append(filter_tag)

        all_communities = [(community_id,)]
        community_tags = []
        for community in all_communities:
            filter_tag = filter_tags(community_id=community[0])
            community_tags.append(filter_tag)


    return (user_tags,community_tags)

@shared_task
def compute_rank(user_id=None,community_id=None):

    '''function to compute the rank of community '''
    start_time=time.time()
    action=action_for_user_crete_or_community_create(user_id,community_id)
    user_tags=action[0]
    community_tags=action[1]
    for user in user_tags:
        for community in community_tags:
            score = get_relevant_score(user, community)
            id = is_tag_present(score)
            if id:
                delele_tag_by_id(id)
            if score[2] != 0:
                ranking_tags(score)


    end_time=time.time()

    print("Compute rank execution time:",(end_time-start_time))





if envir:
    if __name__ == "__main__":
        print("python file")
        start_time=time.time()
        compute_rank(user_id=104)

        end_time=time.time()

        print("Execution Time--")
        print(end_time-start_time)





