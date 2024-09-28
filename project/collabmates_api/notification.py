from __future__ import absolute_import, unicode_literals
from external_services.logging.logging_wrapper import LoggingWrapper
from celery import shared_task
import re
import time
from dateutil import tz
import pytz
from django.http.response import JsonResponse
import psycopg2
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, F
from pyfcm import FCMNotification
from togther.models import (Community_Rank, collabcardState,
                            MemberPollVotes, Collabcard, Members, Members, Referal, Community, communityAnswers,
                            Userinfo, communityLevels, communityExpiryCodes, conversationEngage, card_answers,
                            conversationMemberState, memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory, Report, Report_Tags, communityRightsSettings, blockedMembers,
                            userDevices, ModelUtilities, answerAttachment)
from utility.list_utilities import ListUtilities
from utility.string_utilities import StringUtilities
from utility.webhook_utilities import WebhookUtilties

from utility.utils import *
from utility.time_utilities import TimeUtilities
from utility.celery_beat_tasks import CeleryBeatTask
from utility.constants import (INTRO_ROOM_LOOKBACK_PERIOD,
                               MINUTES_2, HOURS_24, MINUTES_5,
                               MINUTES_10, MINUTES_30, VALID_URLS_REGEX, 
                               ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_START,
                               ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_END,
                               NOTIFICATION_PAYLOAD_SENDER)
from utility.version_utilities import VersionUtilities
from utility.firebase_http_v1 import FCMHTTPV1Notification
from project.celery import app
from utility.states import *
from collabmates_api.webhook.constants import WEBHOOK_SOURCE_FEED, WEBHOOK_SOURCE_CHAT

import json
from django.shortcuts import get_object_or_404
import traceback

from datetime import datetime, timedelta

from .notifications.constants import NotificationCategories, NotificationSubCategories, NOTIFICATION_SUB_CATEGORY_KEY, \
    NOTIFICATION_CATEGORY_KEY
from .notifications.tasks_impl import TasksHelper
from .serializers import get_answer_files, get_collabcard_files
from .static_text import *
from utility.time_utilities import TimeUtilities
from utility.constants import (INTRO_ROOM_NOTIFICATION_TITLE_PLURAL,
                               INTRO_ROOM_NOTIFICATION_TITLE_SINGULAR,
                               INTRO_ROOM_NOTIFICATION_SUBTITLE_SINGULAR,
                               INTRO_ROOM_NOTIFICATION_SUBTITLE_PLURAL,
                               INTRO_ROOM_NOTIFICATION_ROUTE_SINGULAR,
                               INTRO_ROOM_NOTIFICATION_ROUTE_PLURAL,
                               SYNC_NOTIFICATION_TITLE,
                               SYNC_NOTIFICATION_SUBTITLE,
                               SYNC_NOTIFICATION_ROUTE)

from external_services.segment.segment_impl import SegmentImpl
from django.db import connection
from utility.number_utilities import NumberUtilities

from external_services.caching.cache_impl import CacheImpl
from collabmates_api.sdk.models import (SdkClient)

from external_services.wa_notification.wa_notification_impl import NotificationImpl
from external_services.wa_notification.constants import WATI_NOTIFICATION_CONST

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

# file to store configuration of the system


# database details
db_user = settings.DATABASES['default']['USER']
db_password = settings.DATABASES['default']['PASSWORD']
db_host = settings.DATABASES['default']['HOST']
db_port = settings.DATABASES['default']['PORT']
db_database = settings.DATABASES['default']['NAME']

url = settings.URL

# server keys for sending notification
server_key = settings.FCM_SERVER_KEY

# FCM timeout
fcm_timeout_seconds = settings.FCM_TIMEOUT_SECONDS


# notifications for different mobile os versions
def send_test_notification(request):
    platform = request.GET.get('platform')
    fcm_token = request.GET.get('fcm_token')

    message = {}
    message['payload'] = {
        'title': "Testing Notification",
        'sub_title': "checking",
        'route': "route://collabcard?collabcard_id=" + str(4779)
    }
    token_list = []
    token_list.append(fcm_token)
    # if platform == "android":
    #     res = send_notification_for_android(token_list,message)
    # else:
    res = send_notification_for_ios(token_list, message)

    context = {
        'res': res
    }
    return JsonResponse(context)


def get_firebase_server_key_or_service_file_from_message_payload(message):
    message_payload = message.get('payload', {})
    community_id = message_payload.get('community_id', None)

    service_account_file_dict = None
    server_key = settings.FCM_SERVER_KEY

    if community_id:
        sdk_client_filter = ModelUtilities.get_model_filter(SdkClient, {'community': community_id})

        if sdk_client_filter:
            if sdk_client_filter[0].gcp_service_account_file:
                service_account_file_dict = sdk_client_filter[0].gcp_service_account_file

            if sdk_client_filter[0].firebase_server_key:
                server_key = sdk_client_filter[0].firebase_server_key

        del message['payload']['community_id']

    return server_key, service_account_file_dict


def send_notifications(service_account_file_dict: dict, firebase_key: str, token_chunks_list: list, message: dict,
                       stacks: list = None, legacy_version_extra_kwargs: dict = {},
                       http_v1_extra_kwargs_android: dict = {}, http_v1_extra_kwargs_ios: dict = {},
                       notification_os: str = ""):
    final_result = []
    total_notifications_count = 0
    total_success_count = 0
    total_failures_count = 0

    message_title = message['payload']['title']
    message_body = message['payload']['sub_title']
    remove_notification = False

    if notification_os == NotificationPlatform.ANDROID.value:
        message_title = None
        message_body = None
        remove_notification = True

    if service_account_file_dict:
        push_service = FCMHTTPV1Notification(service_account_file_dict)

        for token_chunk in token_chunks_list:
            result = push_service.notify_multiple_devices(registration_ids=token_chunk,
                                                          stacks=stacks,
                                                          message_title=message_title,
                                                          message_body=message_body,
                                                          message_icon=None,
                                                          data_message=message['payload'],
                                                          remove_notification=remove_notification,
                                                          extra_kwargs_android=http_v1_extra_kwargs_android,
                                                          extra_kwargs_ios=http_v1_extra_kwargs_ios)

            final_result.append(result)
            total_notifications_count += len(token_chunk)
            total_success_count += result.get('success')
            total_failures_count += result.get('failure')

    else:
        push_service = FCMNotification(api_key=firebase_key)

        for token_chunk in token_chunks_list:
            result = push_service.notify_multiple_devices(registration_ids=token_chunk,
                                                          data_message=message['payload'],
                                                          timeout=fcm_timeout_seconds,
                                                          extra_kwargs=legacy_version_extra_kwargs)

            final_result.append(result)
            total_notifications_count += len(token_chunk)
            total_success_count += result.get('success')
            total_failures_count += result.get('failure')

    log_statement = """The {} devices should have total {} notifications out of which {} success & {} failures. 
                    Payload is {} """.format(notification_os, total_notifications_count, total_success_count,
                                             total_failures_count, message.get('payload'))
    print(f"{log_statement} \nFinal Result: {final_result}")

    return final_result


def send_notification_for_android(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to android"""

    if not token_list:
        return

    token_chunks_list = ModelUtilities.divide_chunks(token_list, chunk_size=300)

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs = {
        "priority": "HIGH"
    }

    legacy_extra_kwargs = {
        "android": {
            "priority": "high"
        }
    }

    final_result = send_notifications(service_account_file_dict, firebase_key, token_chunks_list, message, ['android'],
                                      legacy_extra_kwargs, http_v1_extra_kwargs, {},
                                      NotificationPlatform.ANDROID.value)

    return final_result


def send_notification_for_ios(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to android"""

    if not token_list:
        return

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs = {        # refer FCMHTTPV1Notification.parse_payload to construct kwargs
        "payload": {
            "aps": {
                "mutable_content": 'true',
                "sound": message['payload'].get('sound')
            }
        }
    }

    legacy_extra_kwargs = {
        "mutable_content": True
    }

    final_result = send_notifications(service_account_file_dict, firebase_key, [token_list], message, ['ios'],
                                      legacy_extra_kwargs, http_v1_extra_kwargs, {}, NotificationPlatform.IOS.value)

    return final_result


def send_notification_for_web(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to web"""

    if not token_list:
        return

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs = {}
    legacy_extra_kwargs = {}

    final_result = send_notifications(service_account_file_dict, firebase_key, [token_list], message, None,
                                      legacy_extra_kwargs, http_v1_extra_kwargs, {}, NotificationPlatform.WEB.value)

    return final_result


def send_notification_for_react(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to web"""

    if not token_list:
        return

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs = {}
    legacy_extra_kwargs = {}

    final_result = send_notifications(service_account_file_dict, firebase_key, [token_list], message, None,
                                      legacy_extra_kwargs, http_v1_extra_kwargs, {}, NotificationPlatform.REACT.value)

    return final_result


def send_notification_for_flutter(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to flutter"""

    if not token_list:
        return

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs_android = {
        "priority": "HIGH",
        "notification": {
            "channel_id": "likeminds_flutter_channel",
        },
    }

    http_v1_extra_kwargs_ios = {
        "payload": {
            "aps": {
                "content_available": 'true',
                "mutable_content": 'true',
            }
        }
    }

    legacy_extra_kwargs = {
        "android": {
            "priority": "high",
            "channel_id": "likeminds_flutter_channel"
        },
        "ios": {
            "content_available": True,
            "mutable_content": True
        }
    }

    final_result = send_notifications(service_account_file_dict, firebase_key, [token_list], message,
                                      ['android', 'ios'], legacy_extra_kwargs, http_v1_extra_kwargs_android,
                                      http_v1_extra_kwargs_ios, NotificationPlatform.FLUTTER.value)

    return final_result


def send_notification_for_react_native(token_list, message, service_account_file_dict=None, firebase_key=None):
    """function to send notification to react native"""

    if not token_list:
        return

    firebase_key = firebase_key if firebase_key else server_key

    http_v1_extra_kwargs_android = {
        "priority": "HIGH",
    }

    http_v1_extra_kwargs_ios = {
        "payload": {
            "aps": {
                "content_available": 'true',
            }
        }
    }

    legacy_extra_kwargs = {
        "android": {
            "priority": "high",
        },
        "ios": {
            "content_available": True,
        }
    }

    final_result = send_notifications(service_account_file_dict, firebase_key, [token_list], message,
                                      ['android', 'ios'], legacy_extra_kwargs, http_v1_extra_kwargs_android,
                                      http_v1_extra_kwargs_ios, NotificationPlatform.REACT_NATIVE.value)

    return final_result


def send_silent_notification(token_list, service_account_file_dict=None):

    if service_account_file_dict:
        push_service = FCMHTTPV1Notification(service_account_file_dict)
        result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                      message_title='',
                                                      message_body='')
    else:
        push_service = FCMNotification(api_key=server_key)
        result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                      timeout=fcm_timeout_seconds)

    return result


def get_title_from_collabcard(card):
    ''' To extract the title from a card. '''
    if card.header:
        return card.header
    else:
        return card.title[:30]


def get_devices_of_users(user_id):
    '''function to get all devices of users'''

    devices_filter = userDevices.objects.filter(user=user_id)
    user_devices = []

    for device in devices_filter:
        temp = {}
        temp['id'] = device.user.id
        temp['fcm_token'] = device.fcm_token
        temp['mobile_os'] = device.mobile_os
        user_devices.append(temp)

    return user_devices


def track_notification(user_id, notification_payload):
    SegmentImpl.track_event(str(user_id),
                            event_name=SEGMENT_NOTIFICATION_TRACKING_EVENT_NAME,
                            event_data=notification_payload)


def track_notification_with_notification_payload_list(notification_payload_list):

    for notification in notification_payload_list:

        if notification.get('user_id') and notification.get('payload'):
            SegmentImpl.track_event(str(notification['user_id']),
                                    event_name=SEGMENT_NOTIFICATION_TRACKING_EVENT_NAME,
                                    event_data=notification['payload'])


def pre_compute_user_devices_by_user_list(user_list, is_broadcast_notification=False):
    """function to pre compute users' devices with user list"""

    devices_filter = ModelUtilities.get_model_filter(userDevices, {'user_id__in': user_list})

    # If it is a broadcast notification, then dont send notifications to users with android version in range specified
    if is_broadcast_notification:
        devices_filter = devices_filter.exclude(platform_code='an', 
                                                version_code__lte=ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_END, 
                                                version_code__gte=ANDROID_BRODCAST_NOTIFIFCATION_BLOCK_VERSION_START)
        
    devices_filter = list(devices_filter.values('id', 'fcm_token', 'mobile_os', 'user_id'))
        
    devices_dict = {user_id: [] for user_id in user_list}

    for device in devices_filter:

        if devices_dict.get(device['user_id']):
            devices_dict[device['user_id']].append(device)

        else:
            devices_dict[device['user_id']] = [device]

    return devices_dict

def get_community_id_from_notification_message(message):
    '''function to get community id from notification message payload'''

    if message.get('payload'):
        return message['payload'].get('community_id', None)

    return None

def send_notification_webhooks_in_chunks(payload: dict, uuids: list, webhooks, webhook_type, chunk_size: int=1000):
    '''function to send webhook requests in chunks'''

    total_uuids = len(uuids)
    payload['data']['tota_pages'] = (total_uuids // chunk_size) + 1

    # Trigger the webhooks in batches of chunk_size
    for i in range(0, total_uuids, chunk_size):
        start_index = i
        end_index = i + chunk_size
        uuids_batch = uuids[start_index:end_index]

        for webhook in webhooks:

            # Update the payload with client uuids
            payload['id'] = str(uuid.uuid4())
            payload['data']['uuids'] = uuids_batch
            payload['data']['current_page'] = (i // chunk_size) + 1

            # send webhook request
            WebhookUtilties.send_webhook_request_with_payload.delay(
                url=webhook.get('url'),
                payload=payload,
                webhook_type=webhook_type,
                secret=webhook.get('secret')
            )
    
def generate_payload_for_notification_webhooks(webhook_type, notification_payload):

    source = ""

    if webhook_type == WebhookTypes.NOTIFICATIONS_CHAT.value:
        source = WEBHOOK_SOURCE_CHAT

    elif webhook_type == WebhookTypes.NOTIFICATIONS_FEED.value:
        source = WEBHOOK_SOURCE_FEED

    # webhook payload
    payload = {
        "event": webhook_type,
        "source": source,
        "created_at": TimeUtilities.current_time_in_milliseconds(),
        "data": {
            "notification_payload": notification_payload,
            "uuids": []
        }
    }

    return payload

@shared_task
def trigger_webhooks_for_notifications(user_ids: list, notification_payload: dict, community_id, sdk_source):
    '''function to trigger webhooks for notifications'''

    if not (user_ids and notification_payload and community_id):
        return
    
    webhook_type = ""

    # Set the webhook type 
    if sdk_source == VersionUtilities.SdkSource.CHAT:
        webhook_type = WebhookTypes.NOTIFICATIONS_CHAT.value

    elif sdk_source == VersionUtilities.SdkSource.FEED:
        webhook_type = WebhookTypes.NOTIFICATIONS_FEED.value

    else:
        return
    
    # Get active webhooks for the community
    webhooks = WebhookUtilties.validate_and_fetch_all_webhook_url_and_secret(
        community_id=community_id,
        webhook_type=webhook_type
    )

    if not webhooks:
        return
    
    # generate payload
    payload =  generate_payload_for_notification_webhooks(webhook_type, notification_payload)

     # Fetch client uuids
    client_uuids = ModelUtilities.get_model_filter(SDKClientUsersInfo, {
        'user_id__in': user_ids
    }).values_list('user_unique_id', flat=True)

    if not client_uuids:
        return 

    # trigger webhooks in chunks 
    send_notification_webhooks_in_chunks(payload, list(client_uuids), webhooks, webhook_type, 1000)

    return


def notification_meta(notification_list, message, is_broadcast_notification: bool=False, sdk_source: str="chat"):
    """function to process notification to send"""

    # Get the user ids from the notification list
    user_id_list = [user_dict['id'] for user_dict in notification_list]

    # Get community id from the message payload
    community_id = get_community_id_from_notification_message(message)

    # Trigger webhooks for notifications
    trigger_webhooks_for_notifications.delay(
        user_ids=user_id_list,
        notification_payload=message,
        community_id=community_id,
        sdk_source=sdk_source
    )

    # Check if user_notifications are enabled
    user_notifications_disabled_filter = ModelUtilities.get_model_filter(CommunitySettings, {
        'community_id': community_id,
        'setting_type': community_setting_types.USER_NOTIFICATIONS,
        'enabled': False
    }).first()

    # If user_notifications are disabled, then log and return 
    if user_notifications_disabled_filter:
        info_logger.info(f"User notifications are disabled for community: {community_id}, hence no notifications are triggered with message payload: {message} and for users: {user_id_list}")
        return

    # Pre compute user devices and their fcm tokens by user list
    user_device_dict = pre_compute_user_devices_by_user_list(user_list=user_id_list, 
                                                             is_broadcast_notification=is_broadcast_notification)

    tokens = {
        'Android': [],
        'iOS': [],
        'web': [],
        'Flutter': [],
        'React Native': [],
        'React': [],
    }

    category_dict = message.get('category')

    if category_dict:
        message['category'] = category_dict.get('category')
        message['subcategory'] = category_dict.get('subcategory')

    notification_payload_list = []

    for data in notification_list:

        if 'id' in data:
            user_id = data['id']

            print('notification sent data, receiver: {}, category: {}, subcategory: {}'.format(
                user_id,
                message.get('category'),
                message.get('subcategory')
            ))

        else:
            continue

        user_devices = user_device_dict[user_id]

        payload = {}

        for device in user_devices:

            notification_payload_dict = {}
            device_token = device['fcm_token']
            tokens[device['mobile_os']].append(device_token)
            payload = message
            payload['fcm_token'] = device_token

            notification_payload_dict['user_id'] = device['user_id']
            notification_payload_dict['payload'] = payload

            if message.get('category'):
                message['payload']['category'] = message.get('category')

            if message.get('subcategory'):
                message['payload']['subcategory'] = message.get('subcategory')

            message['payload']['sender'] = NOTIFICATION_PAYLOAD_SENDER

            notification_payload_list.append(notification_payload_dict)

    firebase_key, gcp_service_account_file_dict = get_firebase_server_key_or_service_file_from_message_payload(message)

    send_notification_for_android(tokens['Android'], message, gcp_service_account_file_dict, firebase_key)

    send_notification_for_ios(tokens['iOS'], message, gcp_service_account_file_dict, firebase_key)

    send_notification_for_web(tokens['web'], message, gcp_service_account_file_dict, firebase_key)

    send_notification_for_flutter(tokens['Flutter'], message, gcp_service_account_file_dict, firebase_key)

    send_notification_for_react_native(tokens['React Native'], message, gcp_service_account_file_dict, firebase_key)

    send_notification_for_react(tokens['React'], message, gcp_service_account_file_dict, firebase_key)

    track_notification_with_notification_payload_list(notification_payload_list)


def get_connection():
    '''function to create a postgres connection'''
    try:
        # connection = psycopg2.connect(user=db_user,
        #                               password=db_password,
        #                               host=db_host,
        #                               port=db_port,
        #                               database=db_database)
        return connection

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_token_for_fcm(member_id, flag=None):
    '''function to get token from user'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        if not flag:
            curr.execute("select fcm_token from togther_userinfo where user_id_id=" + str(member_id))
            fcm_token = curr.fetchone()
            if fcm_token:
                return fcm_token[0]
        else:
            curr.execute("select fcm_token,mobile_os from togther_userinfo where user_id_id=" + str(member_id))

            notification_details = curr.fetchone()
            if notification_details:
                fcm_token = notification_details[0]
                if notification_details[1]:
                    mobile_os = notification_details[1]
                else:
                    mobile_os = "Android"
                return (fcm_token, mobile_os)

        return None

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def get_user_fcm_details(user_instance):
    user_details = {
        "id": user_instance.id,
    }

    return user_details


def get_community_name(community_id):
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select name from togther_community where id= " + str(community_id)
        curr.execute(sql)
        community_name = curr.fetchone()[0]
        curr.close()

        return community_name

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)


def is_mobile_os_android(fcm_token):
    '''function to change whether the mobile os is android or ios'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select mobile_os from togther_userinfo where fcm_token='" + fcm_token + "'"
        curr.execute(sql)
        mobile_os = curr.fetchone()

        if mobile_os:
            # print(mobile_os[0])
            if mobile_os[0] == "Android":
                # print("Android")
                return True
            elif mobile_os[0] == "iOS":
                # print("iOS")
                return False
        else:
            return True

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def send_notification_to_multiple_devices(token_list, message, service_account_file_dict):
    '''This function is used to send notifications by checking whether the request is android or ios'''

    for token in token_list:

        mobile_os = is_mobile_os_android(token)
        if mobile_os:
            send_notification(token, message, True, service_account_file_dict)  # if request is android
        else:
            send_notification(token, message, False, service_account_file_dict)  # if request is iOS


def send_notification(fcm_token, message, is_android, service_account_file_dict=None):
    '''function to send notification for android as well as iOS'''

    token_list = []
    token_list.append(fcm_token)

    if not is_android:
        if service_account_file_dict:
            push_service = FCMHTTPV1Notification(service_account_file_dict)
            result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                        message_title=message['payload']['title'],
                                                        message_body=message['payload']['sub_title'],
                                                        data_message=message['payload'])

        else:
            push_service = FCMNotification(api_key=server_key)
            result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                        message_title=message['payload']['title'],
                                                        message_body=message['payload']['sub_title'],
                                                        data_message=message['payload'],
                                                        timeout=fcm_timeout_seconds)

    else:
        if service_account_file_dict:
            push_service = FCMHTTPV1Notification(service_account_file_dict)
            result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                        data_message=message['payload'])

        else:
            push_service = FCMNotification(api_key=server_key)
            result = push_service.notify_multiple_devices(registration_ids=token_list,
                                                            data_message=message['payload'],
                                                            timeout=fcm_timeout_seconds)
    print(result)


def get_tagged_members_list(community_id, chatroom_id, answer):
    tagged_users_list = re.findall("route:\/\/[member member_profile]+\/([0-9]+)", answer)
    tagged_uuids_list = re.findall("route:\/\/user_profile\/([\s\S]*?)>>", answer)
    answer_text = re.sub(r'\|route://[member member_profile]+/[0-9]+>>|<<', '', answer)
    answer_text_from_uuid = re.sub(r'\|route:\/\/user_profile\/([\s\S]*?)>>|<<', '', answer)
    tagged_user_names = "@" + ' @'.join(re.findall('(?<=\<\<).+?(?=\|)', answer))

    if tagged_uuids_list:
        valid_ids = ModelUtilities.get_valid_user_ids_from_uuids(tagged_uuids_list, community_id)
        valid_ids = ListUtilities.convert_elements_int_to_str(valid_ids)
        tagged_users_list.extend(valid_ids)
        answer_text = answer_text_from_uuid

    group_tagged_users, conversation_text, should_unmute_members, is_group_tag = process_group_tags(
        community_id,
        chatroom_id,
        answer_text
    )

    if group_tagged_users:
        tagged_users_list = ListUtilities.merge_lists(tagged_users_list, group_tagged_users)

    if conversation_text:
        answer_text = conversation_text

    tagged_users_list = ListUtilities.remove_duplicates(tagged_users_list)

    return tagged_users_list, answer_text, tagged_user_names, should_unmute_members, is_group_tag


def process_group_tags(community_id: str, chatroom_id: str, answer_text: str):
    everyone_tag: list = re.findall(EVERYONE_TAG_REGEX, answer_text)
    participants_tag: list = re.findall(PARTICIPANTS_TAG_REGEX, answer_text)

    conversation_text: str = StringUtilities.replace_in_string(EVERYONE_TAG_REGEX, EVERYONE_TAG_TEXT, answer_text)
    conversation_text = StringUtilities.replace_in_string(PARTICIPANTS_TAG_REGEX, PARTICIPANTS_TAG_TEXT, conversation_text)

    should_unmute_members: bool = False
    is_group_tag: bool = False

    '''
        if both tags present we process everyone (community) tag 
        and return
    '''
    if everyone_tag:
        # tagged_users = process_everyone_tag(community_id, chatroom_id)
        tagged_users = []
        should_unmute_members = False
        is_group_tag = True
        return tagged_users, conversation_text, should_unmute_members, is_group_tag

    if participants_tag:
        tagged_users = process_participants_tag(chatroom_id)
        is_group_tag = True
        return tagged_users, conversation_text, should_unmute_members, is_group_tag

    return list(), conversation_text, should_unmute_members, is_group_tag


def process_everyone_tag(community_id: str, chatroom_id: str) -> list:
    if not community_id:
        return []

    from collabmates_api.community.community_impl import CommunityImpl

    community_members: list = CommunityImpl('', str(community_id)).get_community_members()
    community_members = list(community_members.values_list('member_id_id', flat=True))

    return ListUtilities.convert_elements_int_to_str(community_members)


def process_participants_tag(chatroom_id: str) -> list:
    if not chatroom_id:
        return []

    from collabmates_api.chatroom.chatroom_impl import ChatroomImpl

    chatroom_participants_un_mute_filter_dict: dict = {
        'card_id': chatroom_id,
        'mute_status': False,
        'follow_status': True,
        'remove': None
    }
    chatroom_un_muted_members: QuerySet = ChatroomImpl(
        '',
        str(chatroom_id)
    ).get_chatroom_participants(chatroom_participants_un_mute_filter_dict)

    chatroom_un_muted_members_ids: list = list(chatroom_un_muted_members.values_list('user_id', flat=True))

    return ListUtilities.convert_elements_int_to_str(chatroom_un_muted_members_ids)


@shared_task
def send_notification_to_admins(community_id, name):
    '''function to send notification to community admins'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "select member_id_id from togther_members where community_id_id= " + str(
            community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins = curr.fetchall()
        notification_list = []

        eligible_admin_ids = list(userAdminRights.objects.filter(community=community_id,
                                                                 right__state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS).values_list(
            "user__id",
            flat=True))
        for admin in admins:
            temp = {}
            promoter_id = admin[0]
            if promoter_id in eligible_admin_ids:
                notification_details = get_token_for_fcm(promoter_id, True)
                if notification_details:
                    temp['id'] = promoter_id
                    temp['fcm_token'] = notification_details[0]
                    temp['mobile_os'] = notification_details[1]

                notification_list.append(temp)

        community_name = get_community_name(community_id)
        message = {
            'payload': {
                'title': community_name,
                'sub_title': str(name) + ' has requested to join your community',
                'route': 'route://member_approve?' + 'community_id=' + str(community_id) + "&" + "community_name=" +
                         str(community_name)
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MEMBERSHIP_REQUESTED
            }
        }

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)

        # send_notification_to_multiple_devices(token_list,message)
        curr.close()

    except (Exception, psycopg2.Error) as error:

        print("Error while connecting to PostgreSQL", error)


@shared_task
def send_notification_for_join_requests(community_id, flag, member_id, promoter_name=""):
    '''function to send notification for approval or denial'''
    community_name = get_community_name(community_id)
    temp = {}
    notification_list = []
    temp['id'] = member_id
    notification_details = get_token_for_fcm(member_id, True)
    temp['fcm_token'] = notification_details[0]
    temp['mobile_os'] = notification_details[1]

    notification_list.append(temp)

    message = {}
    if flag:
        if promoter_name != "":
            message['payload'] = {
                'title': "Membership approved!",
                'sub_title': "Congratulations, " + promoter_name + " has accepted your request to join " + community_name,
                'route': '//route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
                    community_name)
            }
        else:
            message['payload'] = {
                'title': "Membership approved!",
                'sub_title': "Congratulations, you are now part of the " + community_name + " community",
                'route': '//route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
                    community_name)

            }

        message['category'] = {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MEMBERSHIP_APPROVED
        }

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)
    # else:
    #     message['payload'] = {
    #         'title': community_name,
    #         'sub_title': "Your request to join this community has been rejected",
    #         'route': 'route://member_declined?community_id=' + str(community_id)
    #     }

    # notification_meta(notification_list,message)


@shared_task
def send_notification_to_new_promoter(context):
    promoter_id = context['nominated_admin']
    community_id = context['community_id']
    admin_name = context['admin']
    notification_list = []
    try:
        temp = {}
        notification_details = get_token_for_fcm(promoter_id, True)
        if notification_details:
            temp['id'] = promoter_id
            temp['fcm_token'] = notification_details[0]
            temp['mobile_os'] = notification_details[1]

            notification_list.append(temp)
            community_name = get_community_name(community_id)

            message = {}
            message['payload'] = {
                'title': community_name,
                'sub_title': str(admin_name) + " has added you as promoter of the community.",
                'route': 'route://community?community_id=' + str(community_id)
            }

            notification_meta(notification_list, message)


    except (Exception, psycopg2.Error) as error:
        traceback.print_exc()
        print("Error while connecting to PostgreSQL", error)


# notifications for new collabcards

@shared_task
def send_notification_for_new_collabcard_posted(community_id, collabcard_title, card_creater_id, card_creater_name,
                                                card_id, **kwargs):
    ''' function to send notification to all members when new collabcard is posted '''

    try:
        card = Collabcard.objects.get(id=card_id)

        notification_list_member = []
        tagged_users_list = []
        user_names = ''
        custom_payload = {}

        if card.is_secret:
            participants = json.loads(card.secret_chatroom_participants)
            promoter_list = list(
                ModelUtilities.get_model_filter(Members,
                                                {'community_id': card.community_id,
                                                 'state': member_states.ADMIN}).values_list('member_id',
                                                                                            flat=True))
            participants = list(set(participants) | set(promoter_list))

            for user_id in participants:

                if NumberUtilities.get_integer_from_string(card_creater_id) == user_id:
                    continue

                temp = {
                    'id': user_id
                }
                notification_list_member.append(temp)
        else:
            connection = get_connection()
            curr = connection.cursor()
            sql = """
                    SELECT 
                        member_id_id,
                        state
                    FROM 
                        togther_members
                    WHERE 
                        community_id_id=%s
                        AND member_id_id !=%s
                        AND 
                        (
                            state = 1 or
                            state = 4 or
                            state = 9
                        )
                  """
            parameter_list = [community_id, card_creater_id]
            curr.execute(sql, parameter_list)
            member_list = curr.fetchall()

            tagged_users_list, collabcard_title, user_names, should_unmute_members, _ = get_tagged_members_list(
                community_id,
                card_id,
                collabcard_title
            )

            blocked_by_user_list = list(blockedMembers.objects.filter(community=community_id,
                                                                      blocked_member=card_creater_id).values_list(
                "blocked_by__id", flat=True))
            eligible_admin_ids = []
            if card.is_pending:
                eligible_admin_ids = list(userAdminRights.objects.filter(community=community_id,
                                                                         right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS).values_list(
                    "user__id", flat=True))

            for member in member_list:
                member_id = member[0]
                member_state = member[1]
                if card.is_pending:
                    if member_state != member_states.ADMIN:
                        continue
                    elif member_id not in eligible_admin_ids:
                        continue

                temp = {}
                temp['id'] = member_id
                notification_details = get_token_for_fcm(member[0], True)
                temp['fcm_token'] = notification_details[0]
                temp['mobile_os'] = notification_details[1]
                if str(member[0]) not in tagged_users_list and int(member[0]) not in blocked_by_user_list:
                    notification_list_member.append(temp)

            custom_payload = get_custom_data_for_new_chatroom_created(card, kwargs['set_default_unread_count'])

        collabcard_title = get_title_from_collabcard(card)

        community_name = kwargs['community_name']
        message = {}
        typ = kwargs['type'] if 'type' in kwargs else 0

        title = community_name
        category = NotificationCategories.MODERATION,
        subcategory = NotificationSubCategories.CHATROOM_APPROVAL

        if card.is_pending:
            sub_title = str(card_creater_name) + " has created a new chat room " + str(collabcard_title)
            route = 'route://chatroom_detail?chatroom_id=' + str(card_id)

        elif card.is_secret:
            sub_title = str(card_creater_name) + " created a secret chatroom: " + str(collabcard_title)
            route = 'route://chatroom_detail?chatroom_id=' + str(card_id)
            category = NotificationCategories.CHATROOM
            subcategory = NotificationSubCategories.SECRET_CHATROOM_CREATED

        elif typ == card_types.CARD_POLL:
            title = "Time to vote!"
            sub_title = str(card_creater_name) + " started a poll on " + str(collabcard_title) + " in " + community_name
            route = 'route://poll_chatroom?chatroom_id=' + str(card_id)
            category = NotificationCategories.CHATROOM
            subcategory = NotificationSubCategories.POLL_ROOM_CREATED
            schedule_poll_end_notification(card_id)

        else:
            sub_title = str(card_creater_name) + " started a new chatroom: " + str(collabcard_title) + ". Join now!"
            route = 'route://collabcard?collabcard_id=' + str(card_id)
            category = NotificationCategories.HOME
            subcategory = NotificationSubCategories.NEW_CHATROOM_CREATED

        message = {
            'payload': {
                'title': title,
                'sub_title': sub_title,
                'route': route
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: category,
                NOTIFICATION_SUB_CATEGORY_KEY: subcategory
            }
        }

        if not card.is_pending \
                and not card.is_secret and \
                typ not in [card_types.CARD_POLL, card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
            message['payload']['unread_new_chatroom'] = custom_payload

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list_member, message)

        if not card.is_pending:
            # functionality to send notification to tagged users
            new_title_text = re.sub(r'\|route://member/[0-9]+>>|<<', '', card.title)

            for member_id in tagged_users_list:

                if not str(member_id) == str(card_creater_id):
                    send_notification_to_tagged_users(card_id=card_id,
                                                      answerer_name=card_creater_name,
                                                      answer=new_title_text,
                                                      user_id=member_id, user_names=user_names)

    except (Exception, psycopg2.Error) as error:
        info_logger.info("Error while connecting to PostgreSQL", error)


@shared_task
def schedule_poll_end_notification(card_id):
    card_instance = Collabcard.objects.get(pk=card_id)

    args = [card_instance.id]

    poll_end_time = TimeUtilities.convert_milliseconds_to_sec(card_instance.end_date)
    poll_task_end_time = TimeUtilities.add_minutes_to_epoch_time(poll_end_time, minutes=5)
    task_begin_time = TimeUtilities.convert_epoch_to_datetime_in_IST(poll_end_time)
    task_expiry_time = TimeUtilities.convert_epoch_to_datetime_in_IST(poll_task_end_time)

    poll_room_ending_notification.apply_async(args=args,
                                              kwargs={},
                                              eta=task_begin_time,
                                              expires=task_expiry_time
                                              )

    celery_beat_task = CeleryBeatTask()

    if card_instance.type == card_types.CARD_POLL:
        task_name = f'{card_id}_poll_results_announcement_after_6_hours'
        task_path = "collabmates_api.tasks.send_poll_results_announcement_mail"
        celery_beat_task.terminate_task(task_name)

        args = [card_id, task_name]
        date_time = poll_end_time + SIX_HOURS_IN_SECONDS
        celery_beat_task.create_dynamic_clery_task(args=args, kwargs={}, task_name=task_name, task_path=task_path,
                                                   date_time=date_time, interval=False, crontab=True)


def fetch_all_valid_urls(string):
    regex = VALID_URLS_REGEX
    valid_urls = re.findall(regex, string)

    return [x[0] for x in valid_urls]


@app.task
@shared_task
def poll_room_ending_notification(card_id, **kwargs):
    """ function to send notification to all members when event/poll is going to start/end """
    try:
        card_instance = Collabcard.objects.get(pk=card_id)
        card_owner = card_instance.user
        owner_flag = False
        card_title = get_title_from_collabcard(card_instance)

        collabcardState.objects.filter(card=card_id).update(updated_at=time.time())

        members = MemberPollVotes.objects.filter(card=card_id).order_by('-id').select_related('user')
        notification_list = []
        for member in members:

            if card_owner.id == member.user.id:
                owner_flag = True

            notification_list.append({'id': member.user.id})

        # if card owner did not vote, add him to notification list
        if owner_flag is False:
            notification_list.append({'id': card_owner.id})

        sub_title = POLL_EXPIRY_NOTIFICATION_SUB_TITLE
        route = POLL_EXPIRY_NOTIFICATION_ROUTE % card_id

        message = {'payload': {
            'title': str(card_title),
            'sub_title': sub_title,
            'route': route
        }}

        notification_meta(notification_list, message)

    except Exception as e:
        error_logger.error(f"poll_room_ending_notification : {e}")


def should_send_notification(card_instance: object):
    if getattr(card_instance, 'is_deleted', False) and \
            Collabcard.is_chatroom_deleted(card_instance.is_deleted):
        message = f"aborting notification. chatroom is deleted (id = {card_instance.id})."
        return False, message

    return True, ""


def get_custom_data_for_new_chatroom_created(card, set_default_unread_count=False):
    """ function to get data for custom notification """

    unread_conversation = {}
    chatroom_instance = card
    user_instance = chatroom_instance.user
    community_instance = chatroom_instance.community
    userinfo_instance = user_instance.userinfo
    unread_conversation['community_name'] = community_instance.name
    unread_conversation['chatroom_name'] = get_title_from_collabcard(chatroom_instance) + " (New Chatroom)"
    unread_conversation['chatroom_title'] = chatroom_instance.title
    unread_conversation['chatroom_user_name'] = userinfo_instance.name

    if set_default_unread_count:
        unread_conversation['chatroom_unread_conversation_count'] = 0

    collabcard_files = get_collabcard_files(card_id=card.id)
    unread_conversation['images'] = collabcard_files[0]
    unread_conversation['pdf'] = collabcard_files[1]
    unread_conversation['audios'] = collabcard_files[2]
    unread_conversation['videos'] = collabcard_files[3]
    unread_conversation['attachments'] = collabcard_files[4]

    chatroom_user_image = userinfo_instance.image_link
    unread_conversation['chatroom_user_image'] = chatroom_user_image if chatroom_user_image else ''
    unread_conversation['chatroom_id'] = chatroom_instance.id
    unread_conversation['community_id'] = str(community_instance.id)
    unread_conversation['community_image'] = community_instance.image_link
    unread_conversation['route'] = """route://chatroom_new_feed?community_id=%s&community_name=%s""" % (
        str(community_instance.id), str(community_instance.name))
    unread_conversation['route_child'] = """route://collabcard?collabcard_id=%s""" % (str(chatroom_instance.id))
    unread_conversation['chatroom_name_ios'] = get_title_from_collabcard(chatroom_instance)

    print(">>>>>>>>>   ", unread_conversation)

    return json.dumps(unread_conversation)


def get_ios_users_from_user_list(user_list):
    ios_users_set = set(userDevices.objects.filter(user_id__in=user_list,
                                                   mobile_os='iOS').values_list('user_id', flat=True))

    return ios_users_set


def get_notification_payload_metadata_for_conversation_creation(community_instance, card_instance, userinfo_instance,
                                                                conversation_instance):
    from collabmates_api.raw_queries import get_users_sdk_meta_dict

    payload = dict()

    payload['community_name'] = community_instance.name
    payload['chatroom_name'] = card_instance.header
    payload['chatroom_title'] = card_instance.title
    payload['chatroom_user_name'] = ""
    payload['chatroom_user_image'] = ""
    payload['chatroom_id'] = card_instance.id
    payload['notification_id'] = str(card_instance.id) + "_followed"

    payload['route'] = """route://chatroom_followed_feed?community_id=%s&community_name=%s""" % (
        str(community_instance.id), str(community_instance.name))
    payload['chatroom_unread_conversation_count'] = 0
    payload['community_id'] = community_instance.id
    payload['community_image'] = ""

    payload['last_conversation_unique_names'] = []
    payload['chatroom_creator'] = get_users_sdk_meta_dict([card_instance.user_id]).get(card_instance.user_id, {})

    if conversation_instance:
        payload['chatroom_last_conversation_id'] = conversation_instance.id
        payload['chatroom_last_conversation'] = conversation_instance.answer
        payload['chatroom_last_conversation_user_name'] = userinfo_instance.name
        payload['chatroom_last_conversation_user_image'] = ""
        payload['chatroom_last_conversation_timestamp'] = conversation_instance.created_at
        payload['chatroom_last_conversation_creator'] = get_users_sdk_meta_dict([conversation_instance.user_id]).get(
            conversation_instance.user_id, {}
        )

        if conversation_instance.has_files or \
                conversation_instance.attachment_count > 0:
            answer_files = get_answer_files(conversation_instance.id)
            payload['images'] = answer_files['image']
            payload['pdf'] = answer_files['pdf']
            payload['videos'] = answer_files['videos']
            payload['audios'] = answer_files['audios']
            payload['attachments'] = answer_files['attachments']

        payload['route_child'] = """route://collabcard?collabcard_id=%s&last_conversation_id=%s""" % (
            str(card_instance.id), str(conversation_instance.id))

    return json.dumps(payload)


def send_notification_to_tagged_users_on_conversation_creation(tagged_users_list, answer_text, userinfo_instance,
                                                               conversation_instance, card_instance,
                                                               community_instance):
    if not tagged_users_list:
        return

    custom_conversation_notification_payload = \
        get_notification_payload_metadata_for_conversation_creation(community_instance,
                                                                    card_instance, userinfo_instance,
                                                                    conversation_instance)
    message = {
        'payload': {
            'title': card_instance.header,
            'sub_title': userinfo_instance.name + ": " + answer_text,
            'route': f"route://collabcard?collabcard_id={str(card_instance.id)}&community_id={str(community_instance.id)}",
            'unread_follow_notification': custom_conversation_notification_payload
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.USER_TAGGED
        }
    }

    notification_list = []

    for tagged_user in tagged_users_list:
        user_id = NumberUtilities.get_integer_from_string(tagged_user)

        if user_id == userinfo_instance.user_id_id:
            continue

        user_context = dict()

        user_context['id'] = user_id

        notification_list.append(user_context)

    notification_meta(notification_list, message)


def get_icon_for_notification(conversation_instance):
    icon_string = ""

    file_types = list(answerAttachment.objects.filter(answer=conversation_instance).
                      distinct('type').values_list('type', flat=True))

    if 'image' in file_types and 'video' in file_types:
        icon_string = '📷 🎥'

    elif 'image' in file_types:
        icon_string = '📷'

    elif 'pdf' in file_types:
        icon_string = '📄'

    elif 'video' in file_types:
        icon_string = '🎥'

    elif 'gif' in file_types:
        icon_string = '👾'

    elif 'audio' in file_types:
        icon_string = '🎧'

    elif 'voice_note' in file_types:
        icon_string = '🎤'

    return icon_string


@shared_task
def send_follow_notification(card_id, user_id, conversation_id):
    card_instance = Collabcard.get_chatroom_or_None(card_id)

    print("card_instance", card_instance)

    if not card_instance:
        return
    userinfo_instance = Userinfo.get_userinfo_or_None(user_id)

    print("userinfo instance", userinfo_instance)

    if not userinfo_instance:
        return

    conversation_instance = ModelUtilities.get_model_instance_or_none(card_answers, conversation_id)

    print("conversation_instance", conversation_instance)

    if not conversation_instance:
        return

    if conversation_instance.state == conversation_states.CONVERSATION_POLL:
        return

    answer = conversation_instance.answer

    community_instance = card_instance.community

    current_time = TimeUtilities.current_time_in_milliseconds()

    chatroom_follower_list = list(
        collabcardState.objects.filter(
            card=card_instance,
            follow_status=True,
            remove=None,
            mute_status=False
        ).filter(
            ~Q(user=user_id)
        ).filter(
            Q(is_noti_paused=False) | (Q(is_noti_paused=True) & Q(unpause_noti_at__lte=current_time))
        ).values_list(
            'user_id',
            'noti_state'
        ).order_by(
            '-user_id'
        )
    )

    tagged_users_list, answer_text, user_names, should_unmute_members, is_group_tag = get_tagged_members_list(
        community_instance.id,
        card_id,
        answer
    )

    icon_string = ""

    if conversation_instance.has_files:
        icon_string = get_icon_for_notification(conversation_instance)

    notification_list = []

    custom_conversation_notification_payload = \
        get_notification_payload_metadata_for_conversation_creation(community_instance,
                                                                    card_instance, userinfo_instance,
                                                                    conversation_instance)
    
    # If @participants or @everyone tag is used, send different route,
    # to not trigger unread_notification api from client side
    if is_group_tag:
        route = CHATROOM_DETAIL_NOTIFICATION_ROUTE % card_id

    else:
        route = COLLABCARD_COMMUNITY_NOTIFICATION_ROUTE % (card_id, community_instance.id)

    message = {
        'payload': {
            'title': card_instance.header,
            'sub_title': userinfo_instance.name + ":" + icon_string + " " + answer_text,
            'route': route,
            'unread_follow_notification': custom_conversation_notification_payload
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.USER_RESPONDED
        }
    }

    for obj in chatroom_follower_list:

        if all([obj[1] in [noti_states.ONLY_MENTIONS_AND_REPLIES, noti_states.DM_MENTION_REPLIES_POLL],
                conversation_instance.card.type != card_types.CARD_DIRECT_MESSAGE,
                str(obj[0]) not in tagged_users_list]):

            if not conversation_instance.reply:
                continue

            elif conversation_instance.reply and (conversation_instance.reply.user_id != obj[0]):
                continue

        user_context = dict()

        user_context['id'] = obj[0]

        notification_list.append(user_context)

    message = TasksHelper.add_community_info_to_notification_payload(message, community_instance.id)
    notification_meta(notification_list, message, is_broadcast_notification=is_group_tag)


def compute_mute_status_for_users(current_user_id):
    mute_list = list(collabcardState.objects.filter(user_id=current_user_id,
                                                    mute_status=True).values_list('card_id', flat=True))
    return mute_list


def get_custom_data_for_new_conversation_created(user_id: str, community_id: str, page_size: int = 10) -> list:
    """function to send notification for new conversation posted to followed users"""

    from collabmates_api.raw_queries import (get_excluded_chatroom_ids_for_notification_settings_for_user,
                                             get_ordered_chatrooms_data_on_unseen_count)

    mute_status_list = compute_mute_status_for_users(user_id)

    ordered_unseen_dict = get_ordered_chatrooms_data_on_unseen_count(user_id, community_id)

    if not ordered_unseen_dict:
        return []

    followed_chatrooms_ids_list = list(ordered_unseen_dict.keys())

    excluded_card_ids = get_excluded_chatroom_ids_for_notification_settings_for_user(
        user_id, chatroom_ids_list=followed_chatrooms_ids_list)

    excluded_card_ids = list(set(mute_status_list + excluded_card_ids))

    # check if intro room setting is enabled and hide the master room accordingly
    filter_dict = {
        'community_id': community_id,
        'setting_type': community_setting_types.INTRO_ROOM,
        'enabled': True
    }

    intro_room_setting_enabled = False

    intro_room_setting_filter = ModelUtilities.get_model_filter(CommunitySettings, filter_dict)

    if intro_room_setting_filter:
        intro_room_setting_enabled = True

    unread_conversation = []

    for card_id, unread_dict in ordered_unseen_dict.items():

        if len(unread_conversation) >= page_size:
            break

        if card_id in excluded_card_ids:
            continue

        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            continue

        if intro_room_setting_enabled and card_instance.type == card_types.CARD_MASTER_INTRO:
            continue

        temp = {}
        community_instance = card_instance.community

        chatroom_name = card_instance.header

        if not chatroom_name:
            chatroom_name = card_instance.title

        if unread_dict.get('unseen_count') > 1:
            chatroom_name = chatroom_name + """ (%s messages)""" % (str(unread_dict.get('unseen_count')))

        temp['community_name'] = community_instance.name
        temp['chatroom_name'] = chatroom_name
        temp['chatroom_title'] = card_instance.title
        temp['chatroom_user_name'] = ""
        temp['chatroom_user_image'] = ""
        temp['chatroom_id'] = card_instance.id

        temp['notification_id'] = str(card_id) + "_followed"
        temp['route'] = """route://chatroom_followed_feed?community_id=%s&community_name=%s""" % (
            str(community_instance.id), str(community_instance.name))
        temp['chatroom_unread_conversation_count'] = unread_dict.get('unseen_count')
        temp['community_id'] = str(community_instance.id)
        temp['community_image'] = community_instance.image_link
        temp['route_child'] = """route://collabcard?collabcard_id=%s""" % (str(card_id))

        last_instance = card_answers.objects.filter(card=card_id, state=0).last()

        if last_instance:
            user_id = last_instance.user_id

            userinfo_instance = Userinfo.get_userinfo_or_None(user_id)

            if not userinfo_instance:
                continue

            last_conversation = last_instance.answer
            temp['chatroom_last_conversation'] = last_conversation
            temp['chatroom_last_conversation_user_name'] = userinfo_instance.name
            temp['chatroom_last_conversation_user_image'] = userinfo_instance.image_link
            created_at = last_instance.created_at

            if TimeUtilities.is_epoch_in_milliseconds(created_at):
                created_at = TimeUtilities.convert_milliseconds_to_sec(created_at)

            temp['chatroom_last_conversation_timestamp'] = created_at

            if last_instance.has_files or \
                    last_instance.attachment_count > 0:
                answer_files = get_answer_files(last_instance)
                temp['images'] = answer_files['image']
                temp['pdf'] = answer_files['pdf']
                temp['videos'] = answer_files['videos']
                temp['audios'] = answer_files['audios']
                temp['attachments'] = answer_files['attachments']

        unread_conversation.append(temp)

    return unread_conversation


def _get_conversation_engage_filter_for_new_conversation(user_id: str, community_id: str) -> dict:
    filter_dict = {
        'user_id': user_id,
        'draft_id': None,
        'unseen_count__gt': 0
    }

    if community_id:
        filter_dict['community_id'] = community_id

    return filter_dict


def get_custom_data_for_new_conversation_created_ios(user_id):
    """ function to send custom data in case of ios """

    # time.sleep(2)
    followed_chatrooms = conversationEngage.objects.filter(user_id=user_id, draft_id=None).order_by('-updated_at',
                                                                                                    '-id')
    print(followed_chatrooms)
    print("\n")
    temp = {}

    if followed_chatrooms.exists():

        conversation = followed_chatrooms[0]
        print(conversation)
        if not conversation.unseen_count:
            return {}

        chatroom_name = get_title_from_collabcard(conversation.card)

        # if conversation.unseen_count > 1:
        #     chatroom_name = chatroom_name+""" (%s messages)"""%(str(conversation.unseen_count))

        temp['community_name'] = conversation.card.community.name
        temp['chatroom_name'] = chatroom_name
        temp['chatroom_title'] = conversation.card.title
        temp['chatroom_user_name'] = conversation.user.userinfo.name
        temp['chatroom_user_image'] = conversation.user.userinfo.image_link
        temp['chatroom_id'] = conversation.card.id
        temp['notification_id'] = str(conversation.card.id) + "_followed"

        temp['route'] = """route://chatroom_followed_feed?community_id=%s&community_name=%s""" % (
            str(conversation.card.community.id), str(conversation.card.community.name))
        temp['chatroom_unread_conversation_count'] = conversation.unseen_count
        temp['community_id'] = str(conversation.card.community.id)
        temp['community_image'] = conversation.card.community.image_link

        # temp['unseen_conversation_count'] = conversation.unseen_count

        # sending names of unique members who have responded in chatroom

        card_instance = conversation.card
        temp['last_conversation_unique_names'] = get_last_conversation_unique_names(card_instance, user_id)

        last_instance = card_answers.objects.filter(card=conversation.card, state=0).last()

        if last_instance:
            last_conversation = last_instance.answer
            temp['chatroom_last_conversation'] = last_conversation
            temp['chatroom_last_conversation_user_name'] = last_instance.user.userinfo.name
            temp['chatroom_last_conversation_user_image'] = last_instance.user.userinfo.image_link
            temp['chatroom_last_conversation_timestamp'] = last_instance.created_at

            if last_instance.has_files or \
                    last_instance.attachment_count > 0:
                answer_files = get_answer_files(last_instance.id)
                temp['images'] = answer_files['image']
                temp['pdf'] = answer_files['pdf']
                temp['videos'] = answer_files['videos']
                temp['audios'] = answer_files['audios']
                temp['attachments'] = answer_files['attachments']

            temp['route_child'] = """route://collabcard?collabcard_id=%s&last_conversation_id=%s""" % (
                str(conversation.card.id), str(last_instance.id))

    return json.dumps(temp)


def get_last_conversation_unique_names(card_instance, user_id):
    '''function to get last conversation unique names'''

    name_set = set()
    name_list = []
    conversation_state_filter = conversationMemberState.objects.filter(card=card_instance, user=user_id)
    if conversation_state_filter.exists():
        last_conversation = conversation_state_filter[0].conversation

        answer_filter = card_answers.objects.filter(card=card_instance, state=0, id__gt=last_conversation.id).order_by(
            '-id')
        for answer in answer_filter:

            if answer.user.id == user_id:
                continue
            if answer.user not in name_set:
                name_set.add(answer.user)
                name_list.append(answer.user.userinfo.name)

            if len(name_list) > 4:
                break
    else:
        answer_filter = card_answers.objects.filter(card=card_instance, state=0).order_by(
            '-id')
        for answer in answer_filter:
            if answer.user not in name_set:
                name_set.add(answer.user)
                name_list.append(answer.user.userinfo.name)

            if len(name_list) > 4:
                break

    return name_list


@shared_task
def send_notification_to_tagged_users(card_id, answerer_name, answer, user_id, user_names, chatroom_created=True):
    '''function to send notification to those users who didn't follow the collabcard but tagged in an answer'''

    try:

        card = Collabcard.objects.get(id=card_id)

        message = {
            'payload': {
                'title': str(answerer_name) + " tagged you!",
                'sub_title': str(get_title_from_collabcard(card)) + ": " + answer,
                'route': "route://collabcard?collabcard_id=" + str(card_id)
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.USER_TAGGED
            }
        }

        if chatroom_created:
            custom_payload = get_custom_data_for_new_chatroom_created(card)
            message['payload']['unread_new_chatroom'] = custom_payload

        notification_list = []
        temp = {}
        notification_details = get_token_for_fcm(user_id, True)
        temp['id'] = user_id
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]

        device_filter = userDevices.objects.filter(user=temp['id'], mobile_os='iOS')

        if device_filter.exists() and chatroom_created is False:
            # case for send conversation message
            unread_followed_chatroom = get_custom_data_for_new_conversation_created_ios(user_id)
            message['payload']['unread_followed_chatroom'] = unread_followed_chatroom

        notification_list.append(temp)

        message = TasksHelper.add_community_info_to_notification_payload(message, card.community.id)
        notification_meta(notification_list, message)

    except (Exception, psycopg2.Error) as error:
        traceback.print_exc()
        print("Error while connecting to PostgreSQL", error)


@shared_task
def send_notification_to_event_co_hosts(co_hosts, card_id, event_title, event_creater):
    '''function to send notification to co-hosts'''

    notification_list = []

    card = Collabcard.objects.get(id=card_id)

    community_name = str(card.community.name)

    for host in co_hosts:
        temp = {}
        notification_details = get_token_for_fcm(host, flag=True)
        temp['id'] = host
        temp['fcm_token'] = notification_details[0]
        temp['mobile_os'] = notification_details[1]
        notification_list.append(temp)

    message = {
        'payload': {
            'title': EVENT_CO_HOST_NOTIFICATION_TITLE,
            'sub_title': EVENT_CO_HOST_NOTIFICATION_SUB_TITLE % (event_creater, event_title, community_name),
            'route': EVENT_CO_HOST_NOTIFICATION_ROUTE % str(card_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.CO_HOST_ADDED
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, card.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_to_proposed_admin(nominated_admin_id, community_id, proposed_admin_name):
    '''function to send notification to proposed admin'''

    fcm_token = get_token_for_fcm(nominated_admin_id)

    if fcm_token:
        token_list = []
        token_list.append(fcm_token)
        community_name = get_community_name(community_id)
        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': str(proposed_admin_name) + " has nominated you as a promoter of this community ",
            'route': 'route://community?community_id=' + str(community_id)
        }

        send_notification_to_multiple_devices(token_list, message)


@shared_task
def send_notification_to_eligible_member(eligible_member_id, community_name, community_id):
    '''function to send notification to eligible promoter
     after he becomes eligible to become admin to a community'''

    fcm_token = get_token_for_fcm(eligible_member_id)
    if fcm_token:
        token_list = []
        token_list.append(fcm_token)

        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': "You are now eligible to become a promoter of this community",
            'route': 'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_referred_member(referred_member_id, joined_member_name, community_name, community_id,
                                         referal_count):
    '''function to send notification to referred member(who is referring)'''
    fcm_token = get_token_for_fcm(referred_member_id)

    if fcm_token:
        token_list = []
        token_list.append(fcm_token)
        if referal_count == 1:

            sub_title = str(joined_member_name) + " has shown interest to join. You have referred " + str(
                referal_count) + " member to the community"
        elif referal_count > 1:
            sub_title = str(joined_member_name) + " has shown interest to join. You have referred " + str(
                referal_count) + " members to the community"

        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': sub_title,
            'route': 'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_referred_member_in_active_community(referred_member_id, joined_member_name, community_name,
                                                             community_id, referal_count):
    '''function to send notification to referred member(who is referring)'''
    fcm_token = get_token_for_fcm(referred_member_id)

    if fcm_token:
        token_list = []
        token_list.append(fcm_token)
        if referal_count == 1:
            sub_title = str(joined_member_name) + " has joined this community. You have referred " + str(
                referal_count) + " member to the community"
        elif referal_count > 1:
            sub_title = str(joined_member_name) + " has joined this community. You have referred " + str(
                referal_count) + " members to the community"

        message = {}
        message['payload'] = {
            'title': str(community_name),
            'sub_title': sub_title,
            'route': 'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
    else:
        print('No FCM token to send message')


@shared_task
def send_notification_to_all_admins(community_id, name, current_promoter_id):
    '''function to send notification to community admins'''
    try:
        connection = get_connection()
        curr = connection.cursor()
        sql = "select member_id_id from togther_members where community_id_id= " + str(
            community_id) + " and (state=1 or state=2)"
        curr.execute(sql)
        admins = curr.fetchall()
        token_list = []
        for admin in admins:
            if str(current_promoter_id) != str(admin[0]):
                fcm_token = get_token_for_fcm(admin[0])
                token_list.append((fcm_token))

        community_name = get_community_name(community_id)
        message = {}
        message['payload'] = {
            'title': community_name,
            'sub_title': str(name) + ' is also a promoter now',
            'route': 'route://community?community_id=' + str(community_id)
        }
        send_notification_to_multiple_devices(token_list, message)
        curr.close()

    except (Exception, psycopg2.Error) as error:

        print("Error while connecting to PostgreSQL", error)


# utility functions
def get_referred_members_of_a_member(community_id, member_id):
    community = get_object_or_404(Community, pk=community_id)
    referred_member = User.objects.get(pk=member_id)

    member_list = []
    total_referals = Referal.objects.filter(member=referred_member, community=community)

    if total_referals.exists():
        for interested_member in total_referals:
            mem_id = interested_member.invited_member.id
            member = Members.objects.filter(member_id=mem_id, community_id=community_id)
            if member.exists():
                if member[0].state == 4:
                    member_list.append(member[0].member_id.id)

    return member_list


@shared_task
def send_notification_to_incomplete_profile(member_id, community_id, community_state, community_name, time_in_hrs):
    '''function to send notification to users who pressed skip when joining link was sent'''
    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=time_in_hrs, days=0)
    task_name = str(community_id) + "_" + str(member_id) + "_send_notification_to_incomplete_profile"
    args = [member_id, community_id, community_state, community_name, time_in_hrs]
    task_path = "collabmates_api.notification.send_notification_to_incomplete_profile_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)


@app.task
def send_notification_to_incomplete_profile_scheduled(member_id, community_id, community_state, community_name,
                                                      time_in_hrs):
    # check if they created the profile.
    community_answers = communityAnswers.objects.filter(community_id=community_id, member_id=member_id)

    if community_answers.exists():
        pass

    else:
        notification_list = []

        notification_details = get_token_for_fcm(member_id, flag=True)

        temp = {
            'id': member_id,
            'fcm_token': notification_details[0],
            'mobile_os': notification_details[1],
        }

        notification_list.append(temp)

        message = {
            'payload': {
                'title': "Complete your profile!",
                'sub_title': "Get full access to " + community_name,
                'route': 'route://community?community_id=' + str(community_id)
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.CREATE_PROFILE
            }
        }

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)


@shared_task
def send_login_dropoff_notification(token, platform_code):
    '''send notification to users who did not login after 2 hour'''

    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=2, days=0)
    task_name = str(token) + "_send_login_dropoff_notification"
    args = [token, platform_code]
    task_path = "collabmates_api.notification.send_login_dropoff_notification_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)


@app.task
def send_login_dropoff_notification_scheduled(token, platform_code):
    user = Userinfo.objects.filter(fcm_token=token)

    if user.exists():
        return

    else:
        temp = {
            'id': None,
            'fcm_token': token,
            'mobile_os': platform_code,
        }

        notification_list = [temp]

        message = {
            'payload': {
                'title': "Finish signing up!",
                'sub_title': "Click here to sign up and meet like-minded people and have relevant conversations."
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.HOME,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.LOGIN_DROP_OFF
            }
        }
        notification_meta(notification_list, message)


@app.task
def send_morning_pending_request_notification():
    ''' send morning notification at 8 am '''
    print('sending notification')
    Members.objects.filter(community_id=49063, member_id=504).update(state=3)
    members = Members.objects.filter(state=member_states.PENDING_MEMBER)
    communities = []
    for member in members:
        if member.community_id not in communities:
            communities.append(member.community_id)

    # communities = Community.objects.filter(pk__in=)
    for community in communities:
        members = Members.objects.filter(community_id=community.id)

        pending_members = members.filter(state=member_states.PENDING_MEMBER)
        pending_members_count = pending_members.count()

        if pending_members_count > 0:
            promoters = members.filter(state=member_states.ADMIN)
            notification_list = []
            for promoter in promoters:
                notification_details = get_token_for_fcm(promoter.member_id.id, flag=True)
                temp = {
                    'id': promoter.member_id.id,
                    'fcm_token': notification_details[0],
                    'mobile_os': notification_details[1],
                }

                notification_list.append(temp)

            message = {
                'payload': {
                    "title": str(community.name),
                    "sub_title": str(pending_members_count) +
                                 " members are awaiting your approval to join the community.",
                    "route": 'route://member_approve?' + 'community_id=' + str(community.id) + "&" +
                             "community_name=" + str(community.name)
                },
                'category': {
                    NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                    NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.N_PENDING_REQUESTS
                }
            }

            if pending_members_count == 1:
                message['payload']['sub_title'] = "1 member is awaiting your approval to join the community."

            message = TasksHelper.add_community_info_to_notification_payload(message, community.id)
            notification_meta(notification_list, message)


@shared_task
def send_notification_to_join_drop_off(member_id, community_id, aj, time_in_hrs):
    '''function to send notification to users who opened the private link but did not joint the community'''
    start_time = time.time()
    start_time = add_relative_time_to_epoch(start_time, minutes=0, hours=time_in_hrs, days=0)
    task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
    args = [member_id, community_id, aj, time_in_hrs]
    task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)


@app.task
def send_notification_to_join_drop_off_scheduled(member_id, community_id, aj, time_in_hrs):
    # check if they created the profile.
    member = Members.objects.filter(community_id=community_id, member_id=member_id)

    if member.exists():
        pass

    else:
        user_instance = User.objects.get(pk=member_id)
        member_name = user_instance.userinfo.name
        community_instance = Community.objects.get(id=community_id)
        community_name = community_instance.name

        notification_list = []

        notification_details = get_token_for_fcm(member_id, flag=True)

        temp = {
            'id': member_id,
            'fcm_token': notification_details[0],
            'mobile_os': notification_details[1],
        }

        notification_list.append(temp)

        message = {}
        if aj == "":
            message = {
                'payload': {
                    'title': str(community_name),
                    'sub_title': "Apply to join this community and meet like-minded people. ",
                    'route': 'route://community?community_id=' + str(community_id)
                },
                'category': {
                    NOTIFICATION_CATEGORY_KEY: NotificationCategories.HOME,
                    NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.PRIVATE_LINK_DROP_OFF_30
                }

            }

            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)

            notification_meta(notification_list, message)

        else:
            message = {
                'payload': {
                    'title': str(community_name),
                    'sub_title': "Don't miss relevant conversations. Click here to join and meet like-minded people. ",
                    'route': 'route://community?community_id=' + str(community_id) + '&aj=' + str(aj)
                },
                'category': {
                    NOTIFICATION_CATEGORY_KEY: NotificationCategories.HOME,
                    NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.PUBLIC_LINK_DROP_OFF
                }
            }

            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)

            notification_meta(notification_list, message)

            expiry_instance = communityExpiryCodes.objects.filter(community=community_instance, unique_code=aj)

            if expiry_instance.exists():
                time_to_sleep = expiry_instance[0].created_at + expiry_instance[0].expire_duration - int(
                    time.time()) - 30 * 60
                start_time = expiry_instance[0].created_at + expiry_instance[0].expire_duration - 30 * 60
            else:
                time_to_sleep = -1

            if time_to_sleep > 0:
                task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
                expiry_time = expiry_instance[0].created_at + expiry_instance[0].expire_duration
                args = [member_id, community_id, aj, expiry_time, notification_list]
                task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled_2"
                kwargs = {}
                celerybeatask = CeleryBeatTask()
                celerybeatask.terminate_task(task_name)
                celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                        date_time=start_time, interval=False, crontab=True)
                # time.sleep(time_to_sleep)


@app.task
def send_notification_to_join_drop_off_scheduled_2(member_id, community_id, aj, time_in_hrs, notification_list):
    member = Members.objects.filter(community_id=community_id, member_id=member_id)
    message = {}
    # member_name = user_instance.userinfo.name
    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name

    if member.exists():
        return

    message = {
        'payload': {
            'title': 'Invitation link about to expire!',
            'sub_title': "Don't miss relevant conversations in " + str(
                community_name) + ". Click here to join and meet like-minded people.",
            'route': 'route://community?community_id=' + str(community_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.HOME,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.PRIVATE_LINK_DROP_OFF
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)

    notification_meta(notification_list, message)

    # send notification after 6 hours when of expiry
    # time_to_sleep += 30*60 + 6*60*60
    # time.sleep(time_to_sleep)
    start_time = time.time()
    task_name = str(member_id) + "_" + str(community_id) + "_send_notification_to_join_drop_off"
    args = [member_id, community_id, aj]
    task_path = "collabmates_api.notification.send_notification_to_join_drop_off_scheduled_3"
    kwargs = {}
    celerybeatask = CeleryBeatTask()
    celerybeatask.terminate_task(task_name)
    celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                            date_time=start_time, interval=False, crontab=True)
    #
    # send notification after 6 hours after link expire
    start_time = add_relative_time_to_epoch(start_time, minutes=30, hours=6, days=0)


@app.task
def send_notification_to_join_drop_off_scheduled_3(member_id, community_id, aj):
    member = Members.objects.filter(community_id=community_id, member_id=member_id)

    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name

    expiry_instance = communityExpiryCodes.objects.filter(community=community_instance, unique_code=aj)
    member_name = expiry_instance.promoter.userinfo.name
    if member.exists():
        return

    notification_list = []

    notification_details = get_token_for_fcm(expiry_instance[0].promoter.id, flag=True)

    temp = {
        'id': expiry_instance[0].promoter.id,
        'fcm_token': notification_details[0],
        'mobile_os': notification_details[1],
    }

    notification_list.append(temp)

    message = {
        'payload': {
            'title': member_name + 'may need new invitation!',
            'sub_title': "Your private invitation for joining " + str(
                community_name) + "has expired. Please resend them invite link.",
            'route': 'route://community?community_id=' + str(community_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.HOME,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.EXPIRED_PRIVATE_LINK_DROP_OFF
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)

    notification_meta(notification_list, message)


@app.task
@shared_task
def send_notification_for_directory_creation(community_id, start_time, day=0):
    # add update profile notification as well
    # return

    community_instance = Community.objects.get(id=community_id)
    community_name = community_instance.name

    members = Members.objects.filter(community_id=community_id, state__in=[1, 4, 9], edit_required=True)

    message = {}

    message['payload'] = {
        "title": str(community_name),
        "sub_title": "",
        'route': '//route://community_collabcard?community_id=' + str(community_id) + '&community_name=' + str(
            community_instance.name)
    }

    if day == 0 and members.exists():
        # get tomorrow 9 am
        # start_time = datetime.fromtimestamp(start_time)
        start_time = datetime.fromtimestamp(start_time + (24 * 60 * 60))
        start_time = start_time.replace(hour=9, minute=0) + timedelta(days=3)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + str(start_time) + "_3_send_notification_for_directory_creation"
        day = 3
        args = [community_id, date_time, day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}

        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 3 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9, minute=0) + timedelta(days=2)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name = str(community_id) + str(start_time) + "_3_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + str(start_time) + "_5_send_notification_for_directory_creation"
        day = 5
        args = [community_id, date_time, day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(
                member_name) + ", we are reminding you to complete your directory profile. Without an updated profile, you won’t have seamless access to the community. "
            message['payload']['route'] = "route://member_profile?member_id=" + str(
                member.member_id.id) + "&community_id=" + str(community_id) + '&edit=true'
            message['category'] = {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.UPDATE_PROFILE
            }
            notification_list.append(temp)
            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 5 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9, minute=0) + timedelta(days=2)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name = str(community_id) + str(start_time) + "_5_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + str(start_time) + "_7_send_notification_for_directory_creation"
        day = 7
        args = [community_id, date_time, day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(
                member_name) + ", please update your profile now to take full advantage of our networking features. This is mandatory for all the members. "
            message['payload']['route'] = "route://member_profile?member_id=" + str(
                member.member_id.id) + "&community_id=" + str(community_id) + '&edit=true'
            message['category'] = {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.UPDATE_PROFILE
            }
            notification_list.append(temp)
            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 7 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9, minute=0) + timedelta(days=8)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name = str(community_id) + str(start_time) + "_7_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + str(start_time) + "_15_send_notification_for_directory_creation"
        day = 15
        args = [community_id, date_time, day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(
                member_name) + ", it has been over 15 days you joined us. Please update your profile now to take full advantage of " + str(
                community_name) + " and connect with others."
            message['payload']['route'] = "route://member_profile?member_id=" + str(
                member.member_id.id) + "&community_id=" + str(community_id) + '&edit=true'
            message['category'] = {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.UPDATE_PROFILE
            }
            notification_list.append(temp)
            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return

    elif day == 15 and members.exists():
        start_time = datetime.fromtimestamp(start_time)
        start_time = start_time.replace(hour=9, minute=0) + timedelta(days=15)
        # start_time = start_time + timedelta(minutes=2)
        date_time = start_time.timestamp()
        task_name = str(community_id) + str(start_time) + "_15_send_notification_for_directory_creation"
        celerybeatask = CeleryBeatTask()
        celerybeatask.terminate_task(task_name)
        celerybeatask = CeleryBeatTask()
        task_name = str(community_id) + str(start_time) + "_30_send_notification_for_directory_creation"
        day = 30
        args = [community_id, date_time, day]
        task_path = "collabmates_api.notification.send_notification_for_directory_creation"
        kwargs = {}
        for member in members:
            member_name = member.member_id.userinfo.name
            notification_list = []
            notification_details = get_token_for_fcm(member.member_id.id, flag=True)
            temp = {
                'id': member.member_id.id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1],
            }
            message['payload']['sub_title'] = str(
                member_name) + ", it has been over 30 days you joined us. Please update your profile and improve your chances of connecting with like-minded folks."
            message['payload']['route'] = "route://member_profile?member_id=" + str(
                member.member_id.id) + "&community_id=" + str(community_id) + '&edit=true'
            message['category'] = {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.UPDATE_PROFILE
            }
            notification_list.append(temp)
            message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
            notification_meta(notification_list, message)
        celerybeatask.create_dynamic_clery_task(args, kwargs, task_name, task_path,
                                                date_time=date_time, interval=False, crontab=True)
        return


@shared_task
def send_notification_for_new_promoter(promoter_id, member_id, community_id, custom_title=None):
    community_instance = Community.objects.get(pk=community_id)
    promoter_instance = User.objects.get(pk=promoter_id)
    member_instance = User.objects.get(pk=member_id)
    community_name = community_instance.name
    promoter_name = promoter_instance.userinfo.name

    member_fcm_token = member_instance.userinfo.fcm_token
    member_mobile_os = member_instance.userinfo.mobile_os

    notification_list = []

    user_details = {
        "id": member_id,
        'fcm_token': member_fcm_token,
        'mobile_os': member_mobile_os,
    }
    notification_list.append(user_details)

    message = {
        'payload': {
            'title': community_name,
            'sub_title': f"{promoter_name} has added you in the management team of the community and assigned you the title of {custom_title}",
            'route': f'route://member_profile/{member_id}?community_id={community_id}&member_id={member_id}'
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.BECAME_ADMIN
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_custom_title_changed(promoter_id, member_id, community_id, custom_title):
    community_instance = Community.objects.get(pk=community_id)
    promoter_instance = User.objects.get(pk=promoter_id)
    member_instance = User.objects.get(pk=member_id)
    community_name = community_instance.name
    promoter_name = promoter_instance.userinfo.name

    member_fcm_token = member_instance.userinfo.fcm_token
    member_mobile_os = member_instance.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": int(member_id),
        'fcm_token': member_fcm_token,
        'mobile_os': member_mobile_os,
    }
    notification_list.append(user_details)

    if custom_title is None:
        custom_title = "Community Manager"

    message = {
        'payload': {
            'title': community_name,
            'sub_title': f"{promoter_name} has assigned you the title of {custom_title}",
            'route': f'route://member_profile/{member_id}?community_id={community_id}&member_id={member_id}'
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.CM_TITLE_ASSIGNED
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_ownership_transfered(prev_owner_id, new_owner_id, community_id):
    community_instance = Community.objects.get(pk=community_id)
    pre_owner = User.objects.get(pk=prev_owner_id)
    new_owner = User.objects.get(pk=new_owner_id)
    community_name = community_instance.name
    prev_owner_name = pre_owner.userinfo.name

    new_owner_fcm_token = new_owner.userinfo.fcm_token
    new_owner_mobile_os = new_owner.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": new_owner_id,
        'fcm_token': new_owner_fcm_token,
        'mobile_os': new_owner_mobile_os,
    }
    notification_list.append(user_details)

    message = {
        'payload': {
            "title": community_name,
            "sub_title": f"{prev_owner_name} has transferred the ownership of the community to you.",
            'route': f'route://member_profile/{new_owner_id}?community_id={community_id}&member_id={new_owner_id}'
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.BECAME_OWNER
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_removed_member(admin_id, removed_user_id, community_id):
    community_instance = Community.objects.get(pk=community_id)
    admin = User.objects.get(pk=admin_id)
    removed_user = User.objects.get(pk=removed_user_id)
    community_name = community_instance.name
    admin_name = admin.userinfo.name

    removed_user_fcm_token = removed_user.userinfo.fcm_token
    removed_user_mobile_os = removed_user.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": removed_user_id,
        'fcm_token': removed_user_fcm_token,
        'mobile_os': removed_user_mobile_os,
    }
    notification_list.append(user_details)

    message = {
        'payload': {
            'title': "LikeMinds",
            'sub_title': f"{admin_name} has removed you from the {community_name}. Click here to know the reasons.",
            'route': '//route://community_collabcard?community_id='
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MEMBER_REMOVED
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    # notification_meta(notification_list, message)


@shared_task
def send_notification_for_right_given_to_member(user_id, community_id, rights_added):
    community_instance = Community.objects.get(pk=community_id)
    user_instance = User.objects.get(pk=user_id)
    community_name = community_instance.name

    user_fcm_token = user_instance.userinfo.fcm_token
    user_mobile_os = user_instance.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": user_id,
        'fcm_token': user_fcm_token,
        'mobile_os': user_mobile_os,
    }
    notification_list.append(user_details)

    for right_id in rights_added:
        right = memberRights.objects.get(pk=right_id)
        right_title = str(right.title).lower()
        card_type = 0
        if right.state == member_rights.MEMBER_RIGHT_CREATE_ROOMS:
            card_type = 0
        elif right.state == member_rights.MEMBER_RIGHT_CREATE_POLL:
            card_type = 3
        elif right.state == member_rights.MEMBER_RIGHT_CREATE_EVENT:
            card_type = 2
        
        # If right state is a feed member right, then skip the notification
        elif right.state in (member_rights.FEED_MEMBER_RIGHTS):
            continue
        
        category = NotificationCategories.MODERATION

        route = f"route://create_chatroom?community_id={community_id}&community_name={community_name}&type={card_type}"
        sub_title = f"The Community Manager has reactivated your privilege to {right_title}"
        subcategory = NotificationSubCategories.PERMISSION_FOR_CHATROOM_CREATION

        if right.state == member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM:
            sub_title = "The Community Manager has reactivated your privilege to respond inside chat rooms."
            route = f"route://community_collabcard?community_id={community_id}&community_name={community_name}"
            subcategory = NotificationSubCategories.PERMISSION_FOR_RESPONDING

        elif right.state == member_rights.MEMBER_RIGHT_INVITE_PRIVATE_LINK:
            sub_title = "You have earned the privilege to invite new members to the community via private links!"
            route = f"route://community?community_id={community_id}&share=true"
            subcategory = NotificationSubCategories.PERMISSION_FOR_INVITING_MEMBERS

        elif right.state == member_rights.MEMBER_RIGHT_AUTO_APPROVE:
            sub_title = "You have earned the privilege to have your chat rooms auto-approved. Your chat rooms will be instantenously posted."
            route = f"route://community?community_id={community_id}&share=true"
            subcategory = NotificationSubCategories.PERMISSION_FOR_CHATROOMS_AUTO_APPROVAL

        message = {
            'payload': {
                'title': community_name,
                'sub_title': sub_title,
                'route': route
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: category,
                NOTIFICATION_SUB_CATEGORY_KEY: subcategory
            }
        }

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)


@shared_task
def send_notification_for_pending_chatroom_approved_or_rejected(card_id, is_approved=False):
    card_instance = Collabcard.objects.get(pk=card_id)
    chatroom_title = card_instance.header
    card_creator = card_instance.user
    community_name = card_instance.community.name
    card_creator_first_name = card_creator.userinfo.name.split(" ")[0]
    user_fcm_token = card_creator.userinfo.fcm_token
    user_mobile_os = card_creator.userinfo.mobile_os

    message = {}
    notification_list = []

    user_details = {
        "id": card_creator.id,
        'fcm_token': user_fcm_token,
        'mobile_os': user_mobile_os,
    }
    notification_list.append(user_details)

    if is_approved:
        sub_title = f"Hurray! {card_creator_first_name}, your chat room ‘{chatroom_title}’ has been approved."
        route = f"route://chatroom_detail?chatroom_id={card_id}"
        category = NotificationCategories.MODERATION
        subcategory = NotificationSubCategories.CHATROOM_APPROVED

    else:
        sub_title = f"{card_creator_first_name}, we are sorry to inform you that your chat room ‘{chatroom_title}’ was not approved."
        route = "route://main"
        category = NotificationCategories.MODERATION
        subcategory = NotificationSubCategories.CHATROOM_REJECTED

    message = {
        'payload': {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: category,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, card_instance.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_reports(report_id, community_id, reported_by_user_id,
                                  card_id=None, conversation_id=None, reported_on_user_id=None,
                                  report_type=None, reason=None, tag_id=None):
    reported_by_user = User.objects.get(pk=reported_by_user_id)
    reported_by_user_name = reported_by_user.userinfo.name
    community_instance = Community.objects.get(pk=community_id)
    community_name = community_instance.name

    subcategory = ""
    sub_title_prefix = ""
    reported_on_user = None
    print("report_type >>>>>   ", report_type)

    if report_type == 0:
        reported_on_user = User.objects.get(pk=reported_on_user_id)
        sub_title_prefix = reported_on_user.userinfo.name
        subcategory = NotificationSubCategories.MEMBER_REPORTED

    elif report_type == 1:
        card_instance = Collabcard.objects.get(pk=card_id)
        reported_on_user = card_instance.user
        sub_title_prefix = card_instance.header
        subcategory = NotificationSubCategories.CHATROOM_REPORTED

    elif report_type == 2:
        conversation_instance = card_answers.objects.get(pk=conversation_id)
        reported_on_user = conversation_instance.user
        chatroom_name = conversation_instance.card.header
        sub_title_prefix = f"A message in ‘{chatroom_name}'"
        subcategory = NotificationSubCategories.RESPONSE_REPORTED

    if tag_id:
        report = Report_Tags.objects.get(tag_id=tag_id)
        reason = report.tag_name

    sub_title = f"{sub_title_prefix} was reported by {reported_by_user_name} citing the reason: '{reason}’."
    route = f"route://review_reports?community_id={community_id}&community_name={community_name}&report_id={report_id}"

    message = {}
    notification_list = []
    message['payload'] = {
        "title": community_name,
        "sub_title": sub_title,
        'route': route
    }

    if subcategory:
        message['category'] = {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory
        }

    is_promoter = False
    parent_cm_list = []

    if reported_on_user:
        member_instance = Members.objects.filter(community_id=community_instance, member_id=reported_on_user)
        if member_instance.exists():
            member_instance = member_instance[0]
            if member_instance.is_owner:
                return
            elif member_instance.state == member_states.ADMIN:
                is_promoter = True
                parent_cm_list = json.loads(member_instance.parent_cm_list) if member_instance.parent_cm_list else []
                parent_cm_list = set(parent_cm_list)

    if report_type == 0:
        admin_ids = list(userAdminRights.objects.filter(community=community_instance,
                                                        right__state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS).values_list(
            "user__id",
            flat=True))
        admin_ids = set(admin_ids)
    else:
        admin_ids = list(userAdminRights.objects.filter(community=community_instance,
                                                        right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS).values_list(
            "user__id", flat=True))
        admin_ids = set(admin_ids)

    admin_ids = {str(admin_id) for admin_id in admin_ids}

    if is_promoter:
        admin_ids = list(admin_ids & parent_cm_list)
    else:
        admin_ids = list(admin_ids)

    users = User.objects.filter(id__in=admin_ids)

    for user in users:
        user_details = {
            "id": user.id,
            'fcm_token': user.userinfo.fcm_token,
            'mobile_os': user.userinfo.mobile_os,
        }

        notification_list.append(user_details)

    if report_type in [0, 1]:  # will remove check after implementing conversation delete
        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)


@shared_task
def send_notification_for_chatroom_deleted(deleted_by_user_id, card_id, community_id):
    deleted_by_user = User.objects.get(pk=deleted_by_user_id)
    deleted_by_user_name = deleted_by_user.userinfo.name
    community_instance = Community.objects.get(pk=community_id)
    community_name = community_instance.name

    card_instance = Collabcard.objects.get(pk=card_id)
    card_name = card_instance.header
    sub_title = f"The Community Manager has deleted {card_name}. Click here to know the reasons."
    route = ""

    category = NotificationCategories.MODERATION
    subcategory = NotificationSubCategories.CHATROOM_DELETED

    notification_list = []

    message = {
        'payload': {
            "title": community_name,
            "sub_title": sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: category,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory
        }
    }

    following_member_ids = list(
        conversationEngage.objects.filter(card=card_instance).values_list("user__id", flat=True))

    users = User.objects.filter(id__in=following_member_ids)

    for user in users:
        user_details = {
            "id": user.id,
            'fcm_token': user.userinfo.fcm_token,
            'mobile_os': user.userinfo.mobile_os,
        }

        notification_list.append(user_details)

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    # notification_meta(notification_list, message)


@shared_task
def send_notification_for_right_given_to_manager(user_id, community_id, rights_added):
    try:
        community_instance = Community.objects.get(pk=community_id)
    except Community.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - community id {community_id} does not exist")
        return

    try:
        user_instance = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - user id {user_id} does not exist")
        return

    community_name = community_instance.name

    notification_list = []

    user_details = get_user_fcm_details(user_instance=user_instance)
    notification_list.append(user_details)

    for right_id in rights_added:
        right = adminRights.objects.get(pk=right_id)

        route = f"route://community?community_id={community_id}&community_name={community_name}"
        sub_title = ENABLE_MANAGER_ADD_MANAGER_RIGHT

        if right.state == manager_rights.MANAGER_RIGHT_DELETE_ROOMS:
            sub_title = ENABLE_MANAGER_RIGHT_DELETE_ROOMS

        elif right.state == manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS:
            sub_title = ENABLE_MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS

        elif right.state == manager_rights.MANAGER_RIGHT_EDIT_COMMUNITY:
            sub_title = ENABLE_MANAGER_RIGHT_EDIT_COMMUNITY

        elif right.state == manager_rights.MANAGER_RIGHT_VIEW_CONTACT_INFO:
            sub_title = ENABLE_MANAGER_RIGHT_VIEW_CONTACT_INFO

        message = {
            'payload': {
                'title': community_name,
                'sub_title': sub_title,
                'route': route
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
                NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.CM_PERMISSION_UPDATED
            }
        }

        message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
        notification_meta(notification_list, message)


@shared_task
def send_notification_for_removed_cm(user_id, community_id):
    try:
        community_instance = Community.objects.get(pk=community_id)
    except Community.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - community id {community_id} does not exist")
        return

    try:
        user_instance = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - user id {user_id} does not exist")
        return

    community_name = community_instance.name

    notification_list = []

    user_details = get_user_fcm_details(user_instance=user_instance)
    notification_list.append(user_details)

    sub_title = NOTIFICATION_SUB_TITLE_FOR_CM_REMOVED
    route = f"route://community?community_id={community_id}&community_name={community_name}"
    category = NotificationCategories.MODERATION
    subcategory = NotificationSubCategories.CM_PERMISSION_UPDATED

    message = {
        'payload': {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: category,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


def send_intro_room_evening_notifications():
    current_time = TimeUtilities.current_time_in_sec()
    all_communities = Community.objects.all()
    all_members = Members.objects.all()

    # Intro settings ON
    enabled_intro_settings = ModelUtilities.get_model_filter(CommunitySettings,
                                                             {'setting_type': community_setting_types.INTRO_ROOM,
                                                              'enabled': True})

    if not enabled_intro_settings:
        return

    communities = list(enabled_intro_settings.values_list('community_id', flat=True))

    # get intro rooms in last 24 hours (86400 seconds)
    new_intro_rooms = ModelUtilities.get_model_filter(Collabcard,
                                                      {'date_epoch__gte': current_time - INTRO_ROOM_LOOKBACK_PERIOD,
                                                       'type': card_types.CARD_INTRO,
                                                       'is_deleted': False,
                                                       'community__in': communities})

    communities = new_intro_rooms.values('community').distinct()

    for community_id in communities:
        community = all_communities.get(id=community_id['community'])
        community_members = all_members.filter(community_id=community)
        community_intro_rooms = new_intro_rooms.filter(community=community)
        community_intro_rooms_count = community_intro_rooms.count()

        if community_intro_rooms_count:
            new_members = get_new_member_list(community_intro_rooms)

            for member in community_members:

                if member.member_id_id in new_members:
                    continue

                user_instance = member.member_id
                message = get_message_for_evening_notification(community_intro_rooms, user_instance, community)

                if not message:
                    continue

                notification_list = get_notification_list_intro_notification(user_instance)
                message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
                notification_meta(notification_list, message)


def get_new_member_list(community_intro_rooms):
    """
    Return the list of users who joined in last 24 hours
    """
    new_members = []
    for community_intro_room in community_intro_rooms:
        new_members.append(community_intro_room.user_id)
    return new_members


def get_message_for_evening_notification(community_intro_rooms, user_instance, community):
    """
    Generate and return notification body based on the number of new members
    """

    community_intro_rooms_count = community_intro_rooms.count()

    if community_intro_rooms_count == 1:
        joined_member = community_intro_rooms[0].user
        title = INTRO_ROOM_NOTIFICATION_TITLE_SINGULAR
        sub_title = INTRO_ROOM_NOTIFICATION_SUBTITLE_SINGULAR % (
            user_instance.userinfo.name, joined_member.userinfo.name, community.name)
        route = INTRO_ROOM_NOTIFICATION_ROUTE_SINGULAR % community_intro_rooms[0].id

    else:
        master_intro_chatroom_filter = ModelUtilities.get_model_filter(Collabcard,
                                                                       {'community': community,
                                                                        'type': card_types.CARD_MASTER_INTRO})

        if not master_intro_chatroom_filter:
            return

        title = INTRO_ROOM_NOTIFICATION_TITLE_PLURAL
        sub_title = INTRO_ROOM_NOTIFICATION_SUBTITLE_PLURAL % (
            user_instance.userinfo.name, community.name, community_intro_rooms_count)
        route = INTRO_ROOM_NOTIFICATION_ROUTE_SINGULAR % master_intro_chatroom_filter[0].id

    message = {
        'payload': {
            "title": title,
            "sub_title": sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MEMBER_JOINED
        }
    }
    return message


def get_notification_list_intro_notification(user_instance):
    """
    Send the list of users devices that will receive notifications
    """
    notification_list = []
    user_details = get_user_fcm_details(user_instance=user_instance)
    notification_list.append(user_details)
    return notification_list


@shared_task
def send_notification_to_managers_when_member_leaves_community(user_id, community_id):
    try:
        community_instance = Community.objects.get(pk=community_id)
    except Community.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - community id {community_id} does not exist")
        return

    try:
        user_instance = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        error_logger.error(f"send_notification_for_removed_cm - user id {user_id} does not exist")
        return

    community_name = community_instance.name

    managers_ids = list(Members.objects
                        .filter(community_id=community_instance,
                                state=member_states.ADMIN)
                        .values_list("member_id__id", flat=True))

    notification_list = []
    for manager_id in managers_ids:
        user_details = {
            "id": manager_id
        }
        notification_list.append(user_details)

    sub_title = MEMBER_LEFT_COMMUNITY_NOTIFICATION_SUB_TITLE % user_instance.userinfo.name
    route = COMMUNITY_DETAIL_ROUTE % (community_id, community_name)

    message = {
        'payload': {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.MODERATION,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MEMBER_LEFT
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


def query_executer(query):
    """executes a query and returns a response"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(query)
        res = curr.fetchall()
        curr.close()

        return res

    except (Exception, psycopg2.Error) as error:
        error_logger.error(error)

        return []


def get_android_users_tokens_for_silent_sync_notification(community_id, member_id=None):
    if not member_id:
        sql = """SELECT togther_userDevices.fcm_token
                 FROM togther_members
                 INNER JOIN togther_userDevices
                     ON togther_members.member_id_id = togther_userDevices.user_id
                 WHERE togther_userDevices.mobile_os='Android'
                        AND togther_members.community_id_id=%s""" % (str(community_id))
    else:
        sql = """SELECT togther_userDevices.fcm_token
                 FROM togther_members
                 INNER JOIN togther_userDevices
                     ON togther_members.member_id_id = togther_userDevices.user_id
                 WHERE togther_userDevices.mobile_os='Android'
                        AND togther_members.community_id_id=%s
                        AND togther_members.member_id_id=%s""" % (str(community_id), str(member_id))

    result_set = query_executer(sql)

    token_list = []

    for data in result_set:
        token_list.append(data[0])

    return token_list


@shared_task
def send_sync_notification(notification_dict):
    if not SyncNotificationTypes.has_value(notification_dict['sync_notification_type']):
        error_logger.error("Invalid sync notification type")

        return

    chatroom_id = notification_dict.get('chatroom_id')

    if chatroom_id:
        community_instance = Collabcard.get_community_of_chatroom_or_none(chatroom_id)

        if community_instance:
            notification_dict['community_id'] = community_instance.id

    community_id = notification_dict.get('community_id')

    if not community_id:
        return

    message = {
        'payload': {
            'route': SYNC_NOTIFICATION_ROUTE
        }
    }

    token_list = []

    if notification_dict['sync_notification_type'] == SyncNotificationTypes.ALL_MEMBERS.value:
        token_list = get_android_users_tokens_for_silent_sync_notification(community_id)

    elif notification_dict['sync_notification_type'] == SyncNotificationTypes.SINGLE_MEMBER.value:
        token_list = get_android_users_tokens_for_silent_sync_notification(community_id,
                                                                           notification_dict['member_id'])

    if len(token_list) > 0:
        send_notification_for_android(token_list, message)


@shared_task
def send_pin_chatroom_notification(community_id, member_id, chatroom_id):
    member_filter = Members.objects.filter(community_id=community_id).filter(Q(state=member_states.ADMIN)
                                                                             | Q(state=member_states.MEMBER)
                                                                             | Q(
        state=member_states.PROFILE_UNAVAILABLE)).prefetch_related('member_id')

    card_instance = Collabcard.get_chatroom_or_None(chatroom_id)

    if not card_instance:
        return

    notification_list = []
    promoter_name = ""
    for data in member_filter:
        user_id = data.member_id.id

        if str(user_id) == member_id:
            promoter_name = data.member_id.userinfo.name
            continue

        temp = {
            'id': user_id
        }
        notification_list.append(temp)

    message = {
        'payload': {
            'title': PIN_CHATROOM_TITLE,
            'sub_title': PIN_SUBTITLE % (promoter_name, get_title_from_collabcard(card_instance)),
            'route': PIN_ROUTE % str(card_instance.id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.CHATROOM_PINNED_BY_CM
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, community_id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_removed_secret_room_participant(user_id, chatroom_id):
    try:
        chatroom_instance = Collabcard.objects.get(pk=chatroom_id)
    except Collabcard.DoesNotExist:
        error_logger.error(
            f"send_notification_for_removed_secret_room_participant - chatroom with id {chatroom_id} does not exist")
        return

    community_name = chatroom_instance.community.name

    notification_list = []

    temp = {
        'id': user_id
    }

    notification_list.append(temp)

    sub_title = SECRET_CHATROOM_REMOVED_SUBTITLE % chatroom_instance.header
    route = SECRET_CHATROOM_REMOVED_ROUTE
    category = NotificationCategories.CHATROOM
    subcategory = NotificationSubCategories.MEMBER_REMOVED_FROM_CHATROOM

    message = {
        'payload': {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: category,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, chatroom_instance.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_new_secret_room_participant(user_id, chatroom_id):
    try:
        chatroom_instance = Collabcard.objects.get(pk=chatroom_id)
    except Collabcard.DoesNotExist:
        error_logger.error(
            f"send_notification_for_new_secret_room_participant - chatroom id {chatroom_id} does not exist")
        return

    community_name = chatroom_instance.community.name

    notification_list = []

    temp = {
        'id': user_id
    }

    notification_list.append(temp)

    sub_title = SECRET_CHATROOM_ADD_SUBTITLE % chatroom_instance.header
    route = SECRET_CHATROOM_ADD_ROUTE % chatroom_id
    category = NotificationCategories.CHATROOM
    subcategory = NotificationSubCategories.MEMBER_ADDED_TO_SECRET_CHATROOM

    message = {
        'payload': {
            'title': community_name,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: category,
            NOTIFICATION_SUB_CATEGORY_KEY: subcategory
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, chatroom_instance.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_to_message_creator_on_reaction(user_id, chatroom_id, conversation_id, reaction):
    if chatroom_id is not None:
        chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

        if chatroom_instance is None:
            error_logger.error(
                f"send_notification_to_message_creator_on_reaction - chatroom id {chatroom_id} does not exist")
            return

        creator_dict = {
            'id': chatroom_instance.user_id,
            'chatroom_id': chatroom_id
        }

    elif conversation_id is not None:
        conversation_instance = card_answers.get_conversation_or_None(conversation_id)

        if conversation_instance is None:
            error_logger.error(
                f"send_notification_to_message_creator_on_reaction - conversation id {conversation_id} does not exist")
            return

        chatroom_instance = conversation_instance.card
        chatroom_id = chatroom_instance.id

        creator_dict = {
            'id': conversation_instance.user_id,
            'chatroom_id': conversation_instance.card_id
        }

    else:
        return

    reacted_userinfo_instance = Userinfo.get_userinfo_or_None(user_id)

    if reacted_userinfo_instance is None:
        return

    # if user reacts on his own message, don't send notification
    if any([creator_dict['id'] == reacted_userinfo_instance.user_id_id,
            ModelUtilities.get_model_filter(collabcardState, {'user_id': creator_dict['id'],
                                                              'card_id': creator_dict['chatroom_id'],
                                                              'mute_status': True})]):
        return

    reacted_user_name = reacted_userinfo_instance.name

    title = chatroom_instance.header
    sub_title = MESSAGE_REACTIONS_NOTIFICATION_SUB_TITLE % (reacted_user_name, reaction)

    if conversation_id:
        route = MESSAGE_REACTIONS_CONVERSATION_NOTIFICATION_ROUTE % (chatroom_id, conversation_id)
    else:
        route = MESSAGE_REACTIONS_CHATROOM_NOTIFICATION_ROUTE % chatroom_id

    message = {
        'payload': {
            'title': title,
            'sub_title': sub_title,
            'route': route
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.USER_REACTED
        }
    }

    notification_list = [creator_dict]

    message = TasksHelper.add_community_info_to_notification_payload(message, chatroom_instance.community_id)

    notification_meta(notification_list, message)


@shared_task
def send_poll_conversation_creation_notification(card_id, poll_conversation_creator_id, conversation_id):
    card_instance = Collabcard.get_chatroom_or_None(card_id)

    if not card_instance:
        return

    print("poll conversation notification", card_instance)

    community_instance = card_instance.community

    userinfo_instance = Userinfo.objects.filter(user_id=poll_conversation_creator_id)

    if not userinfo_instance:
        return

    print("userinfo poll conversation", userinfo_instance)

    member_filter = Members.objects.filter(community_id=community_instance).filter(
        Q(state=member_states.MEMBER) | Q(state=member_states.ADMIN) | Q(state=member_states.PROFILE_UNAVAILABLE))

    if card_instance.is_secret:
        collabcardstate_user_ids = list(ModelUtilities.get_model_filter(collabcardState,
                                                                        {"card": card_instance,
                                                                         "remove": None,
                                                                         "follow_status": True,
                                                                         "mute_status": False}).values_list("user_id", flat=True))

        member_filter = member_filter.filter(member_id_id__in=collabcardstate_user_ids)

    notification_list = []

    message = {
        'payload': {
            'title': "Time to vote",
            'sub_title': POLL_CONVERSATION_SUBTITLE % (userinfo_instance[0].name, card_instance.header,
                                                       community_instance.name),
            'route': POLL_CONVERSATION_ROUTE % (community_instance.id, card_instance.id, conversation_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MICRO_POLL_CREATED
        }
    }

    for member in member_filter:

        if member.member_id_id == poll_conversation_creator_id:
            continue

        temp = {
            'id': member.member_id_id
        }

        notification_list.append(temp)

    print("notification_list", notification_list)

    message = TasksHelper.add_community_info_to_notification_payload(message, community_instance.id)
    notification_meta(notification_list, message)


@shared_task
def send_poll_conversation_creation_notification_v1(card_id, poll_conversation_creator_id, conversation_id):
    card_instance = Collabcard.get_chatroom_or_None(card_id)

    if not card_instance:
        return

    print("poll conversation notification", card_instance)

    community_instance = card_instance.community

    userinfo_instance = Userinfo.objects.filter(user_id=poll_conversation_creator_id)

    if not userinfo_instance:
        return

    print("userinfo poll conversation", userinfo_instance)

    current_time = TimeUtilities.current_time_in_milliseconds()

    filter_dict = {
        "card": card_instance,
        "remove": None,
        "follow_status": True,
        "mute_status": False
    }

    collabcardstate_user_ids = list(ModelUtilities.get_model_filter(collabcardState, filter_dict).filter(
        noti_state__in=[noti_states.ALL_MESSAGES, noti_states.DM_MENTION_REPLIES_POLL]).filter(
        Q(is_noti_paused=False) | (Q(is_noti_paused=True) & Q(unpause_noti_at__lte=current_time))
    ).values_list("user_id", flat=True))

    member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                              'member_id__in': collabcardstate_user_ids})

    notification_list = []

    message = {
        'payload': {
            'title': "Time to vote",
            'sub_title': POLL_CONVERSATION_SUBTITLE % (userinfo_instance[0].name, card_instance.header,
                                                       community_instance.name),
            'route': POLL_CONVERSATION_ROUTE % (community_instance.id, card_instance.id, conversation_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.MICRO_POLL_CREATED
        }
    }

    for member in member_filter:

        if member.member_id_id == poll_conversation_creator_id:
            continue

        temp = {
            'id': member.member_id_id
        }

        notification_list.append(temp)

    message = TasksHelper.add_community_info_to_notification_payload(message, community_instance.id)
    notification_meta(notification_list, message, is_broadcast_notification=True)


@shared_task
def send_notification_for_auto_follow_chatroom_for_all_members(chatroom_id, cm_id, user_ids):
    notification_list = []

    chatroom_instance = Collabcard.get_chatroom_or_None(chatroom_id)

    if not chatroom_instance:
        return

    userinfo_instance = Userinfo.get_userinfo_or_None(cm_id)

    if not userinfo_instance:
        return

    for user_id in user_ids:
        notification_list.append({"id": user_id})

    message = {
        'payload': {
            'title': CHATROOM_NOTIFICATION_OWNER_ADD_ALL_MEMBER_TITLE % (
                userinfo_instance.name, chatroom_instance.title),
            'sub_title': CHATROOM_NOTIFICATION_OWNER_ADD_ALL_MEMBER_SUBTITLE,
            'route': "route://chatroom_detail?chatroom_id=%s" % str(chatroom_id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.AUTO_FOLLOW_ENABLED,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, chatroom_instance.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_on_chatroom_topic_update(chatroom_id, current_user_id):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        return

    user_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                     {'card': card_instance, 'follow_status': True,
                                                      'is_tagged': False, 'remove': None}). \
                     values_list('user_id', flat=True))

    notification_list = []

    for user_id in user_list:

        if user_id == current_user_id:
            continue

        notification_list.append({'id': user_id})

    message = {
        'payload': {
            'title': CHATROOM_TOPIC_NOTIFICATION_TITLE,
            'sub_title': CHATROOM_TOPIC_NOTIFICATION_SUB_TITLE % card_instance.header,
            'route': CHATROOM_TOPIC_NOTIFICATION_ROUTE % str(card_instance.id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.CHATROOM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.TOPIC_UPDATED,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, card_instance.community.id)
    notification_meta(notification_list, message)


@shared_task
def send_notification_for_event_update(chatroom_id):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        return

    user_list = list(ModelUtilities.get_model_filter(collabcardState,
                                                     {'card': card_instance, 'attending_status': True,
                                                      'is_tagged': False, 'remove': None}).\
                     values_list('user_id', flat=True))

    notification_list = []

    for user_id in user_list:

        if user_id == card_instance.user_id:
            continue

        notification_list.append({'id': user_id})

    message = {
        'payload': {
            'title': card_instance.header,
            'sub_title': "Event details have been updated",
            'route': CHATROOM_DETAIL_NOTIFICATION_ROUTE % str(card_instance.id)
        }
    }

    notification_meta(notification_list, message)


@shared_task
def send_notification_on_dm_request_initiation(chatroom_id, current_user_id, current_user_name):
    card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

    if not card_instance:
        return

    filter_dict = {
        'card': card_instance,
        'follow_status': True,
        'remove': None
    }

    user_list = list(ModelUtilities.get_model_filter(collabcardState, filter_dict).values_list('user_id', flat=True))

    notification_list = []

    for user_id in user_list:

        if user_id == current_user_id:
            continue

        notification_list.append({'id': user_id})

    message = {
        'payload': {
            'title': DM_REQUEST_INITIATION_NOTIFICATION_TITLE,
            'sub_title': DM_REQUEST_INITIATION_NOTIFICATION_SUB_TITLE.format(current_user_name),
            'route': CHATROOM_TOPIC_NOTIFICATION_ROUTE % str(card_instance.id)
        },
        'category': {
            NOTIFICATION_CATEGORY_KEY: NotificationCategories.DM,
            NOTIFICATION_SUB_CATEGORY_KEY: NotificationSubCategories.DM_REQUEST_SENT,
        }
    }

    message = TasksHelper.add_community_info_to_notification_payload(message, card_instance.community.id)
    notification_meta(notification_list, message)

