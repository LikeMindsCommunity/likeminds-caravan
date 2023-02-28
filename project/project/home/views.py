from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status as status_codes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class HomeView(APIView):

    # home root method to check server health
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(HomeView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get(request, *args, **kwargs):
        return JsonResponse({'success': True}, status=status_codes.HTTP_200_OK)