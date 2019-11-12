import pyrebase
from django.conf import settings
import requests


if settings.IS_BETA:
    # beta firebase config
    FIREBASE_CONFIG = {
        'apiKey': "AIzaSyBWjDQEiYKdQbQNvoiVvvOn_cbufQzvWuo",
        'authDomain': "collabmates-beta.firebaseapp.com",
        'databaseURL': "https://collabmates-beta.firebaseio.com",
        'projectId': "collabmates-beta",
        'storageBucket': "collabmates-beta.appspot.com",
        'messagingSenderId': "983690302378",
        'appId': "1:983690302378:web:b2fa2c58f2351d5c1b91d3",
        'measurementId': "G-R2PXYC9F4S"
    }

else:

    # production firebase config
    FIREBASE_CONFIG = {
        'apiKey': "AIzaSyCmu_u-n31x2WMQlWAciP5RDXGn2qMuXrg",
        'authDomain': "collabmates-3d601.firebaseapp.com",
        'databaseURL': "https://collabmates-3d601.firebaseio.com",
        'projectId': "collabmates-3d601",
        'storageBucket': "collabmates-3d601.appspot.com",
        'messagingSenderId': "645716458793",
        'appId': "1:645716458793:web:779debf3286d6049"
      }

firebaseConfig=FIREBASE_CONFIG
firebase = pyrebase.initialize_app(firebaseConfig)
database=firebase.database()
storage = firebase.storage()


def update_last_answer_id(card_id,answer_id):

    '''function to update last answer id when a new answer is posted'''

    card_id=str(card_id)
    data={
        'answer_id':str(answer_id)
    }

    if settings.IS_BETA:
        database.child("beta_collabcards").child(card_id).child("collabcard").update(data)
    else:
        database.child("collabcards").child(card_id).child("collabcard").update(data)

    print('Data Updated successfully in firebase')




def upload_image_to_firebase(image_url,user_id):

    image_data = requests.get(image_url).content
    user_id=str(user_id)
    storage.child("files").child("Users").child(user_id).put(image_data)
    image_url=storage.child("files").child("Users").child(user_id).get_url(None)
    return image_url



def is_url_image_valid(image_url):

   '''function to check whether the image url is valid or not'''

   image_formats = ("image/png", "image/jpeg", "image/jpg")
   r = requests.head(image_url)
   if r.headers["content-type"] in image_formats:
      return True
   return False


def upload_files_to_firebase(image_url,user_id):

    '''function to update files to firebase'''

    if is_url_image_valid(image_url):
        image_data = requests.get(image_url).content
        user_id = str(user_id)
        storage.child("files").child("Users").child(user_id).put(image_data)
        image_url = storage.child("files").child("Users").child(user_id).get_url(None)
        return image_url
    else:
        print("Image url is broken for user=",user_id)
        return None


def upload_tag_files(tag_id,image,url=False):

    '''function to put tags images in firebase'''

    if url:
        image_url=image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            tag_id = str(tag_id)
            storage.child("files").child("Tags").child(tag_id).put(image_data)
            image_url = storage.child("files").child("Tags").child(tag_id).get_url(None)
            return image_url
        else:
            print("Image url is broken for tag=", tag_id)
            return ''
    else:
        tag_id=str(tag_id)
        storage.child("files").child("Tags").child(tag_id).put(image)
        image_url = storage.child("files").child("Tags").child(tag_id).get_url(None)
        return image_url


def upload_user_files(user_id,image,url=False):

    '''function to put tags images in firebase'''

    if url:
        image_url=image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            user_id = str(user_id)
            storage.child("files").child("Users").child(user_id).put(image_data)
            image_url = storage.child("files").child("Users").child(user_id).get_url(None)
            return image_url
        else:
            print("Image url is broken for tag=", user_id)
            return ''
    else:
        user_id=str(user_id)
        storage.child("files").child("Users").child(user_id).put(image)
        image_url = storage.child("files").child("Users").child(user_id).get_url(None)
        return image_url


def upload_community_files(community_id,image,url=False):

    '''function to put tags images in firebase'''

    if url:
        image_url=image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            community_id = str(community_id)
            storage.child("files").child("Communities").child(community_id).put(image_data)
            image_url = storage.child("files").child("Communities").child(community_id).get_url(None)
            return image_url
        else:
            print("Image url is broken for tag=", community_id)
            return ''
    else:
        community_id=str(community_id)
        storage.child("files").child("Communities").child(community_id).put(image)
        image_url = storage.child("files").child("Communities").child(community_id).get_url(None)
        return image_url


