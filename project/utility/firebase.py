from __future__ import absolute_import, unicode_literals
from celery import shared_task
import pyrebase
from django.conf import settings
import requests
import time
from urllib.request import urlopen
import os
from PIL import Image
from io import BytesIO

from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import Community, Tags_lpig
import json
from django.http.response import JsonResponse

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

firebaseConfig = FIREBASE_CONFIG
firebase = pyrebase.initialize_app(firebaseConfig)
database = firebase.database()
storage = firebase.storage()

error_logger = LoggingWrapper.get_instance()


def update_last_answer_id(card_id, answer_id):
    """function to update last answer id when a new answer is posted"""

    try:
        card_id = str(card_id)
        data = {
            'answer_id': str(answer_id)
        }

        database.child("collabcards").child(card_id).child("collabcard").update(data)

    except Exception as e:
        error_logger.error(e)


def upload_image_to_firebase(image_url, user_id):
    try:
        image_data = requests.get(image_url).content
        user_id = str(user_id)
        storage.child("files").child("profile").child(user_id).put(image_data)
        image_url = storage.child("files").child("profile").child(user_id).get_url(None)

        return image_url

    except Exception as e:
        error_logger.error(e)

        return None


def is_url_image_valid(image_url):
    '''function to check whether the image url is valid or not'''

    image_formats = ("image/png", "image/jpeg", "image/jpg")
    r = requests.head(image_url)
    if r.headers["content-type"] in image_formats:
        return True
    return False


def upload_tag_files(tag_id, image, url=False):
    '''function to put tags images in firebase'''
    name = "img_tag_" + str(tag_id)
    if url:
        image_url = image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            tag_id = str(tag_id)
            storage.child("files").child("tag").child(tag_id).child(name).put(image_data)
            image_url = storage.child("files").child("tag").child(tag_id).child(name).get_url(None)
            return image_url
        else:
            print("Image url is broken for tag=", tag_id)
            return ''
    else:
        tag_id = str(tag_id)
        storage.child("files").child("tag").child(tag_id).child(name).put(image)
        image_url = storage.child("files").child("tag").child(tag_id).child(name).get_url(None)
        return image_url


def upload_user_files(user_id, image, url=False):
    '''function to put tags images in firebase'''
    name = "img_user_" + str(user_id)
    if url:
        image_url = image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            user_id = str(user_id)
            storage.child("files").child("user").child(user_id).child(name).put(image_data)
            image_url = storage.child("files").child("user").child(user_id).child(name).get_url(None)
            return image_url
        else:
            print("Image url is broken for user=", user_id)
            return ''
    else:
        user_id = str(user_id)
        storage.child("files").child("user").child(user_id).child(name).put(image)
        image_url = storage.child("files").child("user").child(user_id).child(name).get_url(None)
        return image_url


def upload_community_files(community_id, image, url=False):
    '''function to put tags images in firebase'''
    name = "img_community_" + str(community_id)
    if url:
        image_url = image
        try:
            response = urlopen(image_url)
            image_data = response.read()
        except Exception as e:
            print(e)
            return
        community_id = str(community_id)
        storage.child("files").child("community").child(community_id).child(name).put(image_data)
        time.sleep(1)
        image_url = storage.child("files").child("community").child(community_id).child(name).get_url(None)
        return image_url

    else:
        community_id = str(community_id)
        try:
            time.sleep(.200)
            storage.child("files").child("community").child(community_id).child(name).put(image)
            time.sleep(.200)
            image_url = storage.child("files").child("community").child(community_id).child(name).get_url(None)
            return image_url
        except Exception as e:
            print(e)
            return None


@shared_task
def upload_community_thumbnail(community_id, image_url):
    name = "img_community_thumbnail__" + str(community_id)

    try:
        response = urlopen(image_url)
    except Exception as e:
        print(e)
        return
    img = BytesIO(response.read())
    img = Image.open(img).convert('RGB')
    image = img.resize((200, 200), Image.ANTIALIAS)
    file_name = name + ".jpeg"
    image.save(file_name)

    community_id = str(community_id)
    community = Community.objects.get(id=community_id)
    try:
        time.sleep(.200)
        storage.child("files").child("community").child(community_id).child(name).put(file_name)
        time.sleep(.200)
        image_url = storage.child("files").child("community").child(community_id).child(name).get_url(None)
        print(image_url)
        community.thumbnail = image_url
        community.save()
    except Exception as e:
        print(e)
        return None
    finally:
        os.remove(file_name)


@shared_task
def upload_tag_thumbnail(tag_id, image_url):
    name = "img_tag_thumbnail__" + str(tag_id)

    try:
        response = urlopen(image_url)
    except Exception as e:
        print(e)
        return
    img = BytesIO(response.read())
    img = Image.open(img).convert('RGB')
    image = img.resize((200, 200), Image.ANTIALIAS)
    file_name = name + ".jpeg"
    image.save(file_name)

    tag_id = str(tag_id)
    tag = Tags_lpig.objects.get(id=tag_id)
    try:
        time.sleep(.200)
        storage.child("files").child("tag").child(tag_id).child(name).put(file_name)
        time.sleep(.200)
        image_url = storage.child("files").child("tag").child(tag_id).child(name).get_url(None)
        print(image_url)
        tag.thumbnail = image_url
        tag.updated_at = time.time()
        tag.save()
    except Exception as e:
        print(e)
        return None
    finally:
        os.remove(file_name)


def upload_main_website_images_to_firebase(file):
    '''saving main website images in firebase'''

    name = "third_section"
    storage.child("files").child("main_website").child(name).put(file)
    time.sleep(.200)

    image_url = storage.child("files").child("main_website").child(name).get_url(None)

    print(image_url)


def upload_question_files(request=None, community_id=None, question_id=None, member_id=None, image=None, url=False):
    '''function to put tags images in firebase'''
    # / community / < community_id > / question / < question_id > / < member_id >
    name = "img_tag_" + str(question_id)
    question_id = str(question_id)
    community_id = str(community_id)
    member_id = str(member_id)
    if url:
        image_url = image
        if is_url_image_valid(image_url):
            image_data = requests.get(image_url).content
            storage.child("files").child("community").child(community_id).child("question").child(question_id).child(
                member_id).child(name).put(image_data)
            image_url = storage.child("files").child("question").child(question_id).child(name).get_url(None)
            return image_url
        else:
            print("Image url is broken for tag=", question_id)
            return ''
    elif image:
        storage.child("files").child("question").child(question_id).child(name).put(image)
        image_url = storage.child("files").child("question").child(question_id).child(name).get_url(None)
        return image_url
    elif request.method == 'POST':
        files = request.FILES.getlist('file')
        member_id = str(request.user.id)
        name = "img_tag_" + str(question_id)
        image_data = files[0]

        storage.child("files").child("community").child(community_id).child("question").child(question_id).child(
            member_id).child(name).put(image_data)
        image_url = storage.child("files").child("community").child(community_id).child("question").child(
            question_id).child(
            member_id).child(name).get_url(None)

        return JsonResponse({"success": True, "image_url": image_url})


def update_my_chatrooms_on_homefeed_in_firebase(chatroom_id, user_id, conversation_id=""):

    try:
        data = {
            'chatroom_id': str(chatroom_id),
            'conversation_id': conversation_id
        }

        database.child("users").child(user_id).update(data)

    except Exception as e:
        error_logger.error(e)


def update_my_chatrooms_on_homefeed_in_firebase_for_users_list(chatroom_id, users_list, conversation_id=""):

    try:
        data = {
            'chatroom_id': str(chatroom_id),
            'conversation_id': conversation_id
        }

        data = {'users/{}/'.format(user_id): data for user_id in users_list}
        database.update(data)

    except Exception as e:
        error_logger.error(e)


def update_chatroom_conversation_ids_against_community(community_id, card_id, conversation_id):
    """function to update last conversation id when a new answer is posted"""

    if not community_id:
        return

    try:
        data = {
            'conversation_id': str(conversation_id),
            'chatroom_id': str(card_id)
        }

        database.child("community").child(community_id).update(data)

    except Exception as e:
        error_logger.error(e)
