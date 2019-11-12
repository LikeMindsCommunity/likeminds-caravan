# file to migrate existing files in media folder to firebase

from collabmates_api.notification import get_connection
import  psycopg2
from django.conf import  settings
from utility.firebase import upload_files_to_firebase,upload_community_files,upload_tag_files
import time
url=settings.URL


# user image_firebase_migrations
def get_all_users_images():

    '''function to get all user images urls'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        link=str(url)+"/media/"
        sql = """select user_id_id,concat('%s',image_file) from togther_userinfo where image_file!='' order by id desc """%(link)
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        connection.close()
        if res:
            return res
        else:
            return []
    except(Exception, psycopg2.error) as error:
        print("Error", error)


def upload_all_user_images_to_firebase():

    '''function to migrate user images to firebase'''

    start_time=time.time()
    print("User Image migration start time=",start_time)
    files=get_all_users_images()

    count = 0
    for file in files:
        count+=1
        image_url=upload_files_to_firebase(file[1],file[0])
        print(image_url)
        update_image_link_for_user(image_url,file[0])
        print("file uploaded for user=",file[0])
        print("\n")
        if count == 100:
            count=0
            print("\n sleeping for 30 sec \n")
            time.sleep(30)


    print("User Image migration end_time=",(time.time()-start_time))


def update_image_link_for_user(image_link,user_id):
    '''function to update image links for user'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "update togther_userinfo set image_link=%s where user_id_id=%s"
        parameter_list = [image_link, user_id]
        curr.execute(sql, parameter_list)
        curr.close()
        connection.commit()
        connection.close()
        print('Image link updated Successfully for user=',user_id)
    except(Exception, psycopg2.error) as error:
        print("Error", error)


#upload_all_user_images_firebase()



# communities image firebase migrations functions

def get_all_community_images():

    '''function to get community images for firebase migration'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        link = str(url) + "/media/"
        sql = """select id,concat('%s',image_url) from togther_community where image_url!='' order by id desc""" % (link)
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


def update_image_link_for_community(image_link,community_id):
    '''function to update image links for user'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "update togther_community set image_link=%s where id=%s"
        parameter_list = [image_link, community_id]
        curr.execute(sql, parameter_list)
        curr.close()
        connection.commit()
        connection.close()
        print('Image link updated Successfully for community=',community_id)
    except(Exception, psycopg2.error) as error:
        print("Error", error)


def upload_all_communities_images_to_firebase():

    '''function to migrate user images to firebase'''

    start_time = time.time()
    files = get_all_community_images()

    count = 0
    for file in files:
        count += 1
        image_url = upload_community_files(file[0], file[1])
        print(image_url)
        update_image_link_for_community(image_url, file[0])
        print("file uploaded for community=", file[0])
        print("\n")

        if count == 100:
            count=0
            print("\n sleeping for 30 sec \n")

            time.sleep(30)



    print("Communities Image migration end time=", (time.time() - start_time))



# tags image firebase migration functions

def get_all_tags_images():

    '''function to get community images for firebase migration'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        link = str(url) + "/media/"
        sql = """select id,concat('%s',tag_image) from togther_tags_lpig where tag_image!='' order by id desc""" % (link)
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


def upload_all_tag_images_to_firebase():

    '''function to migrate user images to firebase'''

    start_time = time.time()
    files = get_all_tags_images()

    count = 0
    for file in files:
        count += 1
        image_url = upload_tag_files(file[0], file[1],True)
        print(image_url)
        update_image_link_for_tags(image_url, file[0])
        print("file uploaded for tag=", file[0])
        print("\n")

        if count == 100:
            count=0
            print("\n sleeping for 30 sec \n")

            time.sleep(30)



    print("Tags Image migration end time=", (time.time() - start_time))

def update_image_link_for_tags(image_link,tag_id):

    '''function to update image links for user'''

    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "update togther_tags_lpig set image_link=%s where id=%s"
        parameter_list = [image_link, tag_id]
        curr.execute(sql, parameter_list)
        curr.close()
        connection.commit()
        connection.close()
        print('Image link updated Successfully for tag=',tag_id)
    except(Exception, psycopg2.error) as error:
        print("Error", error)




# migrating image files from server to firebase




start_time=time.time()

upload_all_user_images_to_firebase()
print("\n")
upload_all_communities_images_to_firebase()
print("\n")
upload_all_tag_images_to_firebase()

end_time=time.time()

print("Overall Time of execution=",(end_time-start_time))



