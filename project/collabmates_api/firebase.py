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

