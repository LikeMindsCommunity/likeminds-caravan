from togther.models import *
import requests as rqst
import json
import time
from .tasks import *


def update_userinfo(backend, user, response, *args, **kwargs):
    ''' update user info of user as soon as user registers '''

    userinfo = Userinfo.objects.filter(user_id=user)
    if not userinfo.exists():
        if backend.name == 'facebook':
            url = "https://graph.facebook.com/v2.9/" + response[
                'id'] + "?fields=name,email,gender,location,picture,link&access_token=" + response['access_token']
            resp = rqst.get(url)
            data = json.loads(resp.text)
            image_url = "http://graph.facebook.com/" + response[
                'id'] + "/picture?width=400&height=400"
            usr = User.objects.get(pk=user.id)
            if not usr.email:
                usr.email = data['email']
                usr.save()
            try:
                user = Userinfo.objects.get(user_id=usr)
            except:
                user = Userinfo()
                if 'name' in data:
                    user.name = data['name']
                if 'email' in data:
                    user.email = data['email']
                if 'location' in data:
                    user.city = data['location']['name']
                user.image_url = image_url
                user.created_at = time.time()
                user.login_type = 'facebook'
                user.login_json = data
                user.user_id = usr
                user.save()
                mail_triger(str(usr.id))

        if backend.name == 'linkedin-oauth2':
            # accessing Linked In API to get user basic information
            url = 'https://api.linkedin.com/v2/me?projection=(id,firstName,emailAddress,lastName,vanityName,headline,interests,location,picture-url,name,profilePicture(displayImage~:playableStreams))&oauth2_access_token=' + \
                  response['access_token']
            email_url = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))&oauth2_access_token=' + \
                        response['access_token']
            resp = rqst.get(url)
            # getting public details of user from Linked In
            data_main = json.loads(resp.text)
            resp = rqst.get(email_url)
            email_data = json.loads(resp.text)
            # getting specific details from received Json
            user_name = data_main['firstName']['localized']['en_US'] + " " + data_main['lastName']['localized'][
                'en_US']
            profile_picture = data_main['profilePicture']['displayImage~']['elements'][2]['identifiers'][0][
                'identifier']
            email = email_data['elements'][0]['handle~']['emailAddress']
            usr = User.objects.get(pk=user.id)
            if not usr.email:
                usr.email = email
                usr.save()
            # checking if there is any user having details with the email we got from linkedIn
            userinfo = Userinfo.objects.filter(email=email)
            if not userinfo:
                # if there is no user having th email , create a user info for the user
                user = Userinfo()
                user.name = user_name
                user.email = email
                user.image_url = profile_picture
                # info.linkedin_link = data['publicProfileUrl']
                user.created_at = time.time()
                user.login_type = 'linkedIn'
                user.login_json = [data_main, email_data]
                user.user_id = usr
                user.save()
                mail_triger(str(usr.id))






