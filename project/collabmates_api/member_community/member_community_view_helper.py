from rest_framework import status as status_codes
from utility.response_utilities import ResponseUtilities
from utility.string_utilities import StringUtilities
from togther.models import (ModelUtilities, Community, Collabcard, Members)
from collabmates_api.sdk.models import (SdkClient)
from utility.states import (dm_icon_from_states, unsubscribe_types, member_states)


def timeit(func):
    from functools import wraps
    import time
    from external_services.logging.logging_wrapper import LoggingWrapper

    error_logger = LoggingWrapper.get_instance()

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        error_logger.error(f'COMMUNITY/FEED Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result

    return timeit_wrapper


class MemberCommunityViewHelper:

    @staticmethod
    def validate_join_community_request(member_id):
        if not member_id:
            return ResponseUtilities.get_impl_error_context("Empty member-id",
                                                            status_code=status_codes.HTTP_400_BAD_REQUEST)

        return {}

    @staticmethod
    def validate_join_community_sdk_request(user_id, community_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    @timeit
    def validate_fetch_feed_request(user_id, community_id, api_key: str = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id, api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key!")

        return {'user_instance': user_instance, 'community_instance': community_instance}

    @staticmethod
    def validate_fetch_member_profile_request(current_user_id, user_id, community_id, api_key, uuid = None):
        current_user_instance = ModelUtilities.get_user_instance_or_none(current_user_id)

        if not current_user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid x-member-id")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID or x-api-key")
        
        # If uuid is present, get valid member instance
        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_inner_error_context("Invalid uuid")
            
            user_id = valid_id[0]

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'current_user_instance': current_user_instance
        }

    @staticmethod
    def validate_request_dm_limit_request(user_id, community_id, api_key, member_id, uuid = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key")

        # If uuid is passed, get valid user id and update member_id
        if uuid:
            valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)

            if not valid_id:
                return ResponseUtilities.get_inner_error_context("Invalid uuid")
            
            member_id = valid_id[0]

        member_instance = ModelUtilities.get_user_instance_or_none(member_id)

        if not member_instance:
            return ResponseUtilities.get_inner_error_context("Invalid member ID")

        is_cm = Members.get_community_member_state(community_instance, user_instance) == member_states.ADMIN

        if not is_cm:
            is_one_user_cm = Members.get_community_member_state(community_instance, member_instance) == member_states.ADMIN

        else:
            is_one_user_cm = True

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'is_one_user_cm': is_one_user_cm
        }

    @staticmethod
    def validate_fetch_dm_chatrooms_request(user_id, community_id, api_key):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }

    @staticmethod
    def validate_member_can_dm_request(user_id, community_id, api_key, req_body):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id, api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key")

        if not req_body.get('req_from'):
            return ResponseUtilities.get_inner_error_context("Send req_from")

        if req_body.get('req_from') not in [dm_icon_from_states.MEMBER_PROFILE, dm_icon_from_states.COMMUNITY_DETAIL,
                                            dm_icon_from_states.DM_FEED, dm_icon_from_states.MEMBER_DIRECTORY,
                                            dm_icon_from_states.DM_FEED_V2, dm_icon_from_states.CHATROOM, dm_icon_from_states.GROUP_CHANNEL]: 
            return ResponseUtilities.get_inner_error_context("Invalid req_from")

        member_instance = None
        chatroom_instance = None

        member_id = req_body.get('member_id')
        uuid = req_body.get('uuid')

        if member_id or uuid:

            # If uuid is passed, get valid user id and update member_id
            if uuid:
                valid_id = ModelUtilities.get_valid_user_ids_from_uuids([uuid], community_instance.id)

                if not valid_id:
                    return ResponseUtilities.get_inner_error_context("Invalid uuid")
                
                member_id = valid_id[0]

            member_instance = ModelUtilities.get_user_instance_or_none(member_id)

            if not member_instance:
                return ResponseUtilities.get_inner_error_context("Invalid member ID")

        if req_body.get('chatroom_id'):
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, req_body.get('chatroom_id'))

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context("Invalid chatroom ID")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'member_instance': member_instance,
            'req_from': req_body.get('req_from'),
            'chatroom_instance': chatroom_instance
        }
        
    @staticmethod
    def validate_unsubscribe_email_notifications_request(user_id, community_id, code_flags: dict = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")
        
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        if (not code_flags) or (not isinstance(code_flags, dict)) or \
                (set(code_flags.keys()) - {unsubscribe_types.MAIL_EVENT_NOTIFICATIONS,
                                           unsubscribe_types.MAIL_CHATROOM_OR_DM}):
            return ResponseUtilities.get_inner_error_context("Invalid code flag object!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'code_flag': code_flags
        }

    @staticmethod
    def validate_fetch_unsubscribe_email_notifications_request(user_id, community_id, chatroom_id: str = None,
                                                               codes: str = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID")

        chatroom_instance = None
        notification_codes = []

        if chatroom_id:
            chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

            if not chatroom_instance:
                return ResponseUtilities.get_inner_error_context("Invalid chatroom ID")

        if codes:
            notification_codes = StringUtilities.get_list_from_string(codes, [])

            if not notification_codes:
                return ResponseUtilities.get_inner_error_context("Send valid codes")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'chatroom_instance':chatroom_instance,
            'notification_codes': notification_codes
        }
