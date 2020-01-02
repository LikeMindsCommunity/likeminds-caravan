import time
import psycopg2
from collabmates_api.notification import get_connection


def get_all_communities():

    '''function to get all the communities from database'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """select id,introduction_text from togther_community where introduction_text is not null and hide_community = '3'"""
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



def process_introduction_text_for_pre_created_communities():

    '''function to update introduction text for pre created communities'''

    commuity_list=get_all_communities()
    community_update_list=[]
    for community in commuity_list:
        temp={}
        append_string=". Also, mention what are you looking for from the community."
        introduction_text=community[1]

        if introduction_text.find('?') != -1:
           introduction_text=introduction_text.replace("?",append_string)

        else:
            introduction_text=introduction_text+append_string
        temp['community_id']=community[0]
        temp['introduction_text']=introduction_text
        community_update_list.append(temp)


    return community_update_list



def update_introduction_text_for_community():

    '''function to update introduction text from pre-created communities'''
    community_update_list=process_introduction_text_for_pre_created_communities()

    for community in community_update_list:
        update_introduction_text_for_community_util(community)
        print("Introduction Text Updated for community_id=",community['community_id'])


    print("Introduction Text Updated for all pre-created communities")



def update_introduction_text_for_community_util(community):
    '''function to update image links for user'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "update togther_community set introduction_text=%s where id=%s"
        parameter_list = [community['introduction_text'], community['community_id']]
        curr.execute(sql, parameter_list)
        curr.close()
        connection.commit()
        connection.close()

    except(Exception, psycopg2.Error) as error:
        print("Error", error)



update_introduction_text_for_community()
