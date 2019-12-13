import time

import psycopg2
from collabmates_api.notification import get_connection


def get_all_tag_id():

    '''function to get the tag id from tags_lpig tables'''

    try:
        connection = get_connection()
        curr = connection.cursor()

        sql = """select id,category_id_id from togther_tags_lpig order by id"""
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



def get_count_based_on_tags_selected_by_user(category_id,tag_id):

    '''function to get the count of tags seleted by the user'''

    try:
        connection = get_connection()
        curr = connection.cursor()

        if category_id == 1:
            sql="select count(*) from togther_user_legacy where tags_id_id=%s"
        elif category_id == 2:
            sql = "select count(*) from togther_user_profession where tags_id_id=%s"
        elif category_id == 3:
            sql = "select count(*) from togther_user_interest where tags_id_id=%s"
        elif category_id == 4:
            sql = "select count(*) from togther_user_geography where tags_id_id=%s"
        else:
            return 0
        parameter_list=[tag_id]
        curr.execute(sql,parameter_list)
        res = curr.fetchone()
        curr.close()
        connection.close()
        return res

    except(Exception, psycopg2.Error) as error:
        print("Error", error)



def update_rank_of_tags(tag_id,rank):

    '''function to update the rank of tags'''

    try:
        connection = get_connection()
        curr = connection.cursor()

        sql = """update togther_tags_lpig set tag_rank=%s where id=%s"""
        parameter_list=[rank,tag_id]
        curr.execute(sql,parameter_list)
        connection.commit()
        curr.close()
        connection.close()
        print("Rank updated for id=",tag_id)

    except(Exception, psycopg2.Error) as error:
        print("Error", error)


def update_Tags_rank_based_on_user_selections():

    '''function to update all tags based on user selection'''

    all_tags=get_all_tag_id()
    for tag in all_tags:
        count=get_count_based_on_tags_selected_by_user(tag[1],tag[0])
        update_rank_of_tags(tag[0],count)


update_Tags_rank_based_on_user_selections()