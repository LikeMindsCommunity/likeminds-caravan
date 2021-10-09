from rest_framework import status as status_codes

from .join_email_manager import JoinEmailManager

from togther.models import CommunityJoinDefaultEmail, ModelUtilities
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class JoinEmailImpl(JoinEmailManager):

    def add_join_email(self, req_body) -> dict:

        body = req_body.get("body")

        if not body:
            response = {
                "success": False,
                "error_message": "body missing in request body"
            }

            return {'response': response, 'status_code': status_codes.HTTP_400_BAD_REQUEST}

        default_email_instances = ModelUtilities.get_model_filter(CommunityJoinDefaultEmail, {})

        if len(default_email_instances) == 0:
            email_data = {"body": body}
            CommunityJoinDefaultEmail.create_instance(email_data)

        else:
            default_email_instance = default_email_instances[0]
            default_email_instance.body = body
            default_email_instance.save()

        response = {"success": True}

        return {'response': response, 'status_code': status_codes.HTTP_200_OK}
