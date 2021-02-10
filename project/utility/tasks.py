from __future__ import absolute_import, unicode_literals

from celery import shared_task
# from collabmates_api.notification import notification_to_complete_onboarding
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from togther.models import *
from PIL import Image, ImageDraw, ImageFont
from utility.firebase import upload_user_initial_image
import os
from .utils import *
import random
import requests
from threading import Timer
from urllib.request import urlopen

is_beta = settings.IS_BETA
url = settings.URL



def mail_triger(member_id, request):
    print('member_id === ', member_id)

    android = is_request_android(request)
    ios = is_request_ios(request)
    pc = is_request_pc(request)

    t = Timer(600.0, onboarding_mail_for_new_users, [member_id, android, ios, pc])
    t.start()


@shared_task
def send_email(subject, template, to_mails_list, categories=None):

    fail_silently = False
    msg = EmailMultiAlternatives(subject,
                                 template,
                                 "LikeMinds<hello@likeminds.community>",
                                 to_mails_list, )
    msg.attach_alternative(template, "text/html")

    if categories is not None:
        categories.append("beta" if settings.IS_BETA else "prod")
        msg.categories = categories
        
    msg.send(fail_silently)
    return


@shared_task
def onboarding_mail_for_new_users(member_id, android, ios, pc):
    print('member_id ===>>>> ', member_id)

    user = User.objects.get(pk=member_id)

    # if user does not have any tags , user has to do on-boarding
    if user_onbaord_new(user):
        ''' if user comes back in the middle of on-baording flow,
        make sure he continues the on-boarding'''
        return
    else:
        # fail_silently=True
        if user.email:

            if user.userinfo.fcm_token and not pc:
                link = url
            elif user.userinfo.fcm_token and pc:
                link = url + "/newpage"
            elif pc:
                link = url + "/signup"
            else:
                if android:
                    link = android_app_download_link
                elif ios:
                    link = ios_app_download_link
                else:
                    link = url + "/onboarding"
            to = user.email
            subject = "Thanks for joining CollabMates! Here's the next step"
            template = get_template("mails/onboarding_mail.html").render({"name": user.userinfo.name,
                                                                          'subject': subject, 'url': link,
                                                                          })
            to = [to]
            # send_email(subject, template, to)
            # notification_to_complete_onboarding(member_id)  # notification to complete onboarding
            return


@shared_task
def new_member_request(member_id, community_id, form_response, ref_id=None, ph_no=None ):
    # time.sleep(5)
    member = User.objects.get(pk=member_id)
    if ref_id:
        ref_person = User.objects.get(pk=ref_id)
        ref_name = ref_person.userinfo.name
    else:
        ref_name = ''

    community = Community.objects.get(pk=community_id)
    community_name = community.name

    member_name = member.userinfo.name
    fail_silently = True
    community_link = url + "/community/" + str(community_id)
    subject = "New Member Request in Community " + str(community_name)

    if ph_no:
        text = str(member_name) + ' has requsted collabmates to verify his account to join' + str(
                community_name)+'\nUser has submitted his contact number  : ' + str(ph_no)

    elif not ref_id:
        if community.hide_community == '3':

            text = str(member_name) + ' has shown interest in ' + str(
                community_name) + ' community and is not referred by anyone'
        elif community.hide_community == '0' or community.hide_community == '1' or community.hide_community == '4':
            if community.hide_community == '1':
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community (Hidden) and is not referred by anyone'
            else:
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community and is not referred by anyone'
        else:
            text = str(member_name) + ' has request to join ' + str(
                community_name) + ' community and is not referred by anyone'

    else:
        if community.hide_community == '3':

            text = str(member_name) + ' has shown interest in ' + str(
                community_name) + ' community and is referred by ' + str(ref_name)
        elif community.hide_community == '0' or community.hide_community == '1' or community.hide_community == '4':
            if community.hide_community == '1':
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community (Hidden) and is referred by ' + str(ref_name)
            else:
                text = str(member_name) + ' has request to join ' + str(
                    community_name) + ' community and is referred by ' + str(ref_name)
        else:
            text = str(member_name) + ' has request to join ' + str(
                community_name) + ' community and is referred by ' + str(ref_name)

    res = {}

    responses = communityAnswers.objects.filter(community=community_id).filter(member=member_id).order_by('id')
    if responses.exists():
        for response in responses:
            res[response.question_title] = response.question_answer

    community_state = community.hide_community

    is_IG = is_IG_community(community)

    template = get_template("mails/new_member_request.html").render(
        {"member_name": member_name, "member_id": member_id, 'ref_name': ref_name,
         'subject': subject, 'community_name': community_name, 'community_id': community_id,
         'text': text, 'community_link': community_link, "community_state": community_state,
         'result': res, 'url': url, 'is_IG':is_IG })

    if is_beta:
        to_list = ['mahesh@likeminds.community']

    elif not is_beta:
        to_list = ['nipun@likeminds.community', 'harsh@likeminds.community']
    else:
        to_list = ['mahesh@likeminds.community']
    # msg = EmailMultiAlternatives(subject,
    #                              template,
    #                              "Collabmates<hello@collabmates.com>",
    #
    #                              to_list,
    #                              )
    #
    # msg.attach_alternative(template, "text/html")
    # return msg.send(fail_silently)
    send_email(subject, template, to_list)


@shared_task
def member_request_approval_or_denied(user_id, community_id, approved):
    user = User.objects.get(pk=user_id)
    community = Community.objects.get(pk=community_id)

    to = user.email
    if approved:
        subject = "Congrats! You are now part of " + community.name + " community."
    else:
        subject = "Sorry! Your request to join " + community.name + " has been rejected."

    link_text = ''
    url = settings.URL
    if user.userinfo.fcm_token:
        if approved:
            url = url + "/community/" + str(community_id)
            link_text = 'Start Engaging'
        else:
            link_text = 'Explore Communties'
    else:
        url = url + "/download_the_app"
        link_text = 'Start Engaging'

    template = get_template("mails/member_approval_or_declined.html").render(
        {"user_name": user.userinfo.name,
         'community_name': community.name,
         'purpose': community.purpose,
         'subject': subject, 'url': url,
         'link_text': link_text,
         'approved': approved
         })
    to = [to]
    send_email(subject, template, to)
    return


@shared_task
def send_mail_for_report_abuse(user_name, collabcard_message, report_tag, community_name, community_url,
                                              reported_user_name=None, report_reason=None):
    '''function to send a mail when the user report abuse on collabcard'''

    subject = str(user_name) + " reported " + report_tag

    help_text = " for collabcard: " if not reported_user_name else " for user: "
    reported_on = str(collabcard_message) if not reported_user_name else str(
            reported_user_name)
    if report_reason:
        text = str(user_name) + " reported " + str(report_tag) +\
               help_text + reported_on + " in community " + str(community_name) +\
               ". The feedback given By user is " + str(report_reason)
    else:
        text = str(user_name) + " reported " + str(report_tag) + help_text + str(
            collabcard_message) + " in community " + str(community_name)
    context = {
        'subject': subject,
        'text': text,
        'community_link': community_url
    }
    template = get_template("mails/report_abuse.html").render(context)
    if not is_beta:
        to = ["nipun@likeminds.community"]
    else:
        to = ["nipun@likeminds.community", "mahesh@likeminds.community"]
    to = to
    send_email(subject, template, to)
    print("Executed")


def send_mail_for_query_and_feedback(mail_dict):

    '''function to send the mail to collabmates regarding a query or feedback'''

    subject="New Collabcard Posted in Collabmates Queries and Feedback Community"
    context=mail_dict
    template = get_template("mails/community_feedback.html").render(context)
    if not is_beta:
        to_list = ['nipungoyal.iitd@gmail.com', 'hrshshukl@gmail.com']
    else:
        to_list = ['rastogi.fresh88@gmail.com']

    send_email(subject, template, to_list)


@shared_task
def save_name_initial_image(user_id, user_name):

    colour_codes = ["#2196F3", "#03A9F4", "#fdbd39", "#F44336", "#9C27B0", "#FFEB3B", "#d0021b", "#28d0021b"]
    chosen_color = random.randint(0, len(colour_codes)-1)
    width, length = 216, 216

    name_initial = user_name[0]
    font = ImageFont.truetype("static/fonts/Roboto-Medium.ttf", 140, encoding="unic")

    canvas = Image.new(mode='RGBA', size=(width, length), color=colour_codes[chosen_color])
    draw = ImageDraw.Draw(canvas)
    text_width, text_height = draw.textsize(name_initial, font=font)

    draw.text(((width - text_width) / 2, (length - text_height) / 2 - 20), name_initial, 'white', font)

    # cropping into circular image
    big_size = (canvas.size[0] * 2, canvas.size[1] * 2)
    mask = Image.new('L', big_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + big_size, fill=255)
    mask = mask.resize(canvas.size, Image.ANTIALIAS)
    canvas.putalpha(mask)

    image_name = f"media/media/user_profile/{user_id}_profile_image.png"
    canvas.save(image_name, "PNG")
    # canvas.show()

    local_image_url = url + "/" + image_name

    image_url = upload_user_initial_image(user_id, image=local_image_url, url=True)

    if image_url:
        user_info = Userinfo.objects.get(user_id=user_id)
        user_info.image_link = image_url
        user_info.save()

    os.remove(image_name)


# mail_dict={}
# mail_dict['user_name'] = "Mahesh Royals"
# mail_dict['email'] = "test@gmail.com"
# mail_dict['collabcard_link'] ="www.google.com"
# mail_dict['content'] = "What is this about I don't know anything about it and I don't want to know either"
# mail_dict['collabcard_id'] = 181

#send_mail_for_query_and_feedback(mail_dict)