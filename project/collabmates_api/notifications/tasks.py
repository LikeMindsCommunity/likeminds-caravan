from celery.app import shared_task

from django.conf import settings

from external_services.email.email_wrapper import MailWrapper
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities
from utility.utils import (filter_user_instances_based_on_notification_flag)

from project.celery import app
from .constants import COMM_TYPE, EVENT_COMM_FREQUENCY, EVENT_TYPE, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL, SENDER_NAME_FOR_EMAIL_COMMS, CALENDAR_INVITE_TYPE
from .tasks_impl import TasksImpl, TasksHelper
from external_services.wa_notification.wa_notification_impl import NotificationImpl
from collabmates_api.notification import notification_meta
from external_services.calender.calendar_impl import CalendarImpl
from collabmates_api.sdk.models import CommunityEmailConfiguration

from ..chatroom.constants import EMAIL_UNSUBSCRIBE_URL

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
url = settings.URL


@shared_task
def trigger_event_comms(payload_for_whatsapp_comms, payload_for_app_and_email_notifications):
    trigger_whatsapp_communication_for_event.delay(payload_for_whatsapp_comms)
    trigger_app_notification_for_event.delay(payload_for_app_and_email_notifications)

    info_logger.info(f"api/event/create: trigger_event_comms: "
                     f"payload for email comms = {payload_for_app_and_email_notifications}")
    
    args = [payload_for_app_and_email_notifications]
    trigger_email_communication_for_event.apply_async(
        args,
        countdown=10
    )


@shared_task
def trigger_whatsapp_communication_for_event(payload_for_whatsapp_comms):
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.CREATION)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.LAST_CALL)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_5_HRS)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_10_MIN)

@shared_task
def send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, event_type):
    try:
        payload = TasksHelper.update_whatsapp_comms_payload_with_object_instances(payload_for_whatsapp_comms)

        event_instance = payload.get('chatroom')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.WA)
        custom_params = tasks_instance.get_response_dict_for_whatsapp_comms(payload)
        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)

        task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        if task_begin_time != 0:
            args = [payload_for_whatsapp_comms, custom_params, event_type]

            info_logger.info("Scheduling whatsapp notification for event_type = %s | custom_params = %s | \
                            payload received = %s" % (event_type, custom_params, payload))

            task_id = schedule_whatsapp_notification_for_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            task_id = ""
            info_logger.info("No whatsapp notification sent for event_type = %s | payload received = %s" % (event_type, payload))

        TasksImpl.log_task_detail_in_db_on_new_task_creation_or_updation(task_id=str(task_id),
                                                                        event_instance=event_instance,
                                                                        comm_type=COMM_TYPE.WA,
                                                                        event_type=event_type)

    except Exception as e:
        error_logger.exception("got error in send_whatsapp_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_whatsapp_comms, event_type))

@app.task
@shared_task(bind=True)
def schedule_whatsapp_notification_for_event_comms(self, payload_for_whatsapp_comms, custom_params, event_type):
    try:
        payload = TasksHelper.update_whatsapp_comms_payload_with_object_instances(payload_for_whatsapp_comms)

        event_instance = payload.get('chatroom')
        community_instance = payload.get('community')

        active_user_ids = TasksHelper.get_active_members_of_community(community_instance.id)
        user_ids = []

        template_name = None

        if event_type == EVENT_TYPE.CREATION:
            active_user_ids = TasksHelper.get_active_members_excluding_non_members_in_community(community_instance.id,
                                                                                                active_user_ids)
            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_instance.id,
                                                                                            event_instance,
                                                                                            add_event_creator=False)

            user_ids = active_user_ids + community_managers
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION

        elif event_type == EVENT_TYPE.LAST_CALL:
            active_user_ids = TasksHelper.get_active_members_excluding_non_members_in_community(community_instance.id,
                                                                                                active_user_ids)
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                            active_user_ids,
                                                                                                            attending=False)

            user_ids = users_not_attending_event
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL

        elif event_type == EVENT_TYPE.ATTENDANCE_5_HRS:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                     active_user_ids,
                                                                                                     attending=True)

            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_instance.id,
                                                                                            event_instance)

            user_ids = users_attending_event + community_managers
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS

        elif event_type == EVENT_TYPE.ATTENDANCE_10_MIN:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                     active_user_ids,
                                                                                                     attending=True)

            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_instance.id,
                                                                                            event_instance)

            user_ids = users_attending_event + community_managers
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_ids = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                       list(user_ids))
        else:
            final_user_ids = user_ids

        user_data_for_wa_notification = TasksHelper.create_user_data_for_wa_notification(user_ids=final_user_ids,
                                                                                        custom_params=custom_params)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

        if send_allowed and (not is_task_deleted) and template_name:
            updated_user_data = TasksHelper.update_wa_subscription_user_data(user_data_for_wa_notification,
                                                                             template_name)

            for user_data in updated_user_data:
                NotificationImpl.send_wa_bulk_notifications(user_data["user_data_list"],
                                                            template_name=user_data["template_name"],
                                                            broadcast_name=user_data["broadcast_name"])

        else:
            info_logger.info("No whatsapp notification scheuduled for event_type = %s | chatroom_deleted = %s | \
                is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted,
                                                                 payload_for_whatsapp_comms))

    except Exception as e:
        error_logger.exception("got error in schedule_whatsapp_notification | error - %s | payload received = %s | \
                                event_type = %s" % (str(e), payload_for_whatsapp_comms, event_type))


@shared_task
def trigger_app_notification_for_event(payload_for_app_notifications):
    send_app_notification_for_event_type(payload_for_app_notifications, EVENT_TYPE.CREATION)
    send_app_notification_for_event_type(payload_for_app_notifications, EVENT_TYPE.LAST_CALL)
    send_app_notification_for_event_type(payload_for_app_notifications, EVENT_TYPE.ATTENDANCE_15_MIN)

@shared_task
def send_app_notification_for_event_type(payload_for_app_notification, event_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_app_notification)

        event_instance = payload.get('chatroom')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.APP_NOTI)
        app_noti_dict = tasks_instance.get_response_dict_for_app_notifications(payload)
        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)

        task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        info_logger.info(f"api/event/create: send_app_notification_for_event : "
                         f"Event_type = {event_type} | "
                         f"Payload = {payload_for_app_notification}"
                         f"app_noti_dict = {app_noti_dict} | "
                         f"task_begin_time = {task_begin_time} | "
                         f"task_expiry_time = {task_expiry_time} | ")
        
        if task_begin_time != 0:
            args = [payload_for_app_notification, app_noti_dict, event_type]

            info_logger.info("api/event/create: Scheduling app notification for event_type = %s | payload generated = %s | payload received = %s" % (event_type, app_noti_dict, payload))

            task_id = schedule_app_notification_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            task_id = ""
            info_logger.info("api/event/create: No app notification sent for event_type = %s | payload received = %s" % (event_type, payload))

        TasksImpl.log_task_detail_in_db_on_new_task_creation_or_updation(task_id=str(task_id),
                                                                        event_instance=event_instance,
                                                                        comm_type=COMM_TYPE.APP_NOTI,
                                                                        event_type=event_type)

    except Exception as e:
        error_logger.exception("got error in send_app_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_app_notification, event_type))

@app.task
@shared_task(bind=True)
def schedule_app_notification_event_comms(self, payload_for_app_notification, app_noti_dict, event_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_app_notification)

        event_instance = payload.get('chatroom')
        community_id = event_instance.community.id

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)
        user_instances = []

        if event_type == EVENT_TYPE.CREATION:
            active_user_ids = TasksHelper.get_active_members_excluding_non_members_in_community(community_id,
                                                                                                active_user_ids)
            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance,
                                                                                            add_event_creator=False)

            user_instances = active_user_ids + community_managers

        elif event_type == EVENT_TYPE.LAST_CALL:
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                            active_user_ids,
                                                                                                            attending=False)
            user_instances = TasksHelper.get_members_excluding_non_members_in_community(community_id,
                                                                                        users_not_attending_event)

        elif event_type == EVENT_TYPE.ATTENDANCE_15_MIN:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids,
                                                                                                    attending=True)

            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance)

            user_instances = users_attending_event + community_managers

        elif event_type == EVENT_TYPE.REGISTRATION:
            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance)

            user_instances = community_managers

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_instances = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                             list(user_instances))
        else:
            final_user_instances = user_instances

        if event_type == EVENT_TYPE.REGISTRATION and payload_for_app_notification.get('user') in final_user_instances:
            final_user_instances.remove(payload_for_app_notification.get('user'))

        user_details_list = TasksHelper.create_user_details_list_for_sending_app_notification(final_user_instances)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

        info_logger.info(f"api/event/create: Scheduliing app notifications: "
                         f"Event_type = {event_type} | "
                         f"Final user instances = {final_user_instances} | "
                         f"User Details list = {user_details_list} |"
                         f"send_allowed = {send_allowed} | "
                         f"is_task_deleted = {is_task_deleted} | "
                         f"app_noti_dict = {app_noti_dict} ")
        
        if send_allowed and not is_task_deleted:
            app_noti_dict = TasksHelper.add_community_info_to_notification_payload(app_noti_dict, community_id)
            notification_meta(user_details_list, app_noti_dict)

        else:
            info_logger.info("No app notification scheuduled for event_type = %s | chatroom_deleted = %s | \
                is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted, \
                payload_for_app_notification))

    except Exception as e:
        error_logger.exception("got error in schedule_app_notification | error - %s | payload received = %s | \
                                event_type = %s" % (str(e), payload_for_app_notification, event_type))


@shared_task
def send_calender_invite_for_event_type(payload_for_calendar_invite, event_type, send_to_members=True, user_list=None,
                                        calendar_invite_type=CALENDAR_INVITE_TYPE.NEW_CALENDAR_CREATION):
    try:

        info_logger.info(f"calendar/invite 2: send_calender_invite_for_event_type: calendar_invite_type = {calendar_invite_type} | user_list = {user_list} | payload_for_calendar_invite = {payload_for_calendar_invite}")
        
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_calendar_invite)

        event_instance = payload.get('chatroom')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.CALENDAR)

        if payload_for_calendar_invite.get('calendar_meta_data'):
            event_metadata = payload_for_calendar_invite.get('calendar_meta_data')

        else:
            event_metadata = tasks_instance.get_event_metadata_for_calendar_invite(payload_for_calendar_invite.get('chatroom'),
                                                                                send_to_members, user_list,
                                                                                calendar_invite_type)

        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)

        task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        info_logger.info(f"calendar/invite 3: send_calender_invite_for_event_type: with task_begin_time = {task_begin_time} | task_expiry_time = {task_expiry_time} | event_metadata = {event_metadata}")

        if task_begin_time != 0:
            args = [payload_for_calendar_invite, event_metadata, event_type, calendar_invite_type]

            info_logger.info("calendar/invite 4: Scheduling calendar invite for event_type = %s | event_metadata = %s | \
                            payload received = %s" % (event_type, event_metadata, payload))

            schedule_calendar_invite_for_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            info_logger.info("No calendar invite sent for event_type = %s | payload received = %s" % (event_type, \
                            payload))

    except Exception as e:
        error_logger.exception("got error in send_calender_invite_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_calendar_invite, event_type))

@app.task
@shared_task
def schedule_calendar_invite_for_event_comms(payload_for_calendar_invite, event_metadata, event_type,
                                            calendar_invite_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_calendar_invite)

        info_logger.info(f"calendar/invite 4: schedule_calendar_invite_for_event_comms: {event_metadata} | calendar_invite_type = {calendar_invite_type}")

        if event_metadata:
            if calendar_invite_type == CALENDAR_INVITE_TYPE.NEW_CALENDAR_CREATION:

                info_logger.info(f"calendar/invite 4: schedule_calendar_invite_for_event_comms: {payload_for_calendar_invite} | calendar_invite_type = {calendar_invite_type}")

                calendar_obj = CalendarImpl().call_calender_api(event_metadata)

                TasksHelper.log_calendar_event_object_in_db(payload.get('chatroom'), calendar_obj)

            elif calendar_invite_type in (CALENDAR_INVITE_TYPE.APPEND_ATTENDEES, CALENDAR_INVITE_TYPE.UPDATE_CALENDAR):

                calendar_id = TasksHelper.get_calendar_id_for_calendar_event(payload.get('chatroom'))

                if calendar_id:
                    calendar_obj = CalendarImpl().patch_calendar_api(calendar_id, event_metadata)

    except Exception as e:
        error_logger.exception("got error in schedule_calendar_invite | error - %s | payload received = %s | \
                                event_type = %s" % (str(e), payload_for_calendar_invite, event_type))


@shared_task
def trigger_email_communication_for_event(payload_for_email_comms):
    payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

    if not payload.get('chatroom').is_paid:
        send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.CREATION)

    send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.LAST_CALL)
    send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.ATTENDANCE_9_AM)


@shared_task
def send_email_notification_for_event_type(payload_for_email_comms, event_type):
    try:

        info_logger.info(f"api/event/create: send_email_notification_for_event_type: "
                         f"Event_type = {event_type} | "
                         f"payload for email comms = {payload_for_email_comms}")
        
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

        event_instance = payload.get('chatroom')
        event_cost_in_event_creation_mail = payload_for_email_comms.get('event_cost')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.EMAIL)
        response_dict = tasks_instance.get_response_dict_for_email_comms(payload, event_cost_in_event_creation_mail)

        info_logger.info(f"api/event/create: get_response_dict_for_email_comms: response_dict = {response_dict}")

        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)

        info_logger.info(f"api/event/create: calculate_time_for_sending_notification: task_begin_time = {task_begin_time}")

        if 'post' in event_type:
            task_expiry_time = TasksHelper.get_end_time_for_event(event_instance) + \
                            EVENT_COMM_FREQUENCY.POST_EVENT_ATTENDEES_MAIL_EXPIRY_AFTER

        else:
            task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        info_logger.info(f"api/event/create: get_end_time_for_event: task_expiry_time = {task_expiry_time}")

        if task_begin_time != 0:
            args = [payload_for_email_comms, response_dict, event_type]

            info_logger.info(f"api/event/create: Scheduling email notification for event_type = {event_type} | "
                             f"Eta = {str(task_begin_time)} | "
                             f"response_dict = {response_dict} | "
                             f"payload received = {payload} | "
                             f" chatroom Event name = {event_instance.title} ")

            task_id = schedule_email_notifications_for_event.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            task_id = ""
            info_logger.info("api/event/create: No email notification sent for event_type = %s | payload received = %s" % (event_type, payload))

        TasksImpl.log_task_detail_in_db_on_new_task_creation_or_updation(task_id=str(task_id),
                                                                        event_instance=event_instance,
                                                                        comm_type=COMM_TYPE.EMAIL,
                                                                        event_type=event_type)

    except Exception as e:
        error_logger.exception("api/event/create: got error in send_email_notification_for_event_type | error - %s | payload received = %s | event_type = %s" % (str(e), payload_for_email_comms, event_type))

@app.task
@shared_task(bind=True)
def schedule_email_notifications_for_event(self, payload_for_email_comms, response_dict, event_type):
    try:

        info_logger.info(f"api/event/create: schedule_email_notifications_for_event: "
                         f"payload_for_email_comms = {payload_for_email_comms} | "
                         f"response_dict = {response_dict} | "
                         f"event_type = {event_type} ")
        
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

        event_instance = payload.get('chatroom')
        community_id = event_instance.community.id

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)
        user_instances = []

        if event_type == EVENT_TYPE.CREATION:
            active_user_ids = TasksHelper.get_active_members_excluding_non_members_in_community(community_id,
                                                                                                active_user_ids)
            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance,
                                                                                            add_event_creator=False)
            user_instances = active_user_ids + community_managers

            info_logger.info(f"api/event/create: Event Creation users calculation | "
                                f"active_user_ids = {active_user_ids} | "
                                f"community_managers = {community_managers} | "
                                f"user_instances = {user_instances} ")
            
            user_instances = filter_user_instances_based_on_notification_flag(user_instances, community_id)

            info_logger.info(f"api/event/create: Event Creation users calculation | "
                             f"user_instances after notifiication flag = {user_instances} ")

        elif event_type == EVENT_TYPE.POST_EVENT_ATTACHMENTS:
            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance,
                                                                                            add_event_creator=True)

            user_instances = active_user_ids + community_managers

            info_logger.info(f"api/event/create: Post Event attachments users calculation | "
                             f"community_managers = {community_managers} | "
                             f"user_instances = {user_instances} ")

        elif event_type == EVENT_TYPE.LAST_CALL:
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                            active_user_ids,
                                                                                                            attending=False)

            user_instances = TasksHelper.get_members_excluding_non_members_in_community(community_id,
                                                                                        users_not_attending_event)
            
            info_logger.info(f"api/event/create: Event Last Call users calculation | "
                             f"users_not_attending_event = {users_not_attending_event} | "
                             f"user_instances = {user_instances} ")
            
            user_instances = filter_user_instances_based_on_notification_flag(user_instances, community_id)

            info_logger.info(f"api/event/create: Event Last Call users calculation | "
                             f"user_instances after notification flag = {user_instances} ")

        elif event_type == EVENT_TYPE.REGISTRATION:

            user_instances = [payload.get('user')]

            info_logger.info(f"api/event/create: Event Registration user calculation | "
                             f"user_instances = {user_instances} ")

        elif event_type == EVENT_TYPE.ATTENDANCE_9_AM:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids,
                                                                                                    attending=True)

            community_managers = TasksHelper.get_community_managers_and_owners_of_community(community_id,
                                                                                            event_instance)

            user_instances = users_attending_event + community_managers

            info_logger.info(f"api/event/create: Event Attendance 9AM users calculation | "
                             f"users_attending_event = {users_attending_event} | "
                             f"community_managers = {community_managers} | "
                             f"user_instances = {user_instances} ")

        elif event_type == EVENT_TYPE.POST_EVENT_ATTENDEES:
            user_instances = TasksHelper.get_community_owner_and_event_creator(community_id, event_instance)

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_instances = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                             list(user_instances))
        else:
            final_user_instances = user_instances

        if event_type == EVENT_TYPE.POST_EVENT_ATTACHMENTS and \
                payload_for_email_comms.get('user') in final_user_instances:
            final_user_instances.remove(payload_for_email_comms.get('user'))

        response_dict['community_name'] = event_instance.community.name

        final_users_count = len(final_user_instances)
        info_logger.info(f"api/event/create: schedule_email_notifications_for_event: | "
                         f"is_non_member_access_event = {is_non_member_access_event} | "
                         f"response_dict = {response_dict} | "
                         f"final_user_instances = {final_user_instances} Count = {final_users_count} | "
                         f"")
        
        count = 1

        email_sender_data = CommunityEmailConfiguration.get_email_sender_data_for_community(community_id)
        
        for user_id in final_user_instances:

            response_dict['unsub'] = EMAIL_UNSUBSCRIBE_URL % (settings.WEB_URL, str(community_id), str(user_id))

            context = TasksHelper.create_context_for_sending_emails([user_id], event_type, event_instance,
                                                                    data_dict=response_dict)

            sender_name = email_sender_data.get('name') if email_sender_data.get('name') \
                else context['from_name']

            sender_email = email_sender_data.get('from_email') if email_sender_data.get('from_email') \
                else context['from_email']

            reply_to_email = email_sender_data.get('reply_email') if email_sender_data.get('reply_email') \
                else context['reply_to']

            send_allowed = TasksHelper.should_send_notification(event_instance)

            is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

            if send_allowed and not is_task_deleted:

                info_logger.info(f"api/event/create: {event_type} | User {count} ({context['to_mails_list']}) out of {final_users_count} | "
                                 f"Sending email with subject = {context['subject']} ")
                
                MailWrapper.send_email_with_custom_from_email(subject=context['subject'], template=context['template'],
                                                              from_email=sender_email,
                                                              to_mails_list=context['to_mails_list'],
                                                              reply_to=reply_to_email,
                                                              from_name=sender_name,
                                                              categories=context['categories'])

            else:
                info_logger.info("api/event/create: No email notification scheduled for event_type = %s | chatroom_deleted = %s | is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted,payload_for_email_comms))

            count += 1

    except Exception as e:
        info_logger.info("api/event/create: got error in send_email_notification_for_event_type | error - %s | payload received = %s | event_type = %s" % (str(e), payload_for_email_comms, event_type))
        error_logger.exception("got error in send_email_notification_for_event_type | error - %s | payload received = %s | event_type = %s" % (str(e), payload_for_email_comms, event_type))


@shared_task
def send_app_notification_on_event_attachment(event_id, has_event_attachment=False):
    try:
        event_instance = TasksHelper.get_chatroom_instance(event_id)

        response_dict = TasksImpl.get_response_dict_for_event_attachment_app_noti(event_instance, has_event_attachment)

        schedule_time = TimeUtilities.get_current_datetime_in_IST()
        task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        args = [event_id, response_dict]

        info_logger.info("Scheduling app notification for event attachment | event_id = %s | response_dict = %s" \
                        % (event_id, response_dict))

        schedule_app_notification_on_event_attachment.apply_async(
            args,
            kwargs={},
            eta=schedule_time,
            expires=task_expiry_time
        )

    except Exception as e:
        error_logger.exception("got error in send_app_notification_on_event_attachment | error - %s | event_id \
                            received = %s" % (str(e), event_id))

@app.task
@shared_task
def schedule_app_notification_on_event_attachment(event_id, app_noti_dict):
    try:
        event_instance = TasksHelper.get_chatroom_instance(event_id)

        community_id = event_instance.community

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)

        user_details_list = TasksHelper.create_user_details_list_for_sending_app_notification(active_user_ids)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        if send_allowed:
            app_noti_dict = TasksHelper.add_community_info_to_notification_payload(app_noti_dict, community_id)
            notification_meta(user_details_list, app_noti_dict)

    except Exception as e:
        error_logger.exception("got error in schedule_app_notification_on_event_attachment | error - %s | event_id \
                            received = %s" % (str(e), event_id))


@shared_task
def reschedule_event_comms_notifications_on_event_update(payload_for_whatsapp_comms, payload_for_app_and_email_notifications):
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.LAST_CALL)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_5_HRS)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_10_MIN)

    send_app_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.LAST_CALL)
    send_app_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.ATTENDANCE_15_MIN)

    send_email_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.LAST_CALL)
    send_email_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.ATTENDANCE_9_AM)

##### keeping the following code in case we find a solution for deleting the tasks from rabbitmq #####

# @shared_task
# def delete_older_tasks_from_celery_queue(task_ids):
#     try:
#         info_logger.info('deleting older celery tasks from queue | task_ids received = %s' % task_ids)

#         for task_id in task_ids:
#             AsyncResult(task_id).revoke(terminate=True)
#             # app.control.revoke(task, terminate=True)

#         info_logger.info('successfully deleted older celery tasks from queue | task_ids received = %s' % task_ids)

#     except Exception as e:
#         error_logger.error('got error while deleting older celery tasks | exception ocurred = %s | task_ids received \
#             = %s' % (str(e), task_ids))


@shared_task
def send_communication_when_chatroom_not_opened(receiver_id, sender_id, chatroom_id, chatroom_not_opened_type,
                                                last_conversation_id):
    try:

        if not chatroom_not_opened_type:
            return

        collabcard_state_instance = TasksHelper.get_collabcard_state_instance(receiver_id, chatroom_id)

        if not collabcard_state_instance:
            error_logger.error("got error in send_communication_when_chatroom_not_opened | error -member %s does \
            not have collabcard state in chatroom_id %s" % (receiver_id, chatroom_id))
            return

        if collabcard_state_instance.last_seen_conversation and \
                collabcard_state_instance.last_seen_conversation.id != last_conversation_id:
            return

        context = TasksHelper.create_context_for_chatroom_not_opened(receiver_id, sender_id, chatroom_id,
                                                                     collabcard_state_instance.community.id,
                                                                     chatroom_not_opened_type)

        email_sender_data = CommunityEmailConfiguration.get_email_sender_data_for_community(
            collabcard_state_instance.community_id)

        sender_name = email_sender_data.get('name') if email_sender_data.get('name') \
            else SENDER_NAME_FOR_EMAIL_COMMS

        sender_email = email_sender_data.get('from_email') if email_sender_data.get('from_email') \
            else context['from_email']

        reply_to_email = email_sender_data.get('reply_email') if email_sender_data.get('reply_email') \
            else context['reply_to']

        if context:
            MailWrapper.send_email_with_custom_from_email(subject=context['subject'], template=context['template'],
                                                          from_email=sender_email,
                                                          to_mails_list=context['to_mails_list'],
                                                          categories=context['categories'],
                                                          reply_to=reply_to_email,
                                                          from_name=sender_name)

            TasksHelper.update_user_email_send_status(receiver_id, chatroom_id, chatroom_not_opened_type)

    except Exception as e:
        error_logger.error("got error in send_communication_when_chatroom_not_opened | error - %s | member_id \
                            received = %s | chatroom_id received = %s | chatroom_not_opened_type \
                            received = %s" % (str(e), receiver_id, chatroom_id, chatroom_not_opened_type))


@shared_task
def send_mail_for_first_time_edit_community_questions(user_id, community_id):
    context = TasksHelper.create_context_for_sending_first_email_on_directory_questions_setup(user_id, community_id)

    if context:
        send_email_response = MailWrapper.send_email.delay(context.get('mail_subject'),
                                                           context.get('mail_template'),
                                                           context.get('from_email'),
                                                           categories=context.get('mail_categories'),
                                                           reply_to=context.get('reply_to_email'))
