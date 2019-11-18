import time

import psycopg2
from collabmates_api.notification import get_connection
from django.conf import settings
from utility.firebase import upload_user_files, upload_community_files, upload_tag_files

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
        image_url=upload_user_files(file[0],file[1],url=True)
        print(image_url)
        update_image_link_for_user(image_url,file[0])
        print("file uploaded for user=",file[0])
        print("\n")
        if count == 200:
            count=0
            print("\n for every 200 sleeping 10 sec \n")
            time.sleep(10)


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
        sql = """select id,image_url from togther_community where image_url!='' order by id desc"""
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
        if file[0] > 8300:
            continue
        # image_url = upload_community_files(file[0], file[1],url=True)
        # print(image_url)
        # update_image_link_for_community(image_url, file[0])
        # print("file uploaded for community=", file[0])
        # print("\n")
        #
        # if count == 200:
        #     count=0
        #     print("\n for every 200 sleeping 10 sec \n")
        #     time.sleep(10)
        file_path=settings.MEDIA_ROOT+"/"+str(file[1])
        try:
            with open(file_path, "rb") as image:
                image_url = upload_community_files(file[0], image, url=False)
        except FileNotFoundError as e:
            print(e)
            image = url + "/media/media/community/default.jpeg"
            image_url=upload_community_files(file[0],image,url=True)

        if image_url:
            update_image_link_for_community(image_url, file[0])
        else:
            image = url + "/media/media/community/default.jpeg"
            image_url = upload_community_files(file[0], image, url=True)
            update_image_link_for_community(image_url, file[0])

        print("file uploaded for community=", file[0])
        print("\n")
        if count == 200:
            count=0
            print("\n Process sleep for 5 sec")
            time.sleep(5)


    print("Communities Image migration end time=", (time.time() - start_time))



# tags image firebase migration functions

def get_all_tags_images():

    '''function to get community images for firebase migration'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        #link = str(url) + "/media/"
        sql = """select id,tag_image from togther_tags_lpig where tag_image!='' order by id desc"""
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
        # image_url = upload_tag_files(file[0], file[1],url=False)
        # print(image_url)
        # update_image_link_for_tags(image_url, file[0])
        # print("file uploaded for tag=", file[0])
        # print("\n")
        #
        # if count == 200:
        #     count=0
        #     print("\n for every 200 sleeping 10 sec \n")
        #     time.sleep(10)

        file_path = settings.MEDIA_ROOT + "/" + str(file[1])
        try:
            with open(file_path, "rb") as image:
                image_url = upload_tag_files(file[0], image, url=False)
                update_image_link_for_tags(image_url, file[0])

        except FileNotFoundError as e:
            print(e)


        print("file uploaded for tags=", file[0])
        print("\n")
        if count == 200:
            count = 0
            print("\n Process sleep for 5 sec")
            time.sleep(5)



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
upload_all_tag_images_to_firebase
print("\n")
upload_all_communities_images_to_firebase()

end_time=time.time()

print("Overall Time of execution=",(end_time-start_time))

