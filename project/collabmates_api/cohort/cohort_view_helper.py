from utility.states import (cohort_type_list, cohort_types, member_states)
from utility.response_utilities import ResponseUtilities
from togther.models import (ModelUtilities, Members, Cohort, Collabcard, ChatroomCohort)
from collabmates_api.sdk.models import (SdkClient)


class CohortViewHelper:

    @staticmethod
    def validate_create_cohort_request(user_id, community_id: str = None, api_key: str = None,
                                       name: str = None, member_ids: list = None, cohort_type: int = 0,
                                       type_id: str = None, filter_list: list = None):

        if cohort_type not in cohort_type_list:
            return ResponseUtilities.get_inner_error_context("Invalid cohort type!")

        if (cohort_type == cohort_types.SUBSCRIPTION_PLAN) and (not type_id):
            return ResponseUtilities.get_inner_error_context("Invalid type ID!")

        if not name:
            return ResponseUtilities.get_inner_error_context("Invalid cohort name!")

        if not isinstance(member_ids, list):
            return ResponseUtilities.get_inner_error_context("Invalid member ID list!")

        if not isinstance(filter_list, list):
            return ResponseUtilities.get_inner_error_context("Invalid filter list!")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id,
                                                                      api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key!")

        community_id = community_instance.id

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_id,
                                                                  'member_id': user_instance})

        if cohort_type in [cohort_types.SUBSCRIPTION_EXPIRED_PLAN, cohort_types.ALL_MEMBER]:

            filter_dict = {
                'type': cohort_type,
                'community_id': community_id
            }

            cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

            if cohort_filter:
                return ResponseUtilities.get_inner_error_context("This type of cohort already exists in community!")

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("User does not have the ability to create cohort!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance
        }

    @staticmethod
    def validate_fetch_cohort_request(user_id, cohort_id, community_id, api_key: str = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return ResponseUtilities.get_inner_error_context("Invalid cohort ID!")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id,
                                                                      api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key!")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_id})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("User does not have the ability to fetch cohort!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
            'cohort_instance': cohort_instance
        }

    @staticmethod
    def validate_delete_cohort_request(user_id, cohort_id):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return ResponseUtilities.get_inner_error_context("Invalid cohort ID!")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': cohort_instance.community_id,
                                                                  'member_id': user_id})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("User does not have the ability to create cohort!")

        return {
            'user_instance': user_instance,
            'cohort_instance': cohort_instance
        }

    @staticmethod
    def validate_edit_cohort_request(user_id, cohort_id, community_id: str = None, api_key: str = None,
                                     member_ids: list = None, cohort_type: int = 0, type_id: str = None,
                                     filter_list: list = None):

        if cohort_type not in cohort_type_list:
            return ResponseUtilities.get_inner_error_context("Invalid cohort type!")

        if (cohort_type == cohort_types.SUBSCRIPTION_PLAN) and (not type_id):
            return ResponseUtilities.get_inner_error_context("Invalid type ID!")

        if not isinstance(member_ids, list):
            return ResponseUtilities.get_inner_error_context("Invalid member ID list!")

        if not isinstance(filter_list, list):
            return ResponseUtilities.get_inner_error_context("Invalid filter list!")

        if not isinstance(filter_list, list):
            return ResponseUtilities.get_inner_error_context("Invalid rights list!")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id,
                                                                      api_key=api_key)

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:

            if cohort_type == cohort_types.NORMAL:
                return ResponseUtilities.get_inner_error_context("Invalid cohort ID!")

            if (cohort_type == cohort_types.SUBSCRIPTION_PLAN) and not type_id:
                return ResponseUtilities.get_inner_error_context("Invalid type ID!")

            if cohort_type == cohort_types.SUBSCRIPTION_EXPIRED_PLAN:
                type_id = None

            if all([cohort_type in [cohort_types.SUBSCRIPTION_EXPIRED_PLAN, cohort_types.ALL_MEMBER],
                    not community_instance]):
                return ResponseUtilities.get_inner_error_context("Invalid community ID/API key!")

            cohort_filter = ModelUtilities.get_model_filter(Cohort,
                                                            {'type_id': type_id,
                                                             'type': cohort_type,
                                                             'community': community_instance})

            if not cohort_filter:
                return ResponseUtilities.get_inner_error_context("Invalid cohort ID!")

            cohort_instance = cohort_filter[0]

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        member_instance = None

        if cohort_instance and not community_instance:
            community_instance = cohort_instance.community

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})

        if member_filter:
            member_instance = member_filter[0]

        return {
            'user_instance': user_instance,
            'cohort_instance': cohort_instance,
            'member_instance': member_instance,
        }

    @staticmethod
    def validate_fetch_community_cohorts_request(user_id, community_id: str = None, api_key: str = None):
        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        community_instance = SdkClient.get_community_instance_or_none(community_id=community_id,
                                                                      api_key=api_key)

        if not community_instance:
            return ResponseUtilities.get_inner_error_context("Invalid community ID/API key!")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_id})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("User does not have the ability to fetch cohort access!")

        return {
            'user_instance': user_instance,
            'community_instance': community_instance,
        }

    @staticmethod
    def validate_update_cohort_access_request(user_id, chatroom_id, cohort_id, cohort_access):

        if cohort_access is None:
            return ResponseUtilities.get_inner_error_context("Invalid cohort access!")

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return ResponseUtilities.get_inner_error_context("Invalid cohort ID!")

        user_instance = ModelUtilities.get_user_instance_or_none(user_id)

        if not user_instance:
            return ResponseUtilities.get_inner_error_context("Invalid user ID!")

        chatroom_instance = ModelUtilities.get_model_instance_or_none(Collabcard, chatroom_id)

        if not chatroom_instance:
            return ResponseUtilities.get_inner_error_context("Invalid chatroom ID!")

        if chatroom_instance.is_secret:
            return ResponseUtilities.get_inner_error_context("Chatroom should be open!")

        chatroom_cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort, {'chatroom_id': chatroom_id,
                                                                                  'cohort_id': cohort_id})

        if not chatroom_cohort_filter:
            return ResponseUtilities.get_inner_error_context("Cohort is not added to this chatroom!")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': chatroom_instance.community,
                                                                  'member_id': user_id})

        if not member_filter:
            return ResponseUtilities.get_inner_error_context("User is not a member of community!")

        member_instance = member_filter[0]

        if not (member_instance.state == member_states.ADMIN):
            return ResponseUtilities.get_inner_error_context("User does not have the ability to update cohort access!")

        return {
            'user_instance': user_instance,
            'chatroom_instance': chatroom_instance,
            'chatroom_cohort_filter': chatroom_cohort_filter,
        }


