from django.http import JsonResponse

from collabmates_api.landing_page.member_community_impl import MemberCommunityImpl
from collabmates_api.landing_page.views_manager import ViewsManager
from collabmates_api.utilities.request_utilities import RequestUtilities
from collabmates_api.utilities.number_utilities import NumberUtilities
from collabmates_api.views import get_error_context


class ViewsImpl(ViewsManager):

    def get_member_communities(self) -> JsonResponse:

        request = self

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page, 1)

        member_id = RequestUtilities.get_member_id_from_headers(request)
        if not member_id:
            """
            TODO: this sends HTTP code: 200 OK response instead of 400 Bad Request
            create exception handling module
            """
            context = get_error_context(False, "member id missing in request")
            return JsonResponse(context)

        member_community_manager = MemberCommunityImpl(member_id, page)
        member_community_manager.extract_member_communities()
        communities = member_community_manager.get_communities()

        return JsonResponse({"member_communities": communities})
