from togther.models import (ModelUtilities, Collabcard, Cohort, Members, User)
from utility.response_utilities import ResponseUtilities


class ValidationUtilities:

    user_id_keys = ['user_id']

    params_models_dict = {
        'user_id': User,
        'chatroom_id': Collabcard,
        'cohort_id': Cohort
    }

    def __init__(self, validation_params: dict):
        self.validation_params = validation_params

    def is_valid(self):
        response_dict = {}

        if not (self.validation_params and isinstance(self.validation_params, dict)):
            return ResponseUtilities.get_inner_error_context('Invalid params object')

        for key, value in self.validation_params.items():

            if key in self.user_id_keys:
                param_instance = ModelUtilities.get_user_instance_or_none(value)

            else:

                if not self.params_models_dict.get(key):
                    continue

                param_instance = ModelUtilities.get_model_instance_or_none(self.params_models_dict.get(key), value)

            if not param_instance:
                return ResponseUtilities.get_inner_error_context('Invalid {}!'.format(key))

            response_dict[key] = param_instance

        return response_dict
