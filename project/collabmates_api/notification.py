import psycopg2
from pyfcm import FCMNotification


# file to store configuration of the system


# database details
db_user="apoorv"
db_password="khare"
db_host="127.0.0.1"
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



def send_notification_to_multiple_devices(token_list,message):
    '''This function is used to send notifications'''
    push_service = FCMNotification(api_key=server_key)

    result = push_service.notify_multiple_devices(registration_ids=token_list, message_title=message['title'], message_body=message['body'],data_message=message['payload'])
    print(result)
    print("\n\n")
    return result




def send_follow_notification(card,user,answer):

    '''function to send notification for followed members'''

    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="select member_id_id from togther_collabcard_follow where collabcard_id_id=%s"
        parameter_list=[card.id]
        curr.execute(sql,parameter_list)
        member_list=curr.fetchall()

        curr.execute("select name from togther_userinfo where user_id_id=%s",[user.id])
        answerer_name=curr.fetchone()
        curr.close()
        connection.close()
        message={}
        message['title']=str(answerer_name[0]) + " answered your query"
        message['body']=answer
        message['payload']={
            "route":"route://collabcard/"+str(card.id)
        }

        token_list=[]
        print(member_list)
        for member in member_list:

            if member[0] == user.id:
                continue
            fcm_token = get_token_for_fcm(member[0])
            token_list.append(fcm_token)
        print(token_list)
        send_notification_to_multiple_devices(token_list,message)

    except (Exception, psycopg2.Error) as error:

        print ("Error while connecting to PostgreSQL", error)













