import  psycopg2
from connection import get_connection

def get_tags_id():
    '''function to get existing communities based on name pattern'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql="select id,category_name from togther_tags"
        curr.execute(sql)
        tags_list=curr.fetchall()
        curr.close()

        connection.close()
        return tags_list
    except(Exception, psycopg2.error) as error:
        print("Error", error)



def update_community_tags(tags_id,category_name):

    '''function to update community tags'''

    try:
        connection = get_connection()
        curr = connection.cursor()
        sql="update togther_community_tags set tags_id=%s where category=%s"
        parameter_list=[tags_id,category_name]
        curr.execute(sql,parameter_list)
        curr.close()
        connection.commit()
        connection.close()
        print('category updated successfully')
    except(Exception, psycopg2.error) as error:
        print("Error", error)


if __name__=="__main__":

    tags_list=get_tags_id()

    for tag in tags_list:
        tag_id=tag[0]
        category_name=tag[1]
        print(tag_id)
        print(category_name)
        update_community_tags(tag_id,category_name)






