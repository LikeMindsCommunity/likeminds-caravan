from django.contrib.auth.models import User

from cms.in_app_review.in_app_review_manager import InAppReviewManager
from cms.utils import get_error_context
from cms.models import InAppReview
from togther.models import ModelUtilities
from utility.time_utilities import TimeUtilities


class InAppReviewImpl(InAppReviewManager):

    def shown_review_popup(self, member_id) -> dict:
        user_instance = ModelUtilities.get_model_instance_or_none(User, member_id)

        if not user_instance:
            return {'success': False, 'error_message': 'Invalid User Id'}

        in_app_review_filter = ModelUtilities.get_model_filter(InAppReview, {'user': user_instance})

        if in_app_review_filter:
            in_app_review_instance = in_app_review_filter[0]
            in_app_review_instance.shown = True
            in_app_review_instance.updated_at = TimeUtilities.current_time_in_milliseconds()
            in_app_review_instance.save()

        else:
            return {'success': False, 'error_message': 'In App Review instance does not exist'}

        return {'success': True}

    def enable_review_popup(self, user_ids) -> dict:

        if not user_ids:
            return {'success': False, 'error_message': 'List of User ids can not be empty.'}

        user_dict = InAppReviewHelper.pre_compute_user_with_user_ids(user_ids)

        in_app_review_existance_dict = InAppReviewHelper.check_existance_of_in_app_review_with_user_ids(user_ids)

        bulk_create_list = []

        for user_id in user_ids:
            user_instance = user_dict.get(user_id)

            if not user_instance:
                return {'success': False, 'error_message': 'Invalid user_ids'}

            if in_app_review_existance_dict.get(user_id) is False:
                in_app_review_instance = InAppReview.create_instance_for_bulk_create({
                    'user_instance': user_instance,
                    'shown': False
                })
                in_app_review_existance_dict[user_id] = True
                bulk_create_list.append(in_app_review_instance)

        ModelUtilities.bulk_create_instances(InAppReview, bulk_create_list)

        return {'success': True}


class InAppReviewHelper:

    @staticmethod
    def pre_compute_user_with_user_ids(user_ids):
        user_filter = ModelUtilities.get_model_filter(User, {'id__in': user_ids})
        user_dict = {user_id: None for user_id in user_ids}

        for user in user_filter:
            user_id = user.id

            if user_dict.get(user_id) is None:
                user_dict[user_id] = user

        return user_dict

    @staticmethod
    def check_existance_of_in_app_review_with_user_ids(user_ids):
        in_app_review_filter_user_list = list(
            ModelUtilities.get_model_filter(InAppReview, {'user_id__in': user_ids}).values_list('user',
                                                                                                flat=True))

        in_app_review_dict = {user_id: False for user_id in user_ids}

        for in_app_review_user_id in in_app_review_filter_user_list:

            if in_app_review_dict.get(in_app_review_user_id) is False:
                in_app_review_dict[in_app_review_user_id] = True

        return in_app_review_dict
