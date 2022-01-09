from celery.app import shared_task
from celery.result import AsyncResult

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.time_utilities import TimeUtilities

from project.celery import app
from .constants import COMM_TYPE, EVENT_COMM_FREQUENCY, EVENT_TYPE, WHATSAPP_TEMPLATE_NAME_FOR_EVENT_ATTENDANCE_10_MIN, \
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
def trigger_event_comms(payload_for_whatsapp_comms, payload_for_app_and_email_notifications):
    trigger_whatsapp_communication_for_event.delay(payload_for_whatsapp_comms)
    trigger_app_notification_for_event.delay(payload_for_app_and_email_notifications)
    trigger_email_communication_for_event.delay(payload_for_app_and_email_notifications)


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
        final_user_ids = []

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

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_ids = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                       list(final_user_ids))

        user_data_for_wa_notification = TasksHelper.create_user_data_for_wa_notification(user_ids=final_user_ids,
                                                                                        custom_params=custom_params)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

        if send_allowed and not is_task_deleted:
            NotificationImpl.send_wa_bulk_notitfications(user_data_for_wa_notification, template_name=template_name,
                                                        broadcast_name=template_name)

        else:
            info_logger.info("No whatsapp notification scheuduled for event_type = %s | chatroom_deleted = %s | \
                is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted, \
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

        if task_begin_time != 0:
            args = [payload_for_app_notification, app_noti_dict, event_type]

            info_logger.info("Scheduling app notification for event_type = %s | payload generated = %s | \
                            payload received = %s" % (event_type, app_noti_dict, payload))

            task_id = schedule_app_notification_event_comms.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            task_id = ""
            info_logger.info("No app notification sent for event_type = %s | payload received = %s" % (event_type, payload))

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
        community_id = event_instance.community

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)
        final_user_instances = []

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

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_instances = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                             list(final_user_instances))

        user_details_list = TasksHelper.create_user_details_list_for_sending_app_notification(final_user_instances)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

        if send_allowed and not is_task_deleted:
            notification_meta(user_details_list, app_noti_dict)

        else:
            info_logger.info("No app notification scheuduled for event_type = %s | chatroom_deleted = %s | \
                is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted, \
                payload_for_app_notification))

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
def trigger_email_communication_for_event(payload_for_email_comms):
    payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

    if not payload.get('chatroom').is_paid:
        send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.CREATION)

    send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.LAST_CALL)
    send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.ATTENDANCE_9_AM)
    send_email_notification_for_event_type(payload_for_email_comms, EVENT_TYPE.POST_EVENT_ATTENDEES)

@shared_task
def send_email_notification_for_event_type(payload_for_email_comms, event_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

        event_instance = payload.get('chatroom')
        event_cost_in_event_creation_mail = payload_for_email_comms.get('event_cost')

        tasks_instance = TasksImpl(event_type=event_type, comm_type=COMM_TYPE.EMAIL)
        response_dict = tasks_instance.get_response_dict_for_email_comms(payload, event_cost_in_event_creation_mail)

        task_begin_time = tasks_instance.calculate_time_for_sending_notification(event_instance=event_instance)

        if 'post' in event_type:
            task_expiry_time = TasksHelper.get_end_time_for_event(event_instance) + \
                            EVENT_COMM_FREQUENCY.POST_EVENT_ATTENDEES_MAIL_EXPIRY_AFTER

        else:
            task_expiry_time = TasksHelper.get_end_time_for_event(event_instance)

        if task_begin_time != 0:
            args = [payload_for_email_comms, response_dict, event_type]

            info_logger.info("Scheduling email notification for event_type = %s | response_dict = %s | \
                            payload received = %s" % (event_type, response_dict, payload))

            task_id = schedule_email_notifications_for_event.apply_async(
                args,
                kwargs={},
                eta=task_begin_time,
                expires=task_expiry_time
            )

        else:
            task_id = ""
            info_logger.info("No email notification sent for event_type = %s | payload received = %s" % (event_type, payload))

        TasksImpl.log_task_detail_in_db_on_new_task_creation_or_updation(task_id=str(task_id),
                                                                        event_instance=event_instance,
                                                                        comm_type=COMM_TYPE.EMAIL,
                                                                        event_type=event_type)

    except Exception as e:
        error_logger.exception("got error in send_email_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_email_comms, event_type))

@app.task
@shared_task(bind=True)
def schedule_email_notifications_for_event(self, payload_for_email_comms, response_dict, event_type):
    try:
        payload = TasksHelper.update_app_notification_payload_with_object_instances(payload_for_email_comms)

        event_instance = payload.get('chatroom')
        community_id = event_instance.community

        active_user_ids = TasksHelper.get_active_members_of_community(community_id)

        if event_type == EVENT_TYPE.CREATION or event_type == EVENT_TYPE.POST_EVENT_ATTACHMENTS:
            final_user_instances = active_user_ids

        elif event_type == EVENT_TYPE.LAST_CALL:
            users_not_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                            active_user_ids,
                                                                                                            attending=False)

            final_user_instances = users_not_attending_event

        elif event_type == EVENT_TYPE.REGISTRATION:

            final_user_instances = [payload.get('user')]

        elif event_type == EVENT_TYPE.ATTENDANCE_9_AM:
            users_attending_event = TasksHelper.get_list_of_members_attending_or_not_attending_event(event_instance.id,
                                                                                                    active_user_ids,
                                                                                                    attending=True)

            final_user_instances = users_attending_event

        elif event_type == EVENT_TYPE.POST_EVENT_ATTENDEES:
            final_user_instances = TasksHelper.get_community_owner_and_event_creator(community_id, event_instance)

        is_non_member_access_event = TasksHelper.is_non_member_access_event(event_instance=event_instance)

        if is_non_member_access_event:
            final_user_instances = TasksHelper.filter_member_ids_for_non_member_access_event(event_instance,
                                                                                             list(final_user_instances))

        context = TasksHelper.create_context_for_sending_emails(final_user_instances, event_type, event_instance,\
                                                                data_dict=response_dict)

        send_allowed = TasksHelper.should_send_notification(event_instance)

        is_task_deleted = TasksHelper.is_event_comms_task_deleted(self.request.id)

        if send_allowed and not is_task_deleted:
            send_email_with_custom_from_email(context['subject'], context['template'], context['from_email'],\
                                            context['to_mails_list'], context['bcc_mails_list'], \
                                            categories=context.get('categories'), reply_to=context['reply_to'])

        else:
            info_logger.info("No email notification scheuduled for event_type = %s | chatroom_deleted = %s | \
                is_task_deleted = %s | payload received = %s" % (event_type, not send_allowed, is_task_deleted, \
                payload_for_email_comms))

    except Exception as e:
        error_logger.exception("got error in send_email_notification_for_event_type | error - %s | payload received = %s |\
                            event_type = %s" % (str(e), payload_for_email_comms, event_type))


@shared_task
def send_email_with_custom_from_email(subject, template, from_email, to_mails_list, bcc_mails_list, \
                                    categories=None, reply_to=None):

    fail_silently = False
    msg = EmailMultiAlternatives(subject=subject,
                                 body=template,
                                 from_email=from_email,
                                 to=to_mails_list,
                                 bcc=bcc_mails_list,
                                 reply_to=reply_to,
                                )
    msg.attach_alternative(template, "text/html")

    if categories is not None:
        msg.categories = categories

    msg.send(fail_silently)
    return


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


@shared_task
def reschedule_event_comms_notifications_on_event_update(payload_for_whatsapp_comms, payload_for_app_and_email_notifications):
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.LAST_CALL)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_5_HRS)
    send_whatsapp_notification_for_event_type(payload_for_whatsapp_comms, EVENT_TYPE.ATTENDANCE_10_MIN)

    send_app_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.LAST_CALL)
    send_app_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.ATTENDANCE_15_MIN)

    send_email_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.LAST_CALL)
    send_email_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.ATTENDANCE_9_AM)
    send_email_notification_for_event_type(payload_for_app_and_email_notifications, EVENT_TYPE.POST_EVENT_ATTENDEES)

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
