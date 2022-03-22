from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes

from external_services.logging.logging_wrapper import LoggingWrapper
from utility.request_utilities import RequestUtilities
from ..rest_api import get_error_context

from .resources_impl import ResourcesImpl

error_logger = LoggingWrapper.get_instance()


class ResourceSettings(APIView):
    """ View Class for CRUD operations on Resource Settings """

    def _validate_request(self, req_body):
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('community_id'):
            res = get_error_context(False, "community_id cannot be empty")

        return res

    def patch(self, request):
        """to update ResourceSettings against a community_id"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(req_body)

            if request_validation_errors:
                return JsonResponse(
                    request_validation_errors,
                    status=status_codes.HTTP_400_BAD_REQUEST
                )

            res_instance = ResourcesImpl(
                community_id=req_body.get('community_id'),
                member_id=member_id
            )
            res = res_instance.update_resource_settings(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res, 
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """to fetch ResourceSettings against a community_id"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_request(req_body)

            if request_validation_errors:
                return JsonResponse(
                    request_validation_errors,
                    status=status_codes.HTTP_400_BAD_REQUEST
                )

            res_instance = ResourcesImpl(
                community_id=req_body.get('community_id'),
                member_id=member_id
            )
            res = res_instance.fetch_resource_settings()

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(res, status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR)


class ResourceCategory(APIView):
    """ View Class for CRUD operations on Resource Category and Resource Category Permissions """

    def _validate_fetch_request(self, req_body):
        """to validate GET request"""
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('community_id'):
            res = get_error_context(False, "community_id cannot be empty")

        elif not req_body.get('page'):
            res = get_error_context(False, "page cannot be empty")

        return res

    def post(self, request):
        """to create new Resource Category object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id,
                community_id=req_body.get('community_id')
            )
            res = res_instance.create_resource_category(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """to fetch Resource Category object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_fetch_request(req_body)

            if request_validation_errors:
                return JsonResponse(
                    request_validation_errors,
                    status=status_codes.HTTP_400_BAD_REQUEST
                )

            res_instance = ResourcesImpl(
                member_id=member_id,
                community_id=req_body.get('community_id')
            )
            res = res_instance.fetch_resource_category(req_body.get('page'))

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request):
        """to update Resource Category object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.update_resource_category(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """to delete Resource Category object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id,
                community_id=req_body.get('community_id')
            )
            res = res_instance.delete_resource_category(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResourceURL(APIView):
    """
    View Class for CRUD operations on
    - Resource URL
    - Resource URL Permissions
    - Resource URL state
    """
    def post(self, request):
        """to create new Resource URL object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id,
                category_id=req_body.get('category_id')
            )
            res = res_instance.create_resource_url(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request):
        """to update Resource URL object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.update_resource_url(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """to delete Resource URL object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.delete_resource_url(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResourceFile(APIView):
    """
    View Class for CRUD operations on
    - Resource File
    - Resource File Permissions
    - Resource File state
    """
    def post(self, request):
        """to create new Resource File object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id,
                category_id=req_body.get('category_id')
            )
            res = res_instance.create_resource_file(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request):
        """to update Resource File object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.update_resource_file(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """to delete Resource File object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.delete_resource_file(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResourceReference(APIView):
    """
    View Class for CRUD operations on
    - Resource Reference
    """
    def _validate_fetch_request(self, req_body):
        """to validate GET request"""
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        elif not req_body.get('category_id'):
            res = get_error_context(False, "category_id cannot be empty")

        elif not req_body.get('page'):
            res = get_error_context(False, "page cannot be empty")

        return res

    def post(self, request):
        """to create new Resource Reference object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id,
                category_id=req_body.get('category_id')
            )
            res = res_instance.create_resource_reference(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """to delete Resource Reference object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.delete_resource_reference(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """to fetch Resource Reference object"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_fetch_request(req_body)

            if request_validation_errors:
                return JsonResponse(
                    request_validation_errors,
                    status=status_codes.HTTP_400_BAD_REQUEST
                )

            res_instance = ResourcesImpl(
                member_id=member_id,
                category_id=req_body.get('category_id')
            )

            res = res_instance.fetch_resource_reference(req_body.get('page'))

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResourceState(APIView):
    """
    View Class to fetch and update resources' state
    """
    def _validate_update_request(self, req_body):
        """to validate PATCH request"""
        res = {}

        if not req_body:
            res = get_error_context(False, "Invalid request body")

        if not req_body.get('state'):
            res = get_error_context(False, "state cannot be empty")

        if not req_body.get('url_id') and not req_body.get('file_id'):
            res = get_error_context(False, "one among url_id or file_id is needed")

        return res

    def patch(self, request):
        """to update Resource State"""
        try:
            member_id = RequestUtilities.get_member_id_from_headers(request)
            req_body = RequestUtilities.load_request_body(request)

            request_validation_errors = self._validate_update_request(req_body)

            if request_validation_errors:
                return JsonResponse(
                    request_validation_errors,
                    status=status_codes.HTTP_400_BAD_REQUEST
                )

            res_instance = ResourcesImpl(
                member_id=member_id
            )
            res = res_instance.update_resource_state(req_body)

            if res.get('success'):
                return JsonResponse(
                    res,
                    status=status_codes.HTTP_200_OK
                )

            return JsonResponse(
                res,
                status=status_codes.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            res = {
                'success': False,
                'Exception': str(e)
            }
            error_logger.error(e.args)
            return JsonResponse(
                res,
                status=status_codes.HTTP_500_INTERNAL_SERVER_ERROR
            )