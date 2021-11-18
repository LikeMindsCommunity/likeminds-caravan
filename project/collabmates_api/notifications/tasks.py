from celery.app import shared_task

from django.conf import settings

from external_services.logging.logging_wrapper import LoggingWrapper

from project.celery import app
from .constants import COMM_TYPE, EVENT_TYPE, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_5_HRS, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_CREATION, \
        WHATSAPP_TEMPLATE_NAME_FOR_EVENT_LAST_CALL
from .tasks_impl import TasksImpl, TasksHelper
from external_services.wa_notification.wa_notification_impl import NotificationImpl

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()
url = settings.URL

@shared_task
def trigger_event_comms(payload_for_whatsapp_comms):
    trigger_whatsapp_communication_for_event.delay(payload_for_whatsapp_comms)


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
        error_logger.exception("got error in send_whatsapp_notification_for_event_type | error - %s | payload reveived = %s |\
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
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids, 
                                                                                                    attending=True)

            final_user_ids = users_attending_event
            template_name = WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN

        user_data_for_wa_notification = TasksHelper.create_user_data_for_wa_notification(user_ids=final_user_ids, 
                                                                                        custom_params=custom_params)

        NotificationImpl.send_wa_bulk_notitfications(user_data_for_wa_notification, template_name=template_name, 
                                                    broadcast_name=template_name)
    
    except Exception as e:
        error_logger.exception("got error in schedule_whatsapp_notification | error - %s | payload reveived = %s | \
                                event_type = %s" % (str(e), payload_for_whatsapp_comms, event_type))
