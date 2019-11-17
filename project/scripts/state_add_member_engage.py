import  psycopg2
from collabmates_api.notification import get_connection

def update_state_for_user_in_member_engage():

    '''function to update state of user in members engage'''
    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="""
                UPDATE togther_member_engage
                SET member_state = togther_members.state
                FROM togther_members
                WHERE togther_members.community_id_id = togther_member_engage.community_id_id
                AND togther_members.member_id_id=togther_member_engage.member_id_id
            """
        curr.execute(sql)
        print("Member Engage updated successfully")
        curr.close()
        connection.commit()
        connection.close()
    except(Exception,psycopg2.error) as error:
        print("Error",error)




update_state_for_user_in_member_engage()