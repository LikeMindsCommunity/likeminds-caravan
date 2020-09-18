from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import logging
import psycopg2
envir=False
#from utility.utils import custom_cache
try:
    from .notification import get_connection
    from project.celery import app

except:
    envir=True
    import sys
    sys.path.append("..")
    from scripts.connection import get_connection
    from project.celery import app


def update_conversation_engage_for_chatrooms(card_id,user_id,last_conversation_id,unseen_count):

    '''function to update chatroom data'''

    try:
        conn = get_connection()
        curr = conn.cursor()

        second_last_conversation = get_second_last_conversation_of_chatroom(card_id,user_id)
        print(second_last_conversation)
        sql="""update togther_conversationengage set last_conversation_id = %s ,unseen_count = %s, second_last_conversation_id=%s where card_id=%s and user_id = %s"""
        paramter_list = [last_conversation_id,unseen_count,second_last_conversation,card_id,user_id]
        curr.execute(sql,paramter_list)
        conn.commit()
        print("conversation engage updated successfully")
        curr.close()
        conn.close()


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def get_second_last_conversation_of_chatroom(card_id,user_id):

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select id from togther_card_answers where state=0 and card_id=%s and user_id !=%s order by id desc limit 1"""%(card_id,user_id)
        curr.execute(sql)
        data = curr.fetchone()
        second_last_conversation = None
        if data:
            second_last_conversation = data[0]
        curr.close()
        conn.close()

        return second_last_conversation


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_active_chatrooms_count_in_community(community_id,user_id,current_time):

    '''function to get active chatrooms based on community and user'''


    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where community_id=%s and user_id=%s  and remove_id is null 
        and (expiry_time is null or expiry_time > %s)"""%(str(community_id),str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_inactive_chatrooms_count_in_community(community_id,user_id,current_time):

    '''function to get in-active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where community_id=%s and user_id=%s  and remove_id is null 
        and (expiry_time is not null and expiry_time < %s)"""%(str(community_id),str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)



def get_active_chatrooms_count(user_id,current_time):

    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where  user_id=%s and remove_id is null 
        and (expiry_time is null or expiry_time > %s)"""%(str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()


        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_inactive_chatrooms_count(user_id,current_time):

    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where  user_id=%s  and remove_id is null 
        and (expiry_time is not null or expiry_time < %s)"""%(str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()


        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def get_active_followed_chatrooms_count(user_id,current_time):

    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where  user_id=%s and follow_status=True and remove_id is null 
        and (expiry_time is null or expiry_time > %s)"""%(str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()


        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_inactive_followed_chatrooms_count(user_id,current_time):

    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select count(*) from togther_collabcardState where  user_id=%s and follow_status=True and remove_id is null 
        and (expiry_time is not null and expiry_time < %s)"""%(str(user_id),str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()


        return count[0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)





def get_active_followed_chatrooms(user_id,current_time,page,limit=10):

    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()
        sql="""select id from togther_conversationEngage where user_id=%s and card_id  in
                  (select card_id from togther_collabcardState where user_id = %s and follow_status = True and (remove_id is null)
                 and (expiry_time is null or expiry_time > %s) 
                ) order by updated_at desc,id desc limit %s offset %s"""%(str(user_id),str(user_id),str(current_time),str(limit),str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = []

        for id in res:
            engage_list.append(id[0])
        curr.close()
        conn.close()

        return engage_list


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_inactive_followed_chatrooms(user_id,current_time,page,limit=10):

    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()
        sql="""select id from togther_conversationEngage where user_id=%s and card_id  in
                  (select card_id from togther_collabcardState where user_id = %s and follow_status = True and (remove_id is null)
                 and (expiry_time is not null and expiry_time <= %s) 
                ) order by updated_at desc,id desc limit %s offset %s"""%(str(user_id),str(user_id),str(current_time),str(limit),str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = []

        for id in res:
            engage_list.append(id[0])
        curr.close()
        conn.close()

        return engage_list


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_draft_chatrooms_on_home_screen(user_id,page,limit=10):

    '''api to get draft chatroom home-screen'''

    try:
        page_number = int(page)
        limit = 10
        offset = (page_number - 1) * 10

        conn = get_connection()
        curr = conn.cursor()
        sql = """select id,card_id,draft_id from togther_conversationEngage where user_id=%s order by updated_at desc,id desc limit %s offset %s""" % (
        str(user_id), str(limit), str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        draft_list = []

        for data in res:
            if data[2]:
                draft_list.append(data[0])
        curr.close()
        conn.close()

        return draft_list


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


@shared_task
def update_community_purpose_card(community_id,card_id):

    '''function to update community pupose collabcard'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        print(card_id)
        print(community_id)
        sql="""update togther_community set purpose_collabcard=%s where id=%s"""%(card_id,community_id)
        print(sql)
        curr.execute(sql)
        conn.commit()
        print("purpose updated successfully")
        curr.close()
        conn.close()


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)




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
        return []

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)




def filter_tags(user_id=0,community_id=0):
    '''function to return the filtered tags based on LPIG'''
    legacy=[]
    profession=[]
    interest=[]
    geo_list=[]
    sql=""

    if community_id:
        sql="select correct_tag_id from togther_community_legacy where community_id_id="+str(community_id)
        tags=get_all_data(sql)

        legacy=[]
        for data in tags:
            legacy.append(data[0])
        #legacy=get_list_of_tag_id(legacy,hashmap)

        sql = "select correct_tag_id from togther_community_profession where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        profession = []
        for data in tags:
            profession.append(data[0])
        #profession=get_list_of_tag_id(profession,hashmap)


        sql = "select correct_tag_id from togther_community_interest where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        interest = []
        for data in tags:
            interest.append(data[0])
        #interest = get_list_of_tag_id(interest, hashmap)

        sql = "select correct_tag_id from togther_community_geography where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        #geo_list = get_list_of_tag_id(geo_list, hashmap)

    if user_id:
        sql = "select correct_tag_id from togther_user_legacy where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        legacy = []
        for data in tags:
            legacy.append(data[0])
        #legacy = get_list_of_tag_id(legacy, hashmap)

        sql = "select correct_tag_id from togther_user_profession where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        profession = []
        for data in tags:
            profession.append(data[0])
        #profession = get_list_of_tag_id(profession, hashmap)

        sql = "select correct_tag_id from togther_user_interest where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        interest = []
        for data in tags:
            interest.append(data[0])
        #interest = get_list_of_tag_id(interest, hashmap)

        sql = "select correct_tag_id from togther_user_geography where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        #geo_list = get_list_of_tag_id(geo_list, hashmap)





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



def delete_previous_data_for_user(user_id):

    '''function to delete tag by id'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "delete from togther_community_rank where member_id_id=%s"
        parameter = [user_id]
        curr.execute(sql, parameter)
        conn.commit()
        curr.close()
        conn.close()
        print("Record deleted successfully for user:,",user_id)
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def action_for_user_crete_or_community_create(user_id,community_id):

    '''function to handle the create user or create community'''

    user_tags = []
    community_tags = []
    if user_id is not None and community_id is None:
        all_user = [(user_id,)]
        delete_previous_data_for_user(user_id)              #deleting the previous data of user
        user_tags = []
        for user in all_user:
            filter_tag = filter_tags(user_id=user[0])
            user_tags.append(filter_tag)
        flag=False

        if user_tags and not flag:
            sql = """SELECT community_id_id
                            FROM togther_community_legacy
                            INNER JOIN togther_user_legacy
                            ON togther_community_legacy.correct_tag_id = togther_user_legacy.correct_tag_id
                            and togther_user_legacy.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_profession
                            INNER JOIN togther_user_profession
                            ON togther_community_profession.correct_tag_id = togther_user_profession.correct_tag_id
                            and togther_user_profession.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_interest
                            INNER JOIN togther_user_interest
                            ON togther_user_interest.correct_tag_id = togther_community_interest.correct_tag_id
                            and togther_user_interest.user_id_id=%s and community_id_id
                            in 
                            (SELECT community_id_id
                            FROM togther_community_geography
                            INNER JOIN togther_user_geography
                            ON togther_community_geography.correct_tag_id = togther_user_geography.correct_tag_id
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
    print("Executing Compute Rank for User",user_id)
    #clearing the custom_cache
    #custom_cache.clear()
    start_time=time.time()
    action=action_for_user_crete_or_community_create(user_id,community_id)
    user_tags=action[0]
    community_tags=action[1]
    for user in user_tags:
        for community in community_tags:
            score = get_relevant_score(user, community)
            if score[2] != 0:
                ranking_tags(score)
                #print(score)


    end_time=time.time()

    print("Compute rank execution time :",(end_time-start_time))



@app.task
def ranking_all_users_and_communities():

    '''function to rank all users and all communities to be triggered daily'''

    start_time=time.time()

    print("Ranking All Users And Communities Based on tags")

    sql = "select user_id_id from togther_userinfo order by id desc"
    all_user = get_all_data(sql)
    for user in all_user:
        filter_tag = filter_tags(user_id=user[0])
        if filter_tag:
            compute_rank(user_id=user[0])
        else:
            print("No Onboarding for user_id:",user[0])


    end_time=time.time()

    diff=(end_time - start_time)

    print("Ranking Script Execution Time:",diff)






if envir:
    if __name__ == "__main__":
        print("python file")
        start_time=time.time()
        ranking_all_users_and_communities()

        end_time=time.time()

        print("Execution Time--")
        print(end_time-start_time)





