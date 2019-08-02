import pyrebase
from django.conf import settings

FIREBASE_CONFIG = {
    'apiKey': "AIzaSyCmu_u-n31x2WMQlWAciP5RDXGn2qMuXrg",
    'authDomain': "collabmates-3d601.firebaseapp.com",
    'databaseURL': "https://collabmates-3d601.firebaseio.com",
    'projectId': "collabmates-3d601",
    'storageBucket': "collabmates-3d601.appspot.com",
    'messagingSenderId': "645716458793",
    'appId': "1:645716458793:web:779debf3286d6049"
  };

firebaseConfig=FIREBASE_CONFIG
print(firebaseConfig)
firebase = pyrebase.initialize_app(firebaseConfig)

database=firebase.database()


def update_last_answer_id(card_id,answer_id):

    '''function to update last answer id when a new answer is posted'''

    card_id=str(card_id)
    data={
        'answer_id':str(answer_id)
    }

    database.child("collabcards").child(card_id).child("collabcard").update(data)

    print('Data Updated successfully in firebase')


update_last_answer_id(197,12)