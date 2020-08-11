
from togther.models import Userinfo,userEmails,User
import time
import json


def get_user_emails():

    email_filter = Userinfo.objects.all()

    email_list = []

    for user in email_filter:

        temp = {}
        temp['email'] = user.email
        temp['user_id'] = user.user_id.id

        if temp['email']:
            email_list.append(temp)


    return email_list


def set_user_emails():

    email_list = get_user_emails()

    for data in email_list:

        email_filter = userEmails.objects.filter(user_id=data['user_id'])
        user_instance = User.objects.get(id=data['user_id'])
        if not email_filter.exists():
            instance = userEmails()
            instance.email = data['email']
            instance.user = user_instance
            instance.email_state = 1
            instance.created_at = time.time()
            instance.verified = True
            instance.save()
            print(data['email']+"saved")
        else:
            print("hello")



start_time = time.time()

set_user_emails()

end_time = time.time()

diff = end_time - start_time

print(diff)