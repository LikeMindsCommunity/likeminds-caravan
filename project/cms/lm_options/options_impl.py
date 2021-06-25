import json
from typing import Union

from django.http import JsonResponse
from rest_framework import status as status_codes

from .options_manager import OptionsManager
from ..models import LMOptions

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.exception_utilities import JsonDecodeException, CustomException
from ..utils import get_error_context

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class OptionsImpl(OptionsManager):

    def fetch_option(self, slug) -> dict:

        option_instance = LMOptions.get_object_or_raise_exception(slug)

        return {
            "success": True,
            "slug": slug,
            "value": option_instance.get_value()
        }

    def create_option(self, req_body) -> dict:

        slug = req_body.get("slug")
        value = req_body.get("value")

        if not slug or not value:
            response = {
                "success": False,
                "error_message": "Slug or Value missing in request body"
            }

            raise CustomException(response, status_code=status_codes.HTTP_400_BAD_REQUEST)

        LMOptions.update_or_create_option(slug=slug, value=value)

        return {"success": True}
