from django.utils.deprecation import MiddlewareMixin

from togther.models import (ModelUtilities)


class CustomAuthenticateUserIDMiddleware(MiddlewareMixin):

    def process_request(self, request: {}) -> None:

        user_instance = ModelUtilities.get_user_instance_or_none(request.META.get('HTTP_X_MEMBER_ID'))

        if user_instance:
            request.META['HTTP_X_MEMBER_ID'] = user_instance.id

            if request.META.get('PATH_INFO') in ['api/community_member/join']:
                request.META['HTTP_X_MEMBER_ID'] = user_instance.userinfo.user_unique_id
