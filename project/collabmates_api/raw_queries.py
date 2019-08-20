import psycopg2
from .notification import get_connection
from collections import OrderedDict

def get_all_tags_of_user(user_id):

    '''function to get all hidden tags of user'''
    try:
        conn = get_connection()
        curr = conn.cursor()

        sql="select tag_id from togther_userinfo_tags where user_id="+str(user_id)
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)



def get_communities_by_hidden_tags(tags_list):

    '''function to get communitites based on tags'''

    sql=""
    if len(tags_list) == 1:
        sql="select community_id_id from togther_community_tags where tags_id="+str(tags_list[0])+"order by community_id_id desc"
    elif len(tags_list) == 2:
        sql="select community_id_id from togther_community_tags where tags_id="+str(tags_list[0])+" UNION ALL "+"select community_id_id from togther_community_tags where tags_id="+str(tags_list[1])+"order by community_id_id desc"
    elif len(tags_list)>2:
        for tag in tags_list:
            sql=sql+"select community_id_id from togther_community_tags where tags_id="+str(tag)+" UNION ALL "

        #removing the last unioun all
        sql=sql[:-11]
        sql=sql+" order by community_id_id desc"
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def is_tag_present(community_id,tags_id):

    '''function to check whether the particular tag present for a particular community'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="select id from togther_community_tags where community_id_id=%s and tags_id=%s"
        parameters_list=[community_id,tags_id]
        curr.execute(sql,parameters_list)
        res = curr.fetchone()
        curr.close()
        conn.close()
        if res:
            return True
        return False
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)

def get_relevant_list(user_id,college_tag,category_tag=0):

    '''function to get relevant communities for the user'''
    user_tags=get_all_tags_of_user(user_id)
    tags_list=[]
    for tag in user_tags:
       tags_list.append(tag[0])
    tags=get_communities_by_hidden_tags(tags_list)
    relevance=dict()


    for tag in tags:
        if category_tag == 0:
            if is_tag_present(tag[0],college_tag):
                if tag[0] not in relevance:
                    relevance[tag[0]] = 1
                else:
                    relevance[tag[0]] = relevance[tag[0]] + 1
        elif is_tag_present(tag[0],category_tag):
            if is_tag_present(tag[0],college_tag):
                if tag[0] not in relevance:
                    relevance[tag[0]] = 1
                else:
                    relevance[tag[0]] = relevance[tag[0]] + 1

    relevant_dict = OrderedDict(sorted(relevance.items(),
                                      key=lambda kv: kv[1], reverse=True))
    relevance_list=list(relevant_dict.keys())
    return relevance_list

# if __name__=="__main__":
#     get_relevant_list(110)