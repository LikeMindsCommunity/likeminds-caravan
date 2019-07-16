
import  psycopg2
from connection import get_connection


def insert_hidden_tags(tag_id,tag_name):
    '''function to insert hidden tags in tags table'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="insert into togther_tags(category_id,category_name,state) values(%s,%s,%s)"
        parameter_list=[tag_id,tag_name,'1']
        curr.execute(sql,parameter_list)
        print('Hidden tags inserted successfully')
        curr.close()
        connection.commit()
        connection.close()
    except(Exception,psycopg2.error) as error:
        print("Error",error)



def insert_hidden_categories(category_name,community_id):

    '''function to add hidden categories in category table'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "insert into togther_community_tags(category,community_id_id) values(%s,%s)"
        parameter_list = [category_name,community_id]
        curr.execute(sql, parameter_list)
        curr.close()
        connection.commit()
        connection.close()
        print('Inserted Successfully',community_id)
    except(Exception, psycopg2.error) as error:
        print("Error", error)



def get_community_id(pattern):
    '''function to get existing communities based on name pattern'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql="select id from togther_community where name like '" + pattern + "%'"
        curr.execute(sql)
        community_id_list=curr.fetchall()
        curr.close()

        connection.close()
        return community_id_list
    except(Exception, psycopg2.error) as error:
        print("Error", error)



if __name__ == "__main__":

   insert_hidden_tags('iitd','IIT Delhi')
   insert_hidden_tags('nsit','NSIT College')


   community_id_list_iitd=get_community_id('IIT')
   community_id_list_nsit=get_community_id('NSIT')

   for community_id in community_id_list_iitd:
       insert_hidden_categories('IIT Delhi',community_id[0])

   for community_id in community_id_list_nsit:
       insert_hidden_categories('NSIT College', community_id[0])

   print('Community Inserted Successfully')
