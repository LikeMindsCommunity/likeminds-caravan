from django.http import JsonResponse
from rest_framework.views import APIView

from collabmates_api.snackbar.snackbar_impl import SnackbarImpl
from utility.exception_utilities import InvalidHeaderException
from utility.request_utilities import RequestUtilities


class FetchSnackbar(APIView):

    def get(self, request):

        member_id = RequestUtilities.get_member_id_from_headers(request)

        if not member_id:
            raise InvalidHeaderException()

        snackbar_manager = SnackbarImpl()
        snackbar_context = snackbar_manager.fetch_snackbar(member_id)

        return JsonResponse(snackbar_context)

