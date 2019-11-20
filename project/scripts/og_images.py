import time
import psycopg2
from collabmates_api.notification import get_connection
from django.conf import settings
from utility.firebase import upload_community_thumbnail

url=settings.URL

def get_all_community_images():

    '''function to get community images for firebase migration'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = """select id,image_link from togther_community where image_link!='' order by id desc"""
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        connection.close()
        if res:
            return res
        else:
            return []
    except(Exception, psycopg2.error) as error:
        print("Error", error)



def upload_all_community_thumbnail():

    '''function to migrate user images to firebase'''

    start_time = time.time()
    files = get_all_community_images()

    count = 0
    for file in files:
        count += 1
        upload_community_thumbnail(file[0],file[1])

        print("thumbnail uploaded for community=", file[0])
        print("\n")
        if count == 200:
            count=0
            print("\n Process sleep for 5 sec")
            time.sleep(5)


    print("Communities Image migration end time=", (time.time() - start_time))

start_time=time.time()


upload_all_community_thumbnail()
end_time=time.time()

print("Overall Time of execution=",(end_time-start_time))