import json
from datetime import datetime, timedelta
from django.conf import settings
from django.template.loader import get_template
from django.db.models import CharField
from django.db.models.functions import Concat

from external_services.calender.calendar_impl import CalendarImpl
from external_services.email.email_wrapper import MailHelper
from togther.models import ModelUtilities, Members, collabcardState, userMobiles, Collabcard, Community, User, \
    userEmails, EventCommsCeleryTasks, UserEmailsSendStatus, ChatroomCohort, CohortMember, CommunityGetStarted, \
    EventGoogleCalendarLogs, removedMembers, Card_Attachment
from collabmates_api.notifications.models import (WhatsappSubscription)
from utility.mail_category_constants import EmailCategories, EmailSubCategories
from utility.time_utilities import TimeUtilities
from utility.states import member_states, mobile_states, email_states, chatroom_not_opened_types, \
    user_email_send_status_types, event_access, card_types, get_started_types
from utility.url_utilities import UrlUtilities
from utility.celery_tasks import get_event_pricing
from collabmates_api.static_text import CUSTOMISE_JOIN_FORM_MAIL_SUBJECT
from collabmates_api.branch import create_single_event_branch_url

from .constants import *
from .tasks_manager import TaskManager

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()

url = settings.WEB_URL


class TasksImpl(TaskManager):
    event_type = None
    comm_type = None

    def __init__(self, event_type, comm_type):
        self.event_type = event_type
        self.comm_type = comm_type

    def get_event_type(self):
        return self.event_type

    def get_comm_type(self):
        return self.comm_type

    def get_response_dict_for_whatsapp_comms(self, payload):

        event_name = payload.get('chatroom').title
        community_name = payload.get('community').name
        event_time = TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(payload.get('chatroom').date_time)
        event_date = TimeUtilities.convert_epoch_time_to_date_month_year(payload.get('chatroom').date_time)

        cm_filter = ModelUtilities.get_model_filter(Members, {
            'community_id': payload.get('community').id,
            'state': member_states.ADMIN,
            'is_owner': True
        })

        if cm_filter:
            cm_name = cm_filter[0].member_id.userinfo.name

        else:
            cm_name = ""

        auto_register_link = create_single_event_branch_url(payload.get('chatroom'), should_register=True)
        auto_register_link = UrlUtilities.extract_part_from_url(auto_register_link, 'path', init_slash_off=True)

        link = UrlUtilities.extract_part_from_url(payload.get('chatroom').single_event_url, 'path', init_slash_off=True)

        custom_params = self.process_whatsapp_notification_custom_params(event_name, community_name, event_time,
                                                                         event_date, cm_name, link, auto_register_link)

        return custom_params

    def process_whatsapp_notification_custom_params(self, event_name, community_name, event_time, event_date,
                                                    cm_name, link, auto_register_link):

        if self.get_event_type() == EVENT_TYPE.LAST_CALL or self.get_event_type() == EVENT_TYPE.CREATION:

            custom_params = [
                {
                    "name": "event_name",
                    "value": event_name
                },
                {
                    "name": "community_name",
                    "value": community_name
                },
                {
                    "name": "event_time",
                    "value": event_time
                },
                {
                    "name": "event_date",
                    "value": event_date
                },
                {
                    "name": "community_manager_name",
                    "value": cm_name
                },
                {
                    "name": "link",
                    "value": auto_register_link
                },
            ]

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_5_HRS:

            custom_params = [
                {
                    "name": "event_name",
                    "value": event_name
                },
                {
                    "name": "community_name",
                    "value": community_name
                },
                {
                    "name": "event_time",
                    "value": event_time
                },
                {
                    "name": "link",
                    "value": link
                },
            ]

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_10_MIN:

            custom_params = [
                {
                    "name": "event_name",
                    "value": event_name
                },
                {
                    "name": "link",
                    "value": link
                },
            ]

        else:
            custom_params = []

        return custom_params

    def get_response_dict_for_app_notifications(self, payload):

        event_id = payload.get('chatroom').id
        event_name = payload.get('chatroom').title
        is_paid_event = payload.get('chatroom').is_paid
        online_link_enable_before = payload.get('chatroom').online_link_enable_before
        community_id = payload.get('chatroom').community.id
        attending_status = payload.get('attending_status', True)

        online_link_enable_before_in_mins = TimeUtilities.convert_milliseconds_to_min(online_link_enable_before)

        member_name = payload.get('user').userinfo.name if payload.get('user') else None

        response_dict = self.process_app_notification_response_dict(event_name, is_paid_event, event_id,
                                                                    online_link_enable_before_in_mins, member_name,
                                                                    community_id, attending_status=attending_status)

        return response_dict

    def process_app_notification_response_dict(self, event_name, is_paid_event, event_id,
                                               online_link_enable_before_in_mins, member_name, community_id,
                                               attending_status=True):

        if self.get_event_type() == EVENT_TYPE.CREATION:

            title = TITLE_EVENT_CREATION_APP_NOTIFICATION % event_name
            subtitle = SUB_TITLE_EVENT_CREATION_APP_NOTIFICATION

            category = NotificationCategories.EVENT_REGISTER_CATEGORY

            if is_paid_event:
                route = ROUTE_PAID_EVENT_CREATION_APP_NOTIFICATION % event_id
                subcategory = NotificationSubCategories.PAID_EVENT_CREATED_SUBCATEGORY

            else:
                route = ROUTE_FREE_EVENT_CREATION_APP_NOTIFICATION % event_id
                subcategory = NotificationSubCategories.FREE_EVENT_CREATED_SUBCATEGORY

        elif self.get_event_type() == EVENT_TYPE.LAST_CALL:

            title = TITLE_EVENT_LAST_CALL_APP_NOTIFICATION
            subtitle = SUB_TITLE_EVENT_LAST_CALL_APP_NOTIFICATION % event_name
            category = NotificationCategories.EVENT_REGISTER_CATEGORY

            if is_paid_event:
                route = ROUTE_PAID_EVENT_LAST_CALL_APP_NOTIFICATION % event_id
                subcategory = NotificationSubCategories.PAID_EVENT_REGISTRATION_LAST_CALL_SUBCATEGORY

            else:
                route = ROUTE_FREE_EVENT_LAST_CALL_APP_NOTIFICATION % event_id
                subcategory = NotificationSubCategories.FREE_EVENT_REGISTRATION_LAST_CALL_SUBCATEGORY

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_15_MIN:

            title = TITLE_EVENT_ATTENDANCE_APP_NOTIFICATION % online_link_enable_before_in_mins
            subtitle = SUB_TITLE_EVENT_ATTENDANCE_APP_NOTIFICATION % event_name
            route = ROUTE_EVENT_ATTENDANCE_APP_NOTIFICATION % event_id
            category = NotificationCategories.EVENT_ATTENDANCE
            subcategory = NotificationSubCategories.EVENT_REMINDER_15_MINUTES_SUBCATEGORY

        elif (self.get_event_type() == EVENT_TYPE.REGISTRATION) and attending_status:

            title = TITLE_EVENT_REGISTRATION_APP_NOTIFICATION
            subtitle = SUB_TITLE_EVENT_REGISTRATION_APP_NOTIFICATION % (member_name, event_name)
            category = NotificationCategories.EVENT_REGISTERED
            subcategory = NotificationSubCategories.EVENT_REGISTRATION_SUBCATEGORY

            if is_paid_event:
                route = ROUTE_PAID_EVENT_REGISTRATION_APP_NOTIFICATION % (event_id, community_id)

            else:
                route = ROUTE_FREE_EVENT_REGISTRATION_APP_NOTIFICATION % (event_id, community_id)

        else:
            title = ""
            subtitle = ""
            route = ""
            category = ""
            subcategory = ""

        response_dict = {
            'payload': {
                'title': title,
                'sub_title': subtitle,
                'route': route
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: category,
                NOTIFICATION_SUB_CATEGORY_KEY: subcategory
            }
        }

        if self.get_event_type() == EVENT_TYPE.REGISTRATION and is_paid_event:
            response_dict['payload']['sound'] = PAID_EVENT_REGISTRATION_SOUND

        return response_dict

    @staticmethod
    def get_event_metadata_for_calendar_invite(card_id, send_to_members, user_list, calendar_invite_type):
        card_instance = ModelUtilities.get_model_instance_or_none(Collabcard, card_id)

        if not card_instance:
            return

        if send_to_members:
            member_list = list(TasksHelper.get_active_members_of_community(card_instance.community))
        else:
            member_list = user_list

        user_email_filter = ModelUtilities.get_model_filter(userEmails,
                                                            {'user__in': member_list,
                                                             'email_state': email_states.PRIMARY,
                                                             'verified': True}).order_by('created_at')

        user_email_list = [{'email': instance.email} for instance in user_email_filter if instance.email]

        event_metadata = TasksImpl.process_calendar_invite_event_metadata(card_instance, user_email_list,
                                                                          calendar_invite_type)

        return event_metadata

    @staticmethod
    def process_calendar_invite_event_metadata(card_instance, user_email_list, calendar_invite_type):

        if not user_email_list:
            return {}

        event_metadata = {}

        if calendar_invite_type == CALENDAR_INVITE_TYPE.NEW_CALENDAR_CREATION:

            from collabmates_api.chatroom.chatroom_impl import ChatroomHelper

            chatroom_url = ChatroomHelper.fetch_chatroom_link(card_instance)

            event_metadata = {
                'summary': card_instance.title,
                'location': chatroom_url,
                'description': card_instance.about,
                'start': {
                    'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(card_instance.date_time),
                    'timeZone': settings.TIME_ZONE,
                },
                'end': {
                    'dateTime': TimeUtilities.convert_epoch_time_to_RFC3339(card_instance.end_date),
                    'timeZone': settings.TIME_ZONE,
                },
                'guestsCanSeeOtherGuests': False,
                'attendees': user_email_list,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': MAIL_EVENT_NOTIFICATION},
                    ],
                },
            }

        elif calendar_invite_type == CALENDAR_INVITE_TYPE.APPEND_ATTENDEES:

            attendees_list = TasksHelper.get_final_attendees_list_for_calendar_event(card_instance,
                                                                                     user_email_list)

            event_metadata = {
                'attendees': attendees_list
            }

        return event_metadata

    def get_response_dict_for_email_comms(self, payload, event_cost_in_event_creation_mail=None):

        event_name = payload.get('chatroom').title
        event_description = payload.get('chatroom').about
        event_time = TimeUtilities.convert_epoch_time_in_hh_mm_am_pm(payload.get('chatroom').date_time)
        event_date = TimeUtilities.convert_epoch_time_to_date_month_year(payload.get('chatroom').date_time)
        community_id = payload.get('chatroom').community.id
        link = payload.get('chatroom').single_event_url
        event_banner_url = TasksHelper.fetch_event_banner(event=payload.get('chatroom'))

        is_paid_event = payload.get('chatroom').is_paid

        event_cost = None

        if is_paid_event and self.get_event_type() == EVENT_TYPE.CREATION:
            event_cost = str(event_cost_in_event_creation_mail) + '/-'

        elif self.get_event_type() == EVENT_TYPE.CREATION or self.get_event_type() == EVENT_TYPE.LAST_CALL:
            branch_link = create_single_event_branch_url(payload.get('chatroom'), should_register=True)

            if branch_link:
                link = branch_link

        response_dict = self.process_email_comms_response_dict(event_name, event_description, event_time, event_date,
                                                               link, event_cost, community_id, event_banner_url)

        return response_dict

    def process_email_comms_response_dict(self, event_name, event_description, event_time, event_date, link, \
                                          event_cost, community_id, event_banner_url):

        if self.get_event_type() == EVENT_TYPE.CREATION or self.get_event_type() == EVENT_TYPE.LAST_CALL:

            response_dict = {
                'event_name': event_name,
                'event_description': event_description,
                'event_time': event_time,
                'event_date': event_date,
                'link': link
            }

            if event_cost:
                response_dict['event_cost'] = event_cost

        elif self.get_event_type() == EVENT_TYPE.REGISTRATION or self.get_event_type() == EVENT_TYPE.ATTENDANCE_9_AM:

            response_dict = {
                'event_name': event_name,
                'event_time': event_time,
                'event_date': event_date,
                'link': link
            }

        elif self.get_event_type() == EVENT_TYPE.POST_EVENT_ATTENDEES:

            link = POST_EVENT_ATTENDEES_LINK % (url, community_id)

            response_dict = {
                'event_name': event_name,
                'link': link,
                'event_time': event_time,
                'event_date': event_date
            }

        elif self.get_event_type() == EVENT_TYPE.POST_EVENT_ATTACHMENTS:

            response_dict = {
                'event_name': event_name,
                'link': link,
            }

        else:
            response_dict = {}

        if response_dict:
            response_dict['event_banner_url'] = event_banner_url

        return response_dict

    def calculate_time_for_sending_notification(self, event_instance):

        event_date_time_epoch = event_instance.date_time
        event_date_time_in_IST = TimeUtilities.convert_epoch_to_datetime_in_IST(event_date_time_epoch)

        if self.get_comm_type() == COMM_TYPE.WA:

            final_time = self.process_whatsapp_notification_final_time(event_date_time_in_IST)

        elif self.get_comm_type() == COMM_TYPE.APP_NOTI:

            online_link_enable_before = event_instance.online_link_enable_before
            online_link_enable_before_in_mins = TimeUtilities.convert_milliseconds_to_min(online_link_enable_before)

            final_time = self.process_app_notification_final_time(event_date_time_in_IST,
                                                                  online_link_enable_before_in_mins)

        elif self.get_comm_type() == COMM_TYPE.EMAIL:

            event_end_date_time_in_IST = TasksHelper.get_end_time_for_event(event_instance)

            final_time = self.process_email_comms_final_time(event_date_time_in_IST, event_end_date_time_in_IST)

        elif self.get_comm_type() == COMM_TYPE.CALENDAR:

            final_time = self.process_calendar_invite_final_time(event_date_time_in_IST)

        final_time = TimeUtilities.add_IST_offset_to_date_time(final_time)

        current_date_time_in_IST = TimeUtilities.get_current_datetime_in_IST()

        if "post" in self.get_event_type() and final_time >= current_date_time_in_IST:
            return final_time

        if final_time >= event_date_time_in_IST or final_time < current_date_time_in_IST:
            final_time = 0

        return final_time

    def process_whatsapp_notification_final_time(self, event_date_time_in_IST):

        if self.get_event_type() == EVENT_TYPE.CREATION:

            event_creation_time = TimeUtilities.get_current_datetime_in_IST()

            final_time = TasksHelper.calculate_notification_time(event_creation_time,
                                                                 EVENT_COMM_SHOULD_HAPPEN_AFTER)

        elif self.get_event_type() == EVENT_TYPE.LAST_CALL:

            event_last_call_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.LAST_CALL_WHATSAPP

            final_time = TasksHelper.calculate_notification_time(event_last_call_time, TIME_10_AM)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_5_HRS:

            event_attendance_5_hrs_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.ATTENDANCE_5_HRS_WHATSAPP

            final_time = TasksHelper.calculate_notification_time(event_attendance_5_hrs_time,
                                                                 EVENT_COMM_SHOULD_HAPPEN_AFTER)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_10_MIN:

            event_attendance_10_min_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.ATTENDANCE_10_MIN_WHATSAPP

            final_time = TasksHelper.calculate_notification_time(event_attendance_10_min_time,
                                                                 EVENT_COMM_SHOULD_HAPPEN_AFTER)

        return final_time

    def process_app_notification_final_time(self, event_date_time_in_IST, online_link_enable_before_in_mins):

        if self.get_event_type() == EVENT_TYPE.CREATION:

            event_creation_time = TimeUtilities.get_current_datetime_in_IST()
            final_time = TasksHelper.calculate_notification_time(event_creation_time,
                                                                 EVENT_COMM_SHOULD_HAPPEN_AFTER)

        elif self.get_event_type() == EVENT_TYPE.LAST_CALL:

            event_last_call_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.LAST_CALL_APP_NOTI
            final_time = TasksHelper.calculate_notification_time(event_last_call_time, TIME_10_AM)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_15_MIN:

            event_attendance_15_min_time = event_date_time_in_IST - timedelta(minutes=online_link_enable_before_in_mins)
            final_time = TasksHelper.calculate_notification_time(event_attendance_15_min_time,
                                                                 EVENT_COMM_SHOULD_HAPPEN_AFTER)

        elif self.get_event_type() == EVENT_TYPE.REGISTRATION:

            event_registration_time = TimeUtilities.get_current_datetime_in_IST()
            final_time = TasksHelper.calculate_notification_time(event_registration_time, TIME_10_AM)

        return final_time

    def process_calendar_invite_final_time(self, event_date_time_in_IST):

        if self.get_event_type() == EVENT_TYPE.REGISTRATION:
            current_date_time_in_IST = TimeUtilities.get_current_datetime_in_IST()
            final_time = current_date_time_in_IST

        return final_time

    def process_email_comms_final_time(self, event_date_time_in_IST, event_end_date_time_in_IST):

        if self.get_event_type() == EVENT_TYPE.CREATION or self.get_event_type() == EVENT_TYPE.REGISTRATION or \
                self.get_event_type() == EVENT_TYPE.POST_EVENT_ATTACHMENTS:

            event_creation_time = TimeUtilities.get_current_datetime_in_IST()

            final_time = event_creation_time

        elif self.get_event_type() == EVENT_TYPE.LAST_CALL:

            event_last_call_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.LAST_CALL_EMAIL

            final_time = TasksHelper.calculate_notification_time(event_last_call_time, TIME_10_AM)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_9_AM:

            final_time = TasksHelper.calculate_9_am_attendance_time_for_email_comms(event_date_time_in_IST)

        elif self.get_event_type() == EVENT_TYPE.POST_EVENT_ATTENDEES:

            post_event_attendees_time = event_end_date_time_in_IST + EVENT_COMM_FREQUENCY.POST_EVENT_ATTENDEES_MAIL

            final_time = post_event_attendees_time

        return final_time

    @staticmethod
    def get_response_dict_for_event_attachment_app_noti(event_instance, has_event_attachment):

        event_name = event_instance.title
        event_id = event_instance.id

        if has_event_attachment:
            title = TITLE_UPDATE_EVENT_ATTACHMENT_APP_NOTIICATION % event_name
            subcategory = NotificationSubCategories.EVENT_ATTACHMENT_UPDATED_SUBCATEGORY

        else:
            title = TITLE_NEW_EVENT_ATTACHMENT_APP_NOTIICATION % event_name
            subcategory = NotificationSubCategories.EVENT_ATTACHMENT_UPLOADED_SUBCATEGORY

        category = NotificationCategories.EVENT_ATTACHMENT_UPLOADED_CATEGORY
        subtitle = SUB_TITLE_EVENT_ATTACHMENT_APP_NOTIICATION
        route = ROUTE_EVENT_ATTACHMENT_APP_NOTIICATION % event_id

        response_dict = {
            'payload': {
                'title': title,
                'sub_title': subtitle,
                'route': route
            },
            'category': {
                NOTIFICATION_CATEGORY_KEY: category,
                NOTIFICATION_SUB_CATEGORY_KEY: subcategory,
            }
        }

        return response_dict

    @staticmethod
    def log_task_detail_in_db_on_new_task_creation_or_updation(task_id, event_instance, comm_type, event_type):
        filter_dict = {
            'event': event_instance,
            'comm_type': comm_type,
            'event_type': event_type,
            'is_deleted': False
        }

        is_task_already_created = ModelUtilities.is_model_filter_exists(EventCommsCeleryTasks, filter_dict)

        if is_task_already_created:
            task_instances = ModelUtilities.get_model_filter(EventCommsCeleryTasks, filter_dict)

            task_instances.update(is_deleted=True, updated_at=TimeUtilities.current_time_in_milliseconds())

            # from .tasks import delete_older_tasks_from_celery_queue
            # delete_older_tasks_from_celery_queue(task_ids)

        if task_id:
            filter_dict['task_id'] = task_id
            EventCommsCeleryTasks.create_instance(filter_dict)


class TasksHelper:

    @staticmethod
    def update_whatsapp_comms_payload_with_object_instances(payload):

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, payload.get('chatroom'))
        community_instance = ModelUtilities.get_model_instance_or_none(Community, payload.get('community'))
        user_instance = ModelUtilities.get_model_instance_or_none(User, payload.get('user'))

        payload_with_objects = {}

        payload_with_objects['chatroom'] = chatroom_instance
        payload_with_objects['community'] = community_instance
        payload_with_objects['user'] = user_instance

        return payload_with_objects

    @staticmethod
    def update_app_notification_payload_with_object_instances(payload):

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, payload.get('chatroom'))

        payload_with_objects = {}

        payload_with_objects['chatroom'] = chatroom_instance
        payload_with_objects['attending_status'] = payload.get('attending_status', True)

        if payload.get('user'):
            user_instance = ModelUtilities.get_model_instance_or_none(User, payload.get('user'))
            payload_with_objects['user'] = user_instance

        return payload_with_objects

    @staticmethod
    def get_active_members_of_community(community_id):

        members_list = ModelUtilities.get_model_filter(Members, {
            'community_id': community_id,
            'state': member_states.MEMBER
        }).values_list('member_id', flat=True)

        return list(members_list)

    @staticmethod
    def get_list_of_members_who_attended_event(chatroom_id):

        attending_members_list = ModelUtilities.get_model_filter(collabcardState, {
            'card': chatroom_id,
            'attended': True
        }).values_list('user', flat=True)

        return list(attending_members_list)

    @staticmethod
    def get_list_of_members_attending_or_not_attending_event(chatroom_id, user_ids, attending=False):

        attending_members_list = ModelUtilities.get_model_filter(collabcardState, {
            'card': chatroom_id,
            'attending_status': attending,
            'user__in': user_ids
        }).values_list('user', flat=True)

        return list(attending_members_list)

    @staticmethod
    def get_community_owner_and_event_creator(community_id, event_instance):

        owner = Members.get_community_owner_user_instance_or_none(community_id)

        event_creator = event_instance.user

        users_list = ModelUtilities.get_model_filter(User, {
            'id__in': [owner.id, event_creator.id]
        }).values_list('id', flat=True)

        return list(users_list)

    @staticmethod
    def get_community_managers_and_owners_of_community(community_id, event_instance, add_event_creator=True):

        community_managers = list(Members.objects.filter(
            community_id__id=community_id,
            state=member_states.ADMIN
        ).values_list("member_id__id", flat=True))

        event_creator_id = event_instance.user.id

        if (not add_event_creator) and (event_creator_id in community_managers):
            community_managers.remove(event_creator_id)

        return community_managers

    @staticmethod
    def calculate_notification_time(noti_time, alternate_noti_time):

        final_time = noti_time

        if noti_time.time() >= EVENT_COMM_SHOULD_HAPPEN_BEFORE.time():
            final_time = datetime.combine(noti_time.date() + timedelta(days=1), \
                                          alternate_noti_time.time())

        elif noti_time.time() < EVENT_COMM_SHOULD_HAPPEN_AFTER.time():
            final_time = datetime.combine(noti_time.date(), alternate_noti_time.time())

        return final_time

    @staticmethod
    def calculate_9_am_attendance_time_for_email_comms(event_date_time_in_IST):

        if event_date_time_in_IST.time() < TIME_9_AM.time():
            final_time = datetime.combine(event_date_time_in_IST.date() - timedelta(days=1), \
                                          TIME_9_AM.time())

        else:
            final_time = datetime.combine(event_date_time_in_IST.date(), TIME_9_AM.time())

        return final_time

    @staticmethod
    def create_user_data_for_wa_notification(user_ids, custom_params=[]):
        mobile_queryset = ModelUtilities.get_model_filter(userMobiles, {
            'user__in': user_ids,
            'state': mobile_states.PRIMARY
        })

        user_mobile_list = [str(mobile.country_code) + str(mobile.mobile_no) for mobile in mobile_queryset]

        final_user_data_list = []

        for mobile in user_mobile_list:
            user_data = {
                "whatsappNumber": mobile,
                "customParams": custom_params
            }

            final_user_data_list.append(user_data)

        return final_user_data_list

    @staticmethod
    def get_end_time_for_event(event_instance):
        event_end_time = event_instance.end_date

        event_end_time_in_IST = TimeUtilities.convert_epoch_to_datetime_in_IST(event_end_time)

        return event_end_time_in_IST

    @staticmethod
    def create_user_details_list_for_sending_app_notification(user_instances):

        notification_details_list = []

        from collabmates_api.notification import get_token_for_fcm

        for user_id in user_instances:
            notification_details = get_token_for_fcm(user_id, True)

            notification_details_list.append({
                'id': user_id,
                'fcm_token': notification_details[0],
                'mobile_os': notification_details[1]
            })

        return notification_details_list

    @staticmethod
    def create_context_for_sending_emails(user_instances, event_type, event_instance, data_dict):

        community_name = event_instance.community.name
        event_name = event_instance.title

        is_paid_event = False

        if event_instance.is_paid:
            is_paid_event = True

        community_owner_instance = Members.get_community_owner_user_instance_or_none(event_instance.community)
        community_owner_email = TasksHelper.get_emails_list_for_user_instances([community_owner_instance])

        to_mails_list = TasksHelper.get_emails_list_for_user_instances(user_instances)
        reply_to = community_owner_email[0] if community_owner_email else ''

        context = {
            'from_name': community_name,
            'from_email': SENDER_EMAIL_FOR_EMAIL_COMMS,
            'to_mails_list': to_mails_list,
            'reply_to': reply_to
        }

        if event_type == EVENT_TYPE.CREATION:
            context['subject'] = SUBJECT_EVENT_CREATION_MAIL % community_name

            if is_paid_event:
                context['template'] = get_template("mails/event_comms/paid-event-created.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_CREATED)

            else:
                context['template'] = get_template("mails/event_comms/free-event-created.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_CREATED)

        elif event_type == EVENT_TYPE.LAST_CALL:
            context['subject'] = SUBJECT_EVENT_LAST_CALL_MAIL

            if is_paid_event:
                event_cost_list = get_event_pricing(event_instance.id)
                event_cost = str(event_cost_list[0]) + '/-' if event_cost_list else "NA"

                data_dict['event_cost'] = event_cost

                context['template'] = get_template("mails/event_comms/paid-event-last-call.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_REGISTRATION_LAST_CALL)

            else:
                context['template'] = get_template("mails/event_comms/free-event-last-call.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_REGISTRATION_LAST_CALL)

        elif event_type == EVENT_TYPE.REGISTRATION:
            context['subject'] = SUBJECT_EVENT_REGISTRATION_MAIL

            if is_paid_event:
                context['template'] = get_template("mails/event_comms/paid-event-reg-success.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.PAID_EVENT_REGISTRATION_SUCCESSFUL)

            else:
                context['template'] = get_template("mails/event_comms/free-event-reg-success.html").render(data_dict)
                context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                    EmailCategories.EVENT_REGISTER, EmailSubCategories.FREE_EVENT_REGISTRATION_SUCCESSFUL)

        elif event_type == EVENT_TYPE.ATTENDANCE_9_AM:
            context['subject'] = SUBJECT_EVENT_ATTENDANCE_MAIL
            context['template'] = get_template("mails/event_comms/event-attendance.html").render(data_dict)
            context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.EVENT_ATTENDANCE, EmailSubCategories.DAY_OF_EVENT)

        elif event_type == EVENT_TYPE.POST_EVENT_ATTENDEES:
            attended_members_list = TasksHelper.get_list_of_members_who_attended_event(event_instance)
            attended_member_count = len(attended_members_list)

            data_dict['attended_member_count'] = attended_member_count

            context['subject'] = SUBJECT_POST_EVENT_ATTENDEES_MAIL % event_name
            context['reply_to'] = SENDER_EMAIL_FOR_EMAIL_COMMS
            context['template'] = get_template("mails/event_comms/post-event-attendees.html").render(data_dict)
            context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.POST_EVENT, EmailSubCategories.EVENT_ATTENDANCE)

        elif event_type == EVENT_TYPE.POST_EVENT_ATTACHMENTS:
            context['subject'] = SUBJECT_POST_EVENT_ATTACHMENT_MAIL
            context['template'] = get_template("mails/event_comms/post-event-attachments.html").render(data_dict)
            context['categories'] = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.POST_EVENT, EmailSubCategories.EVENT_ATTACHMENTS)

        return context

    @staticmethod
    def get_emails_list_for_user_instances(user_instances):
        user_email_filter = ModelUtilities.get_model_filter(userEmails,
                                                            {'user__in': user_instances,
                                                             'email_state': email_states.PRIMARY,
                                                             'verified': True}).order_by('created_at')

        email_list = [instance.email for instance in user_email_filter if instance.email]

        return email_list

    @staticmethod
    def should_send_notification(card_instance: object):
        if getattr(card_instance, 'is_deleted', False) and \
                Collabcard.is_chatroom_deleted(card_instance.is_deleted):
            message = f"aborting notification. chatroom is deleted (id = {card_instance.id})."
            error_logger.exception(message)
            return False

        return True

    @staticmethod
    def get_chatroom_instance(chatroom_id):
        chatroom_instance = ModelUtilities.get_model_instance_or_none(
            Collabcard,
            chatroom_id
        )

        return chatroom_instance

    @staticmethod
    def is_event_comms_task_deleted(task_id):
        filter_dict = {
            'task_id': task_id,
            'is_deleted': True
        }

        is_event_comms_task_deleted = ModelUtilities.is_model_filter_exists(EventCommsCeleryTasks, filter_dict)

        return is_event_comms_task_deleted

    @staticmethod
    def is_non_member_access_event(event_instance: Collabcard):
        """
        This function checks if event has non member access or not.
        @param event_instance: Collabcard instance having type 2 or 6
        @return: True if event access is 0 or NULL else False
        """

        if event_instance.access in [event_access.NON_COMMUNITY_USERS, None]:
            return True

        return False

    @staticmethod
    def filter_member_ids_for_non_member_access_event(event_instance: Collabcard, member_ids: list):
        """
        This function filters member_ids on the basis of added member groups in event.
        @param event_instance: Collabcard instance having type 2 or 6
        @param member_ids: List of member Ids
        @return: List of filtered member_ids
        """

        members_to_be_notified = member_ids.copy()

        active_members = TasksHelper.get_active_members_of_community(community_id=event_instance.community_id)

        if not event_instance or not member_ids or event_instance.type not in [card_types.CARD_EVENT,
                                                                               card_types.CARD_PUBLIC_EVENT]:
            return []

        if event_instance.access in [event_access.COMMUNITY_MEMBERS, event_access.NON_COMMUNITY_USERS_AND_MEMBERS]:
            return member_ids

        event_cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort, {'chatroom_id': event_instance.pk})
        event_cohort_ids = list(event_cohort_filter.values_list('cohort_id', flat=True))

        event_cohort_members = ModelUtilities.get_model_filter(CohortMember, {'cohort_id__in': event_cohort_ids})
        event_cohort_member_ids = (event_cohort_members.values_list('user_id', flat=True).distinct())

        for member_id in member_ids:

            if member_id in active_members and member_id not in event_cohort_member_ids:
                members_to_be_notified.remove(member_id)

        return members_to_be_notified

    @staticmethod
    def get_removed_member_ids_in_community(community_instance: Community) -> list:
        removed_member_ids = list(ModelUtilities.get_model_filter(removedMembers,
                                                                  {'community': community_instance}).
                                  values_list('member_id', flat=True))

        return removed_member_ids

    @staticmethod
    def get_members_excluding_non_members_in_community(community_id, members_list):
        removed_members = TasksHelper.get_removed_member_ids_in_community(community_id)

        return list(set(members_list) - set(removed_members))

    @staticmethod
    def get_active_members_excluding_non_members_in_community(community_instance: Community, active_members: list) -> \
            list:
        """
        This function filters member_ids excluded removed members.
        @param community_instance: Community instance
        @param active_members: IDs of members in a community
        @return: List of filtered member_ids
        """

        if not active_members:
            active_members = TasksHelper.get_active_members_of_community(community_id=community_instance.id)

        removed_members = TasksHelper.get_removed_member_ids_in_community(community_instance)

        return list(set(active_members) - set(removed_members))

    @staticmethod
    def get_collabcard_state_instance(member_id, chatroom_id):
        collabcard_state_instance = ModelUtilities.get_model_filter(collabcardState, {'card_id': chatroom_id,
                                                                                      'user_id': member_id})

        if not collabcard_state_instance:
            return None

        return collabcard_state_instance[0]

    @staticmethod
    def create_context_for_chatroom_not_opened(receiver_id, sender_id, chatroom_id, community_id,
                                               chatroom_not_opened_type):

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)
        sender_instance = ModelUtilities.get_model_instance_or_none(User, sender_id)
        receiver_instance = ModelUtilities.get_model_instance_or_none(User, receiver_id)

        community_owner_instance = Members.get_community_owner_user_instance_or_none(community_instance)
        community_owner_email = TasksHelper.get_emails_list_for_user_instances([community_owner_instance])

        if not community_instance or not chatroom_instance or not sender_instance or not receiver_instance or not \
                chatroom_not_opened_type:
            return None

        to_mails_list = TasksHelper.get_emails_list_for_user_instances([receiver_instance])
        reply_to = community_owner_email[0] if community_owner_email else ''

        from collabmates_api.chatroom.chatroom_impl import ChatroomHelper

        link = ChatroomHelper.fetch_chatroom_link(chatroom_instance)

        utm_campaign = ''

        if chatroom_not_opened_type == chatroom_not_opened_types.TAGGED_CHATROOM:
            utm_campaign = 'tagged_email'

        if chatroom_not_opened_type == chatroom_not_opened_types.DM_CHATROOM:
            utm_campaign = 'dm_email'

        link = link + "&utm_source=email&utm_campaign=" + utm_campaign

        data_dict = {
            'community_name': community_instance.name,
            'chatroom_name': chatroom_instance.header,
            'chatroom_link': link,
            'receiver_name': receiver_instance.userinfo.name,
            'sender_name': sender_instance.userinfo.name,
            'owner_name': community_owner_instance.userinfo.name
        }

        template = None
        categories = []

        if chatroom_not_opened_type == chatroom_not_opened_types.TAGGED_CHATROOM:
            template = get_template("mails/engagement_mails/tagged_chatroom_not_opened.html").render(data_dict)
            categories = MailHelper.get_email_category_list_using_category_subcategory(EmailCategories.ENGAGEMENT,
                                                                                       EmailSubCategories.CHATROOM_TAG)

        if chatroom_not_opened_type == chatroom_not_opened_types.DM_CHATROOM:
            template = get_template("mails/engagement_mails/dm_chatroom_not_opened.html").render(data_dict)
            categories = MailHelper.get_email_category_list_using_category_subcategory(EmailCategories.ENGAGEMENT,
                                                                                       EmailSubCategories.DM)

        context = {
            'from_email': SENDER_FOR_ENGAGEMENT_COMMUNICATION,
            'to_mails_list': to_mails_list,
            'reply_to': reply_to,
            'subject': SUBJECT_CHATROOM_NOT_OPENED_MAIL % sender_instance.userinfo.name,
            'template': template,
            'categories': categories
        }

        return context

    @staticmethod
    def update_user_email_send_status(member_id, chatroom_id, chatroom_not_opened_type):

        status_type = None

        if chatroom_not_opened_type == chatroom_not_opened_types.TAGGED_CHATROOM:
            status_type = user_email_send_status_types.TAGGED_CHATROOM_NOT_OPENED

        if chatroom_not_opened_type == chatroom_not_opened_types.DM_CHATROOM:
            status_type = user_email_send_status_types.DM_CHATROOM_NOT_OPENED

        user_email_send_status_instances = ModelUtilities.get_model_filter(
            UserEmailsSendStatus, {'user_id': member_id, 'chatroom_id': chatroom_id, 'is_completed': False,
                                   'status_type': status_type})

        if not user_email_send_status_instances:
            return

        user_email_send_status_instance = user_email_send_status_instances[0]

        user_email_send_status_instance.is_completed = True
        user_email_send_status_instance.save()

    @staticmethod
    def create_context_for_sending_first_email_on_directory_questions_setup(user_id, community_id):
        user_instance = ModelUtilities.get_model_instance_or_none(User, user_id)
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not (user_instance and community_instance):
            return

        community_get_started_filter = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                       {'community': community_instance,
                                                                        'get_started__type': get_started_types.CUSTOMISE_JOIN_FORM,
                                                                        'completed': True})

        if not len(community_get_started_filter):
            from collabmates_api.views import update_community_get_started
            from collabmates_api.branch import create_community_feed_url_for_cm_onboarding
            from collabmates_api.tasks import get_user_email_preferred_verified

            update_community_get_started(community_instance, get_started_types.CUSTOMISE_JOIN_FORM, is_enabled=True)

            # Send Join Form Mail
            branch_link = create_community_feed_url_for_cm_onboarding(community_instance)

            mail_template = get_template('mails/cm_onboarding/customise_join_form_cm_onboarding.html').render({
                "community_name": community_instance.name,
                "cm_name": user_instance.userinfo.name,
                "community_logo": community_instance.image_link,
                "community_brand_color": community_instance.brand_color if community_instance.brand_color else
                DEFAULT_CM_ONBOARDING_EMAIL_BUTTON_COLOR,
                "button_text": GETTING_STARTED_CM_BUTTON_TEXT,
                "button_link": branch_link
            })

            mail_subject = CUSTOMISE_JOIN_FORM_MAIL_SUBJECT.format(user_instance.userinfo.name)

            user_email = get_user_email_preferred_verified(user_instance.id)

            categories = MailHelper.get_email_category_list_using_category_subcategory(
                EmailCategories.CREATE_COMMUNITY, EmailSubCategories.JOIN_FORM_CREATED)

            if not user_email:
                return {}

            context = {
                "mail_subject": mail_subject,
                "mail_template": mail_template,
                "from_email": [user_email],
                "reply_to_email": [INVITE_MEMBER_REPLY_EMAIL],
                "mail_categories": categories
            }

            return context

    @staticmethod
    def get_final_attendees_list_for_calendar_event(card_instance, user_email_list):
        attendees_list = TasksHelper.get_attendees_list_for_calendar_event(event=card_instance)

        attendees_list.append(user_email_list[0])

        return attendees_list

    @staticmethod
    def get_attendees_list_for_calendar_event(event):
        filter_dict = {
            'event': event,
            'is_deleted': False
        }

        calendar_instance_filter = ModelUtilities.get_model_filter(EventGoogleCalendarLogs, filter_dict)

        if calendar_instance_filter:
            calender_id = calendar_instance_filter[0].calendar_id

            calendar_obj = CalendarImpl().get_calendar_api(calender_id)

            return calendar_obj.get('attendees')

        return []

    @staticmethod
    def log_calendar_event_object_in_db(event, calendar_obj):

        filter_dict = {
            'event': event,
            'calendar_id': calendar_obj.get('id'),
            'is_deleted': False
        }

        EventGoogleCalendarLogs.create_instance(filter_dict)

        return

    @staticmethod
    def get_calendar_id_for_calendar_event(event):

        calendar_id = None

        calendar_id_filter = ModelUtilities.get_model_filter(
            EventGoogleCalendarLogs,
            {
                'event': event
            }
        )

        if calendar_id_filter:
            calendar_id = calendar_id_filter[0].calendar_id

        return calendar_id

    @staticmethod
    def add_community_info_to_notification_payload(message: dict, community_id: int) -> dict:

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if community_instance:
            message['payload']['community_id'] = community_instance.id
            message['payload']['community_name'] = community_instance.name
            message['payload']['community_logo'] = community_instance.thumbnail

        return message

    @staticmethod
    def fetch_event_banner(event):
        filter_dict = {
            'collabcard_id': event,
            'type': 'image'
        }

        chatroom_attachment = ModelUtilities.get_model_filter(Card_Attachment, filter_dict)

        if chatroom_attachment:
            return chatroom_attachment[0].file_url

        return None

    @staticmethod
    def update_wa_subscription_user_data(user_data_list, template_name, broadcase_name):
        final_user_data_list = [
            {
                'user_data_list': [],
                'template_name': template_name,
                'broadcast_name': broadcase_name
            }
        ]

        mobile_instances = userMobiles.objects.annotate(
            number=Concat('country_code', 'mobile_no', output_field=CharField()))

        for user_data in user_data_list:
            user_mobile_instances = mobile_instances.filter(number=user_data['whatsappNumber'])

            if user_mobile_instances:
                user_instance = user_mobile_instances[0].user
                wa_subscription_instances = ModelUtilities.get_model_filter(WhatsappSubscription,
                                                                            {'user': user_instance})

                if not wa_subscription_instances:
                    wa_subscription_instance = WhatsappSubscription(user=user_instance)
                    wa_subscription_instance.save()

                else:
                    wa_subscription_instance = wa_subscription_instances[0]

                if wa_subscription_instance.subscribed:
                    template_data = None

                    # created or added user data if EVENT_CREATION template is there
                    if template_name == WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION:
                        # created or added user data for EVENT_CREATED_WA_UNSUBSCRIBE template
                        if (wa_subscription_instance.event_registration_whatsapp - 1)//3 == 0:
                            for final_user_data in final_user_data_list:
                                if (final_user_data["template_name"] ==
                                        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATED_WA_UNSUBSCRIBE):
                                    template_data = final_user_data

                            if template_data is not None:
                                template_data['user_data_list'].append(user_data)

                            else:
                                final_user_data_list.append({
                                    'user_data_list': [user_data],
                                    'template_name': WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATED_WA_UNSUBSCRIBE,
                                    'broadcast_name': WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATED_WA_UNSUBSCRIBE
                                })

                        # created or added user data for EVENT_CREATION template
                        else:
                            for final_user_data in final_user_data_list:
                                if final_user_data["template_name"] == WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION:
                                    template_data = final_user_data

                            if template_data is not None:
                                template_data['user_data_list'].append(user_data)

                            else:
                                final_user_data_list.append({
                                    'user_data_list': [user_data],
                                    'template_name': WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION,
                                    'broadcast_name': WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION
                                })

                        # incremented the message count for the user
                        wa_subscription_instance.event_registration_whatsapp += 1
                        wa_subscription_instance.save()

                    # created or added user data remaining templates
                    else:
                        for final_user_data in final_user_data_list:
                            if final_user_data["template_name"] == template_name:
                                final_user_data["user_data_list"].append(user_data)

        return final_user_data_list
