import pyrebase
from django.conf import settings

firebaseConfig=settings.FIREBASE_CONFIG

firebase = pyrebase.initialize_app(firebaseConfig)

database=firebase.database()


def update_last_answer_id(card_id,answer_id):

    '''function to update last answer id when a new answer is posted'''

    card_id=str(card_id)
    data={
        'answer_id':str(answer_id)
    }

    database.child("collabcards").child(card_id).update(data)

    print('Data Updated successfully in firebase')


