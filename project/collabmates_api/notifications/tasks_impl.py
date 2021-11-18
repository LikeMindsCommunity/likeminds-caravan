from datetime import datetime, timedelta

from togther.models import ModelUtilities, Members, collabcardState, userMobiles, Collabcard, Community, User
from utility.time_utilities import TimeUtilities
from utility.utils import generate_private_link_for_chatroom
from utility.states import member_states, mobile_states

from .constants import COMM_TYPE, EVENT_TYPE, EVENT_COMM_FREQUENCY, EVENT_COMM_SHOULD_HAPPEN_AFTER, \
                        EVENT_COMM_SHOULD_HAPPEN_BEFORE, EVENT_LAST_CALL_TIME
from .tasks_manager import TaskManager


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
            'community_id' : payload.get('community').id,
            'state': member_states.ADMIN,
            'is_owner': True
        })

        if cm_filter:
            cm_name = cm_filter[0].member_id.userinfo.name
        
        else:
            cm_name = ""

        share_url = generate_private_link_for_chatroom(
            payload.get('chatroom'),
            payload.get('user')
        )

        link = share_url.get('private_link')

        custom_params = self.process_whatsapp_notification_custom_params(event_name, community_name, event_time, event_date, \
                                                                        cm_name, link)

        return custom_params

    def process_whatsapp_notification_custom_params(self, event_name, community_name, event_time, event_date, \
                                                    cm_name, link):
        
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
                    "value": link
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
            custom_params = {}
        
        return custom_params

    def calculate_time_for_sending_notification(self, event_instance):

        event_date_time_epoch = event_instance.date_time

        event_date_time_in_IST = TimeUtilities.convert_epoch_to_datetime_in_IST(event_date_time_epoch)

        if self.get_comm_type() == COMM_TYPE.WA:

            final_time = self.process_whatsapp_notification_final_time(event_date_time_in_IST)
        
        final_time = TimeUtilities.add_IST_offset_to_date_time(final_time)

        current_date_time_in_IST = TimeUtilities.get_current_datetime_in_IST()

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

            final_time = TasksHelper.calculate_notification_time(event_last_call_time, EVENT_LAST_CALL_TIME)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_5_HRS:

            event_attendance_5_hrs_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.ATTENDANCE_5_HRS_WHATSAPP

            final_time = TasksHelper.calculate_notification_time(event_attendance_5_hrs_time, 
                                                                        EVENT_COMM_SHOULD_HAPPEN_AFTER)

        elif self.get_event_type() == EVENT_TYPE.ATTENDANCE_10_MIN:

            event_attendance_10_min_time = event_date_time_in_IST - EVENT_COMM_FREQUENCY.ATTENDANCE_10_MIN_WHATSAPP

            final_time = TasksHelper.calculate_notification_time(event_attendance_10_min_time, 
                                                                        EVENT_COMM_SHOULD_HAPPEN_AFTER)
        
        return final_time

        
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
    def get_active_members_of_community(community_id):

        members_list = ModelUtilities.get_model_filter(Members, {
            'community_id': community_id,
            'state': member_states.MEMBER
        }).values_list('member_id', flat=True)

        return members_list

    @staticmethod
    def get_list_of_members_attending_or_not_attending_event(chatroom_id, user_ids, attending=False):
        
        attending_members_list = ModelUtilities.get_model_filter(collabcardState, {
            'card': chatroom_id,
            'attending_status': attending,
            'user__in': user_ids
        }).values_list('user', flat=True)

        return attending_members_list

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
    def create_user_data_for_wa_notification(user_ids, custom_params={}):
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
