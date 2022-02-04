from rest_framework.exceptions import APIException
from rest_framework import status as status_codes


class BaseException(APIException):
    status_code = status_codes.HTTP_400_BAD_REQUEST
    default_code = 'bad  request'
    default_detail = 'Service temporarily unavailable, try again later.'

    def __init__(self, detail=None, status_code=None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class CustomException(BaseException):
    detail = {
        "success": False,
        "error_message": "Something went wrong"
    }


class InvalidHeaderException(BaseException):
    detail = {
        "success": False,
        "error_message": "send member id in headers"
    }


class InvalidUserException(BaseException):
    detail = {
        "success": False,
        "error_message": "user does not exist"
    }


class InvalidCommunityException(BaseException):
    detail = {
        "success": False,
        "error_message": "Community does not exist"
    }


class InvalidChatroomException(BaseException):
    detail = {
        "success": False,
        "error_message": "Chatroom does not exist"
    }


class InvalidConversationException(BaseException):
    detail = {
        "success": False,
        "error_message": "Conversation does not exist"
    }


class JsonDecodeException(BaseException):
    detail = {
        "success": False,
        "error_message": "Json decode error"
    }


class ResourceNotFoundException(BaseException):
    detail = {
        "success": False,
        "error_message": "resource not found on the server"
    }
