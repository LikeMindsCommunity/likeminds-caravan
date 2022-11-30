from togther.models import (ModelUtilities, Collabcard, Cohort, User)
from collabmates_api.sdk.models import (SdkClient)
from utility.response_utilities import ResponseUtilities


class ValidationUtilities:

    user_id_keys = ['user_id']
    community_id_keys = ['community_id', 'api_key']

    params_models_dict = {
        'user_id': User,
        'chatroom_id': Collabcard,
        'cohort_id': Cohort,
        'community_id': SdkClient,
        'api_key': SdkClient
    }

    @staticmethod
    def is_valid(validation_params: dict = None):
        response_dict = {}

        if not (validation_params and isinstance(validation_params, dict)):
            return ResponseUtilities.get_inner_error_context('Invalid params object')

        for key, value in validation_params.items():

            if not ValidationUtilities.params_models_dict.get(key):
                continue

            if key in ValidationUtilities.user_id_keys:
                param_instance = ModelUtilities.get_user_instance_or_none(value)

            elif key in ValidationUtilities.community_id_keys:

                if not (value and isinstance(value, dict)):
                    return ResponseUtilities.get_inner_error_context('Invalid community ID/API key!')

                param_instance = SdkClient.get_community_instance_or_none(**value)

            else:
                param_instance = ModelUtilities.get_model_instance_or_none(
                    ValidationUtilities.params_models_dict.get(key), value)

            if not param_instance:
                return ResponseUtilities.get_inner_error_context('Invalid {}!'.format(key))

            response_dict[key] = param_instance

        return response_dict
