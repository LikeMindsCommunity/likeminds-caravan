'''This file contails the api which are used by clients to test'''


from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from togther.models import userMobiles
import json
from django.http.response import JsonResponse
from django.contrib.auth.models import User
@csrf_exempt
def delete_user(request):

    if settings.IS_BETA:
        request_body = json.loads(request.body)

        if 'user_id' in request_body and request_body['user_id']:

            try:
                user_instance = User.objects.get(id=request_body['user_id'])
            except:
                return JsonResponse({'success': False, 'error_message': "send correct user id in beta server"})

            User.objects.filter(id=user_instance.id).delete()

            return JsonResponse({'success':True})
        elif 'mobile_no' in request_body and request_body['mobile_no']:

            try:
                user_mobiles = userMobiles.objects.get(mobile_no=request_body['mobile_no'])
                user_instance=user_mobiles.user
            except:
                return JsonResponse({'success': False, 'error_message': "send correct user id in beta server"})

            User.objects.filter(id=user_instance.id).delete()
            return JsonResponse({'success': True})

    return JsonResponse({'success':False,'error_message':"send correct user id in beta server"})
