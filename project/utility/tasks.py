from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.template.loader import get_template
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from togther.models import *
from django.conf import settings
from togther.models import *


url  = settings.URL



from threading import Timer

def mail_triger(member_id):
    print('member_id === ',member_id)

    t = Timer(300.0, onboarding_mail_for_new_users,[member_id])
    t.start()


def send_email(subject,template,to):
    fail_silently=True
    msg = EmailMultiAlternatives(subject,
                                template,
                                "Collabmates<hello@collabmates.com>",
                                [to],)
    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)


@shared_task
def onboarding_mail_for_new_users(member_id):
    print('member_id === ',member_id)

    user = User.objects.get(pk = member_id)
    user_legacy = User_Legacy.objects.filter(user_id=user)
    user_prof = User_Profession.objects.filter(user_id=user)
    user_int = User_Interest.objects.filter(user_id=user)
    user_gro = User_Geography.objects.filter(user_id=user)

    # if user does not have any tags , user has to do on-boarding
    if user_legacy.exists() and user_prof.exists() and user_int.exists() and user_gro.exists():

        ''' if user comes back in the middle of on-baording flow,
        make sure he continues the on-boarding'''
        return
    else:
        fail_silently=True
        if user.email:
            to = user.email
            subject="Thanks for joining CollabMates! Here's the next step"
            template = get_template("mails/onboarding_mail.html").render({"name":user.userinfo.name,
                                                                          'subject':subject,'url':url,
                                                                          })
            # msg = EmailMultiAlternatives(subject,
            #                                  template,
            #                                  "Collabmates<hello@collabmates.com>",
            #                                  [to],
            #                                  )
            # msg.attach_alternative(template, "text/html")
            # return msg.send(fail_silently)
            send_email(subject, template, to)


@shared_task
def new_user(member_id):
    pass


@shared_task
def new_member_request(member_id,commuinity_id,ref_id=None):


    member = User.objects.get(pk=member_id)
    if ref_id:
        ref_person = User.objects.get(pk=ref_id)
        ref_name = ref_person.userinfo.name
    else:
        ref_name = ''

    commuinity = Community.objects.get(pk=commuinity_id )
    commuinity_name = commuinity.name

    member_name = member.userinfo.name
    fail_silently = True
    community_link=url+"/community/"+str(commuinity_id)
    subject = "New Member Request in Community "+ str(commuinity_name)
    if not ref_id:
        if commuinity.hide_community == '3':

            text = str(member_name)+ ' has shown interest in '+str(commuinity_name) + ' community and is not referred by anyone'
        elif commuinity.hide_community == '0' or commuinity.hide_community == '1' or commuinity.hide_community == '4':
            if commuinity.hide_community == '1':
                text = str(member_name)+ ' has request to join '+str(commuinity_name) + ' community (Hidden) and is not referred by anyone'
            else:
                text = str(member_name)+ ' has request to join '+str(commuinity_name) + ' community and is not referred by anyone'
        else:
            text = str(member_name) + ' has request to join ' + str(commuinity_name) + ' community and is not referred by anyone'

    else:
        if commuinity.hide_community == '3':

            text = str(member_name) + ' has shown interest in ' + str(
                commuinity_name) + ' community and is referred by ' + str(ref_name)
        elif commuinity.hide_community == '0' or commuinity.hide_community == '1' or commuinity.hide_community == '4':
            if commuinity.hide_community == '1':
                text = str(member_name) + ' has request to join ' + str(
                    commuinity_name) + ' community (Hidden) and is referred by ' + str(ref_name)
            else:
                text = str(member_name) + ' has request to join ' + str(
                    commuinity_name) + ' community and is referred by ' + str(ref_name)
        else:
            text = str(member_name) + ' has request to join ' + str(
                commuinity_name) + ' community and is referred by ' + str(ref_name)

    template = get_template("mails/new_member_request.html").render({"member_name": member_name,'ref_name':ref_name,
                                                                  'subject': subject, 'commuinity_name': commuinity_name,
                                                                  'text':text,'community_link':community_link})
    
    if url == "https://beta.collabmates.com":
        to_list = ['mahesh61437mahe@gmail.com']
    elif url == "https://www.collabmates.com":
        to_list = ['nipungoyal.iitd@gmail.com','hrshshukl@gmail.com']
    else:
        to_list = ['mahesh61437mahe@gmail.com']
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "Collabmates<hello@collabmates.com>",

                                 to_list,
                                 )

    msg.attach_alternative(template, "text/html")
    return msg.send(fail_silently)

    # send_email(subject, template, to=to_list)



