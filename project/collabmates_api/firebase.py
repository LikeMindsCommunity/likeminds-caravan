import pyrebase
from django.conf import settings

url=settings.URL

if url == 'https://beta.collabmates.com':
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



def update_last_answer_id(card_id,answer_id):

    '''function to update last answer id when a new answer is posted'''

    card_id=str(card_id)
    data={
        'answer_id':str(answer_id)
    }

    if url == 'https://beta.collabmates.com':
        database.child("beta_collabcards").child(card_id).child("collabcard").update(data)
    else:
        database.child("collabcards").child(card_id).child("collabcard").update(data)

    print('Data Updated successfully in firebase')


