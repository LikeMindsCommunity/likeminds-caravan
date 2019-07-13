import psycopg2
from pyfcm import FCMNotification
from django.conf import  settings

# file to store configuration of the system


# database details
db_user="apoorv"
db_password="khare"
db_host=settings.DB_HOST
db_port="5432"
db_database="togther"



# server keys for sending notification

server_key = 'AAAAllezPSk:APA91bEYRnVqZGMS_YNTDwu4wJfQfbubN7jQtwvdAyZI6XvoRIjQPii9kj2joizPGJ8GhcoXpcIF5ftsZ-zyBuY9WzqS48b2JCZ51Lv8K9L56gMwBjLsW7tDSfntEqMtAQ9f8f024M5P'



def get_connection():
    '''function to create a postgres connection'''
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_database)
        return connection
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)


def get_token_for_fcm(member_id):

    '''function to get token from user'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute("select fcm_token from togther_userinfo where user_id_id=" + str(member_id))
        fcm_token = curr.fetchone()
        return fcm_token[0]
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL  ", error)

def get_community_name(community_id):
    try:
        conn=get_connection()
        curr=conn.cursor()
        sql = "select name from togther_community where id= " + str(community_id)
        curr.execute(sql)
        community_name = curr.fetchone()[0]
        curr.close()
        conn.close()
        return community_name
    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)


def send_notification_to_multiple_devices(token_list,message):
    '''This function is used to send notifications'''
    push_service = FCMNotification(api_key=server_key)


    result = push_service.notify_multiple_devices(registration_ids=token_list,data_message=message['payload'])
    print(result)

    return result


def send_follow_notification(card,user,answer):

    '''function to send notification to followed members'''

    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_follow_collabcard where collabcard_id_id=%s"
        parameter_list=[card.id]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()
        curr.execute("select name from togther_userinfo where user_id_id=%s",[user.id])
        answerer_name=curr.fetchone()
        curr.close()
        connection.close()
        message={}

        message['payload']={
            "title":str(answerer_name[0]) + " responded",
            "sub_title":answer,
            "route":"route://collabcard?collabcard_id="+str(card.id)
        }
        token_list=[]

        for member in member_list:

            if member[0] == user.id:
                continue
            fcm_token = get_token_for_fcm(member[0])
            token_list.append(fcm_token)
        send_notification_to_multiple_devices(token_list,message)

    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)



def send_notification_to_admins(community_id,name):
    '''function to send notification to community admins'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_members where community_id_id= " + str(community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins=curr.fetchall()
        token_list=[]
        for admin in admins:
             fcm_token=get_token_for_fcm(admin[0])
             token_list.append((fcm_token))

        community_name=get_community_name(community_id)
        message={}
        message['payload']={
            'title':community_name,
            'sub_title':str(name)+' has requested to join your community',
            'route':'route://member_approve?'+'community_id=' + str(community_id) + "&" + "community_name=" + str(community_name)
        }
        send_notification_to_multiple_devices(token_list,message)
        curr.close()
        connection.close()
    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)


def send_notification_for_join_requests(community_id,flag,member_id):
    '''function to send notification for approval or denial'''
    community_name=get_community_name(community_id)
    fcm_token=get_token_for_fcm(member_id)
    token_list=[]
    token_list.append(fcm_token)
    message={}
    if flag:
        message['payload']={
            'title':community_name,
            'sub_title':"Congrats! you are now part of this commnity",
            'route':'route://member_approved?community_id='+ str(community_id)
        }
    else:
        message['payload'] = {
            'title': community_name,
            'sub_title': "Sorry! your request to join this community has been rejected",
            'route': 'route://member_declined?community_id=' + str(community_id)
        }

    send_notification_to_multiple_devices(token_list,message)


def send_notification_for_new_collabcard_posted(community_id,collabcard_title,poster_id,poster_name):
    '''function to send notification to all members when new collabcard is posted'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_members where community_id_id=%s and member_id_id !=%s and (state=1 or state=2 or state=4)"
        parameter_list=[community_id,poster_id]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()

        token_list=[]
        for member in member_list:
            token=get_token_for_fcm(member[0])
            token_list.append(token)
        community_name=get_community_name(community_id)
        message={}
        message['payload']={
            'title':str(poster_name) + " @ "+str(community_name),
            'sub_title':str(collabcard_title),
            'route':'route://community_collabcard?community_id=' + str(community_id) + '&community_name='+ str(community_name)
        }

        send_notification_to_multiple_devices(token_list,message)


    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)



def send_notification_to_proposed_admin(nominated_admin_id,community_id,proposed_admin_name):
    '''function to send notification to proposed admin'''

    fcm_token=get_token_for_fcm(nominated_admin_id)

    if fcm_token:
        token_list=[]
        token_list.append(fcm_token)
        community_name = get_community_name(community_id)
        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': str(proposed_admin_name) + " has nominated you as a promoter of this community ",
            'route': 'route://community?community_id=' + str(community_id)
        }

        send_notification_to_multiple_devices(token_list, message)







