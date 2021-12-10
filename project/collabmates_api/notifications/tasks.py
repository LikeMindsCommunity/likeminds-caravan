from celery.app import shared_task

from django.conf import settings

from external_services.logging.logging_wrapper import LoggingWrapper

from project.celery import app
from utility.time_utilities import TimeUtilities
from .constants import COMM_TYPE, EVENT_TYPE, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL
from .tasks_impl import TasksImpl, TasksHelper
from external_services.wa_notification.wa_notification_impl import NotificationImpl
from collabmates_api.notification import notification_meta
from external_services.calender.calendar_impl import CalendarImpl


error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
url = settings.URL

@shared_task
def trigger_event_comms(payload_for_whatsapp_comms, payload_for_app_notifications):
    trigger_whatsapp_communication_for_event.delay(payload_for_whatsapp_comms)
    trigger_app_notification_for_event.delay(payload_for_app_notifications)


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
                        
            schedule_whatsapp_notification_for_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:    
            info_logger.info("No whatsapp notification sent for event_type = %s | payload received = %s" % (event_type, payload))
    
    except Exception as e:
        error_logger.exception("got error in send_whatsapp_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_whatsapp_comms, event_type))

@app.task
@shared_task
def schedule_whatsapp_notification_for_event_comms(payload_for_whatsapp_comms, custom_params, event_type):
    try:
        payload = TasksHelper.update_whatsapp_comms_payload_with_object_instances(payload_for_whatsapp_comms)

        event_instance = payload.get('chatroom')
        community_instance = payload.get('community')

        active_user_ids = TasksHelper.get_active_members_of_community(community_instance.id)

        if event_type == EVENT_TYPE.CREATION:
            final_user_ids = active_user_ids
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION

        elif event_type == EVENT_TYPE.LAST_CALL:
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id, 
                                                                                                            active_user_ids, 
                                                                                                            attending=False)

            final_user_ids = users_not_attending_event
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL

        elif event_type == EVENT_TYPE.ATTENDANCE_5_HRS:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids, 
                                                                                                    attending=True)

            final_user_ids = users_attending_event
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS

        elif event_type == EVENT_TYPE.ATTENDANCE_10_MIN:

            final_user_ids = active_user_ids
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN

        user_data_for_wa_notification = TasksHelper.create_user_data_for_wa_notification(user_ids=final_user_ids, 
                                                                                        custom_params=custom_params)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        if send_allowed:
            NotificationImpl.send_wa_bulk_notitfications(user_data_for_wa_notification, template_name=template_name, 
                                                        broadcast_name=template_name)
    
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

        if task_begin_time != 0:
            args = [payload_for_app_notification, app_noti_dict, event_type]

            info_logger.info("Scheduling app notification for event_type = %s | payload generated = %s | \
                            payload received = %s" % (event_type, app_noti_dict, payload))
                        
            schedule_app_notification_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:    
            info_logger.info("No app notification sent for event_type = %s | payload received = %s" % (event_type, payload))
    
    except Exception as e:
        error_logger.exception("got error in send_app_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_app_notification, event_type))

@app.task
@shared_task
def schedule_app_notification_event_comms(payload_for_app_notification, app_noti_dict, event_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_app_notification)

        event_instance = payload.get('chatroom')
        community_id = event_instance.community

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)

        if event_type == EVENT_TYPE.CREATION:
            final_user_instances = active_user_ids

        elif event_type == EVENT_TYPE.LAST_CALL:
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id, 
                                                                                                            active_user_ids, 
                                                                                                            attending=False)

            final_user_instances = users_not_attending_event

        elif event_type == EVENT_TYPE.ATTENDANCE_15_MIN:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids, 
                                                                                                    attending=True)

            final_user_instances = users_attending_event

        elif event_type == EVENT_TYPE.REGISTRATION:
            final_user_instances = TasksHelper.get_community_owner_and_event_creator(community_id, event_instance)

        user_details_list = TasksHelper.create_user_details_list_for_sending_app_notification(final_user_instances)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        if send_allowed:
            notification_meta(user_details_list, app_noti_dict)

    except Exception as e:
        error_logger.exception("got error in schedule_app_notification | error - %s | payload received = %s | \
                                event_type = %s" % (str(e), payload_for_app_notification, event_type))


@shared_task
def send_calender_invite_for_event_type(payload_for_calendar_invite, event_type, send_to_members=True, user_list=None):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_calendar_invite)

        event_instance = payload.get('chatroom')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.CALENDAR)
        event_metadata = tasks_instance.get_event_metadata_for_calendar_invite(payload_for_calendar_invite.get('chatroom'), 
                                                                            send_to_members, user_list)
        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)
        
        task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        if task_begin_time != 0:
            args = [payload_for_calendar_invite, event_metadata, event_type]

            info_logger.info("Scheduling calendar invite for event_type = %s | event_metadata = %s | \
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
def schedule_calendar_invite_for_event_comms(payload_for_calendar_invite, event_metadata, event_type):
    try:
        if event_metadata:
            CalendarImpl().call_calender_api(event_metadata)

    except Exception as e:
        error_logger.exception("got error in schedule_calendar_invite | error - %s | payload received = %s | \
                                event_type = %s" % (str(e), payload_for_calendar_invite, event_type))


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
            notification_meta(user_details_list, app_noti_dict)
    
    except Exception as e:
        error_logger.exception("got error in schedule_app_notification_on_event_attachment | error - %s | event_id \
                            received = %s" % (str(e), event_id))
