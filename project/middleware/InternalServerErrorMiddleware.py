from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse


class InternalServerErrorHandlerMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):

        if not settings.DEBUG:
            response = {
                'success': False,
                'error_message': str(exception),
                'error_root': exception.__class__.__name__
            }

            return JsonResponse(response, safe=False, status=500)
        return None
